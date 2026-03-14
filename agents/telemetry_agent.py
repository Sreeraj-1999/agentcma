"""
Telemetry Agent v3 — embedding-based tag resolution.

Two-stage key resolution:
  Stage 1 (Embedding, ~$0.0001): Embed question → cosine similarity → top 20 tags
  Stage 2 (LLM, cheap): Pick exact keys from 20 candidates → ~200 tokens

Never sends 629 keys to LLM. Semantic search, not keyword matching.
"""

import json
import numpy as np
from pathlib import Path
from openai import AzureOpenAI
from config.llm_client import chat
from config.settings import (
    AGENT_CONFIG,
    get_vessel_fk,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    OPENAI_API_VERSION,
    AZURE_OPENAI_EMBEDDING_MODEL,
)
from datamarts.pg_connector import execute_sql


CACHE_PATH = Path("data/tag_cache.json")
_cache = None
_embed_client = None


def _get_embed_client():
    global _embed_client
    if _embed_client is None:
        _embed_client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=OPENAI_API_VERSION,
        )
    return _embed_client


def load_cache() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    if not CACHE_PATH.exists():
        raise FileNotFoundError("Tag cache not found. Run: python build_tag_cache.py")
    _cache = json.loads(CACHE_PATH.read_text())
    return _cache


def embed_query(text: str) -> list[float]:
    """Embed a single query string."""
    client = _get_embed_client()
    response = client.embeddings.create(
        model=AZURE_OPENAI_EMBEDDING_MODEL,
        input=[text],
    )
    return response.data[0].embedding


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def find_similar_tags(question: str, top_k: int = 20) -> list[dict]:
    """
    Stage 1: Embed question, find top_k most similar tags by cosine similarity.
    Cost: 1 embedding call (~$0.0001)
    """
    cache = load_cache()
    tags = cache["tags"]

    # Embed the question
    q_embedding = embed_query(question)

    # Score every tag
    scored = []
    for tag_name, info in tags.items():
        if "embedding" not in info:
            continue
        sim = cosine_similarity(q_embedding, info["embedding"])
        scored.append({
            "tag": tag_name,
            "description": info["description"],
            "unit": info.get("unit", ""),
            "similarity": sim,
        })

    # Sort by similarity, return top_k
    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:top_k]


class TelemetryAgent:
    def __init__(self):
        self.datamart_name = "telemetry"

    def run(self, question: str, vessel_name: str = None, context: dict = None) -> dict:
        fk_vessel = get_vessel_fk(vessel_name) if vessel_name else None
        if fk_vessel is None:
            return self._error_result(f"Unknown vessel: {vessel_name}. Add to VESSEL_ID_MAP in settings.py")

        # Stage 1: Embedding search (1 API call, ~$0.0001)
        candidates = find_similar_tags(question, top_k=20)
        if not candidates:
            return self._error_result("This data is not available in our telemetry system. Available data includes engine sensors, temperatures, pressures, and alarms.")

        # Stage 2: LLM picks exact keys from 20 candidates (~200 tokens)
        selected_keys = self._resolve_keys(question, candidates, context)
        if not selected_keys:
            return self._error_result("This data is not available in our telemetry system. The requested measurements were not found among the vessel's sensor tags.")

        # Generate SQL
        sql = self._generate_sql(question, selected_keys, fk_vessel, context)
        if not sql:
            return self._error_result("Failed to generate SQL query")

        # Execute
        result = execute_sql(sql)
        if not result["success"]:
            sql = self._retry_sql(question, selected_keys, fk_vessel, sql, result["error"])
            if sql:
                result = execute_sql(sql)
            if not result["success"]:
                return self._error_result(f"SQL failed: {result['error']}")

        # Interpret
        interpretation = self._interpret_results(question, result, selected_keys, context)

        return {
            "answer": interpretation.get("answer", ""),
            "condition_met": interpretation.get("condition_met"),
            "evidence": interpretation.get("evidence", ""),
            "raw_data": result["rows"][:20],
            "query_used": sql,
            "selected_keys": selected_keys,
            "error": None,
        }

    def _resolve_keys(self, question: str, candidates: list[dict], context: dict) -> list[str]:
        """Stage 2: LLM picks from embedding-filtered candidates."""
        candidate_text = "\n".join(
            f"- {c['tag']}: {c['description']} ({c['unit']})" for c in candidates
        )

        context_str = ""
        if context:
            context_str = f"\nContext from previous steps:\n{json.dumps(context, indent=2, default=str)}"

        messages = [
            {
                "role": "system",
                "content": f"""Select the relevant sensor tags for this question.
Return ONLY a JSON array of exact tag names. No explanation.

Candidate tags:
{candidate_text}{context_str}"""
            },
            {"role": "user", "content": question}
        ]

        try:
            response = chat(messages, temperature=0.0)
            response = response.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
            return json.loads(response.strip())
        except Exception:
            return []

    def _generate_sql(self, question: str, keys: list[str], fk_vessel: int, context: dict) -> str | None:
        context_str = ""
        if context:
            context_str = f"\nContext:\n{json.dumps(context, indent=2, default=str)}"

        cache = load_cache()
        key_info = []
        for k in keys:
            info = cache["tags"].get(k, {})
            key_info.append(f"  {k}: {info.get('description', k)} ({info.get('unit', '')})")

        messages = [
            {
                "role": "system",
                "content": f"""Generate PostgreSQL query for marine vessel telemetry.

Tables:
- "VesselDataLive": Latest reading (1 row per vessel)
- "VesselData": Historical (many rows)
Both: id, payload (JSONB), fk_vessel (INT), "vesselTime" (TIMESTAMP), "vesselTimeStamp" (BIGINT)

Rules:
- Double-quote table names: "VesselDataLive", "VesselData"
- Double-quote camelCase columns: "vesselTime", "vesselTimeStamp", "createdAt"
- NEVER double-quote fk_vessel — always write it as: fk_vessel = {fk_vessel} (no quotes)
- payload->>'key' returns text. Cast: (payload->>'key')::float
- WHERE fk_vessel = {fk_vessel}
- Latest = "VesselDataLive", Historical = "VesselData"
- ALWAYS fetch the data first. Do NOT invent threshold values or add arbitrary numeric filters (e.g. > 80) unless the user specifies an exact number. Let the data speak for itself.

Selected keys:
{chr(10).join(key_info)}

Return ONLY SQL.{context_str}"""
            },
            {"role": "user", "content": question}
        ]

        try:
            response = chat(messages, temperature=0.0)
            return response.strip().removeprefix("```sql").removeprefix("```").removesuffix("```").strip()
        except Exception:
            return None

    def _retry_sql(self, question, keys, fk_vessel, failed_sql, error):
        messages = [
            {
                "role": "system",
                "content": f"""Fix this PostgreSQL query.
Failed: {failed_sql}
Error: {error}
Double-quote "VesselDataLive"/"VesselData", "vesselTime" etc.
payload->>'key' for text, ::float to cast. fk_vessel = {fk_vessel}
Return ONLY corrected SQL."""
            },
            {"role": "user", "content": question}
        ]
        try:
            response = chat(messages, temperature=0.0)
            return response.strip().removeprefix("```sql").removeprefix("```").removesuffix("```").strip()
        except Exception:
            return None

    def _interpret_results(self, question, query_result, keys, context):
        rows = query_result["rows"][:10]
        context_str = ""
        if context:
            context_str = f"\nContext:\n{json.dumps(context, indent=2, default=str)}"

        messages = [
            {
                "role": "system",
                "content": f"""Marine telemetry analyst. Respond with JSON:
{{"answer": "your answer", "condition_met": true/false/null, "evidence": "key data points"}}

Rules:
- If the question is a yes/no condition (e.g. "is X above Y?"), answer with yes/no + explanation, and set condition_met to true/false.
- If the question is informational (e.g. "what is the RPM?"), give a direct answer with the actual values, and set condition_met to null.
ONLY JSON.{context_str}"""
            },
            {
                "role": "user",
                "content": f"Question: {question}\nData ({query_result['row_count']} rows): {json.dumps(rows, default=str)}"
            }
        ]
        try:
            response = chat(messages, temperature=0.0)
            response = response.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
            return json.loads(response.strip())
        except Exception as e:
            return {"answer": f"Could not interpret: {e}", "condition_met": None, "evidence": str(rows[:3])}

    def _error_result(self, msg):
        return {"answer": f"Error: {msg}", "condition_met": None, "evidence": "", "raw_data": [], "query_used": "", "selected_keys": [], "error": msg}