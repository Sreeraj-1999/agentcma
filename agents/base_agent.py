"""
Base Agent — the core intelligence layer.

Takes a natural language question + datamart schema,
asks Azure GPT-4.1 to generate a pandas query,
executes it, then asks GPT-4.1 to interpret the results.

Every datamart agent inherits from this.
"""

import json
from config.llm_client import chat
from datamarts.executor import execute_query, get_schema_description, load_schema
from datamarts.csv_reader import get_datamart_info
from config.settings import AGENT_CONFIG


class BaseAgent:
    def __init__(self, datamart_name: str):
        self.datamart_name = datamart_name
        self.schema = load_schema(datamart_name)
        self.source = self.schema.get("source", "csv")
        self.schema_description = get_schema_description(datamart_name)

    def run(self, question: str, vessel_name: str = None, context: dict = None) -> dict:
        """
        Main entry point. Ask a question, get a structured answer.

        Args:
            question: Natural language question (e.g. "Are there pending jobs for ME turbocharger?")
            vessel_name: Filter by vessel (e.g. "Flora Schulte")
            context: Accumulated context from previous agents in the chain

        Returns:
            {
                "answer": "Yes/No + explanation",
                "condition_met": True/False/None,
                "evidence": "Summary of data found",
                "raw_data": [...],
                "query_used": "the pandas/sql query that was generated",
                "error": None or error message
            }
        """
        # Step 1: Generate query
        query_code = self._generate_query(question, vessel_name, context)
        if query_code is None:
            return self._error_result("Failed to generate query")

        # Step 2: Execute query (with retry on failure)
        result = execute_query(self.datamart_name, query_code, self.source)

        if not result["success"]:
            # Retry once — tell LLM the error so it can fix the query
            query_code = self._retry_query(question, vessel_name, query_code, result["error"])
            if query_code is None:
                return self._error_result(f"Query failed: {result['error']}")
            result = execute_query(self.datamart_name, query_code, self.source)
            if not result["success"]:
                return self._error_result(f"Query failed after retry: {result['error']}")

        # Step 3: Interpret results
        interpretation = self._interpret_results(question, result, context)

        return {
            "answer": interpretation.get("answer", ""),
            "condition_met": interpretation.get("condition_met"),
            "evidence": interpretation.get("evidence", ""),
            "raw_data": result["rows"][:20],  # cap raw data passed forward
            "query_used": query_code,
            "error": None,
        }

    def _generate_query(self, question: str, vessel_name: str, context: dict) -> str | None:
        """Ask LLM to generate a pandas query (or SQL for postgres)."""

        if self.source == "csv":
            query_type = "pandas"
            query_instructions = """Generate a pandas query string that will be executed as:
    result = eval(query_code, {}, {"df": dataframe, "pd": pandas})

Rules:
- The DataFrame is called `df`
- Always return a DataFrame or Series, not a bool
- For filtering: df[df['col'] == 'value']
- For dates: use pd.Timestamp('2026-03-13') for comparison. Today is 2026-03-13.
- String matching: use .str.contains('keyword', case=False, na=False) for fuzzy matching
- Return ONLY the query string, nothing else. No explanation, no markdown."""
        else:
            query_type = "SQL"
            query_instructions = """Generate a PostgreSQL query.
Rules:
- Return ONLY the SQL string, nothing else. No explanation, no markdown.
- Use single quotes for string literals."""

        vessel_filter = ""
        if vessel_name:
            vessel_filter = f"\nIMPORTANT: Filter by vessel name = '{vessel_name}'"

        context_str = ""
        if context:
            context_str = f"\nContext from previous steps:\n{json.dumps(context, indent=2, default=str)}"

        messages = [
            {
                "role": "system",
                "content": f"""You are a {query_type} query generator for marine vessel maintenance data.
You will be given a schema and a question. Generate ONLY the query code, nothing else.

Schema:
{self.schema_description}
{vessel_filter}{context_str}

{query_instructions}"""
            },
            {
                "role": "user",
                "content": question,
            }
        ]

        try:
            response = chat(messages, temperature=0.0)
            # Clean up response — remove markdown fences if present
            query = response.strip()
            query = query.removeprefix("```python").removeprefix("```sql").removeprefix("```")
            query = query.removesuffix("```")
            return query.strip()
        except Exception as e:
            print(f"[BaseAgent] Query generation failed: {e}")
            return None

    def _retry_query(self, question: str, vessel_name: str, failed_query: str, error: str) -> str | None:
        """Retry query generation with error feedback."""

        messages = [
            {
                "role": "system",
                "content": f"""You are a query generator. Your previous query failed. Fix it.

Schema:
{self.schema_description}

Failed query: {failed_query}
Error: {error}

Generate ONLY the corrected query string. Nothing else."""
            },
            {
                "role": "user",
                "content": question,
            }
        ]

        try:
            response = chat(messages, temperature=0.0)
            query = response.strip()
            query = query.removeprefix("```python").removeprefix("```sql").removeprefix("```")
            query = query.removesuffix("```")
            return query.strip()
        except Exception:
            return None

    def _interpret_results(self, question: str, query_result: dict, context: dict) -> dict:
        """Ask LLM to interpret query results and determine if condition is met."""

        # Limit data sent to LLM
        rows_to_show = query_result["rows"][:10]
        row_count = query_result["row_count"]

        context_str = ""
        if context:
            context_str = f"\nContext from previous steps:\n{json.dumps(context, indent=2, default=str)}"

        messages = [
            {
                "role": "system",
                "content": f"""You are a marine vessel maintenance analyst.
You were asked a question, and a query was run against the data.
Analyze the results and respond with a JSON object:

{{
    "answer": "Clear yes/no answer with brief explanation",
    "condition_met": true or false or null (if question doesn't have a yes/no condition),
    "evidence": "Key data points that support your answer (keep brief)"
}}

Return ONLY valid JSON. No markdown, no explanation outside the JSON.{context_str}"""
            },
            {
                "role": "user",
                "content": f"""Question: {question}

Query returned {row_count} rows.
Data (first {len(rows_to_show)} rows):
{json.dumps(rows_to_show, indent=2, default=str)}"""
            }
        ]

        try:
            response = chat(messages, temperature=0.0)
            # Clean and parse JSON
            response = response.strip()
            response = response.removeprefix("```json").removeprefix("```")
            response = response.removesuffix("```")
            return json.loads(response.strip())
        except Exception as e:
            return {
                "answer": f"Could not interpret results: {e}",
                "condition_met": None,
                "evidence": f"Raw data: {rows_to_show[:3]}",
            }

    def _error_result(self, error_msg: str) -> dict:
        return {
            "answer": f"Error: {error_msg}",
            "condition_met": None,
            "evidence": "",
            "raw_data": [],
            "query_used": "",
            "error": error_msg,
        }
