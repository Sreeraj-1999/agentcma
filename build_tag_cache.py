"""
Build tag cache with embeddings.

Run once:
    python build_tag_cache.py

Creates data/tag_cache.json with descriptions + embeddings for every tag.
Costs ~$0.01 one time.
"""

import sys
sys.path.insert(0, ".")

import json
import numpy as np
import pandas as pd
from pathlib import Path
from openai import AzureOpenAI
from config.settings import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    OPENAI_API_VERSION,
    AZURE_OPENAI_EMBEDDING_MODEL,
    get_vessel_fk,
)
from datamarts.pg_connector import execute_sql

CACHE_PATH = Path("data/tag_cache.json")
EXCEL_PATH = Path("data/Freya_schulte_AMS_mapped_1.xlsx")


def get_embeddings(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    """Get embeddings from Azure OpenAI in batches."""
    client = AzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_version=OPENAI_API_VERSION,
    )

    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        print(f"  Embedding batch {i // batch_size + 1}/{(len(texts) - 1) // batch_size + 1}...")
        response = client.embeddings.create(
            model=AZURE_OPENAI_EMBEDDING_MODEL,
            input=batch,
        )
        for item in response.data:
            all_embeddings.append(item.embedding)

    return all_embeddings


def build_cache():
    print("=== Building Tag Cache with Embeddings ===\n")

    # Step 1: Load excel mapping
    df = pd.read_excel(EXCEL_PATH)
    df = df.dropna(subset=["actual_tag"])

    excel_map = {}
    for _, row in df.iterrows():
        tag = str(row["actual_tag"]).strip()
        excel_map[tag] = {
            "description": str(row["description"]).strip() if pd.notna(row["description"]) else tag,
            "unit": str(row["unit"]).strip() if pd.notna(row["unit"]) else "",
        }

    print(f"Excel tags loaded: {len(excel_map)}")

    # Step 2: Get actual payload keys from Flora's live data
    fk = get_vessel_fk("Flora Schulte")
    result = execute_sql(
        'SELECT jsonb_object_keys(payload) AS key_name FROM "VesselDataLive" WHERE fk_vessel = %s',
        (fk,),
    )

    if not result["success"]:
        print(f"DB error: {result['error']}. Using excel keys only.")
        db_keys = list(excel_map.keys())
    else:
        db_keys = sorted([row["key_name"] for row in result["rows"]])
        print(f"DB payload keys: {len(db_keys)}")

    # Step 3: Match DB keys to descriptions
    tags = {}
    for key in db_keys:
        # Exact match
        if key in excel_map:
            tags[key] = excel_map[key]
            continue

        # Strip @AVG/@LAST/@MAX/@MIN/@RMS suffix
        base_key = key.split("@")[0] if "@" in key else None
        if base_key and base_key in excel_map:
            suffix = key.split("@")[1]
            suffix_map = {"AVG": "average", "LAST": "last value", "MAX": "maximum", "MIN": "minimum", "RMS": "RMS"}
            desc = excel_map[base_key]["description"]
            tags[key] = {
                "description": f"{desc} ({suffix_map.get(suffix, suffix)})",
                "unit": excel_map[base_key]["unit"],
            }
            continue

        # No match — readable key name as description
        tags[key] = {
            "description": key.replace("_", " "),
            "unit": "",
        }

    print(f"Total tags mapped: {len(tags)}")

    # Step 4: Generate embeddings for all tag descriptions
    print("\nGenerating embeddings...")
    tag_names = list(tags.keys())
    # Embed: "tag_name: description (unit)" for best semantic matching
    texts_to_embed = []
    for name in tag_names:
        info = tags[name]
        text = f"{name}: {info['description']}"
        if info["unit"]:
            text += f" ({info['unit']})"
        texts_to_embed.append(text)

    embeddings = get_embeddings(texts_to_embed)
    print(f"Embeddings generated: {len(embeddings)}")

    # Step 5: Attach embeddings to tags
    for i, name in enumerate(tag_names):
        tags[name]["embedding"] = embeddings[i]

    # Step 6: Save cache
    cache = {
        "tags": tags,
        "vessel": "Flora Schulte",
        "total_tags": len(tags),
        "embedding_model": AZURE_OPENAI_EMBEDDING_MODEL,
        "embedding_dim": len(embeddings[0]) if embeddings else 0,
    }

    CACHE_PATH.write_text(json.dumps(cache))
    print(f"\nCache saved to {CACHE_PATH}")
    print(f"Total tags: {len(tags)}")
    print(f"Embedding dimension: {cache['embedding_dim']}")
    print(f"File size: {CACHE_PATH.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    build_cache()
