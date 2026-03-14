"""
Unified datamart executor.
Agents call this — it routes to PostgreSQL or CSV reader based on datamart type.
"""

import yaml
from pathlib import Path
from config.settings import PROJECT_ROOT
from datamarts.pg_connector import execute_sql
from datamarts.csv_reader import execute_pandas_query, get_datamart_info, get_vessel_names


SCHEMA_DIR = PROJECT_ROOT / "config" / "schemas"


def load_schema(datamart_name: str) -> dict:
    """Load the YAML schema for a datamart."""
    schema_path = SCHEMA_DIR / f"{datamart_name}.yaml"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    with open(schema_path, "r") as f:
        return yaml.safe_load(f)


def get_schema_description(datamart_name: str) -> str:
    """
    Get a human-readable schema description for the LLM prompt.
    This is what the agent sees when deciding how to query.
    """
    schema = load_schema(datamart_name)
    source = schema.get("source", "unknown")

    lines = [
        f"Datamart: {datamart_name}",
        f"Source: {source}",
        f"Description: {schema.get('description', 'N/A')}",
        "",
    ]

    if source == "postgresql":
        for table_name, table_info in schema.get("tables", {}).items():
            lines.append(f"Table: {table_name}")
            lines.append(f"  {table_info.get('description', '')}")
            for col in table_info.get("columns", []):
                lines.append(f"  - {col['name']} ({col['type']}): {col['description']}")
            lines.append("")
    else:
        lines.append("Columns:")
        for col in schema.get("columns", []):
            lines.append(f"  - {col['name']} ({col['type']}): {col['description']}")

    return "\n".join(lines)


def execute_query(datamart_name: str, query: str, source: str = None) -> dict:
    """
    Execute a query against any datamart.
    
    Args:
        datamart_name: Name of the datamart
        query: SQL string (for postgres) or pandas query string (for csv)
        source: "postgresql" or "csv" — auto-detected from schema if not provided
    """
    if source is None:
        schema = load_schema(datamart_name)
        source = schema.get("source", "csv")

    if source == "postgresql":
        return execute_sql(query)
    else:
        return execute_pandas_query(datamart_name, query)


def list_datamarts() -> list[dict]:
    """List all available datamarts with their source type."""
    datamarts = []
    for schema_file in SCHEMA_DIR.glob("*.yaml"):
        schema = yaml.safe_load(schema_file.read_text())
        datamarts.append({
            "name": schema_file.stem,
            "source": schema.get("source", "unknown"),
            "description": schema.get("description", ""),
        })
    return datamarts
