"""
PostgreSQL connector for telemetry datamart.
Handles connection pooling, safe query execution, and result formatting.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from config.settings import TELEMETRY_DB


@contextmanager
def get_connection():
    """Get a PostgreSQL connection. Auto-closes when done."""
    conn = psycopg2.connect(
        host=TELEMETRY_DB["host"],
        port=TELEMETRY_DB["port"],
        dbname=TELEMETRY_DB["dbname"],
        user=TELEMETRY_DB["user"],
        password=TELEMETRY_DB["password"],
    )
    try:
        yield conn
    finally:
        conn.close()


def execute_sql(sql: str, params: tuple = None) -> dict:
    """
    Execute a SQL query safely and return structured results.
    
    Returns:
        {
            "success": True/False,
            "columns": [...],
            "rows": [{...}, {...}],
            "row_count": int,
            "error": None or error message
        }
    """
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                
                # If it's a SELECT, fetch results
                if cur.description:
                    columns = [desc[0] for desc in cur.description]
                    rows = [dict(row) for row in cur.fetchall()]
                    return {
                        "success": True,
                        "columns": columns,
                        "rows": rows,
                        "row_count": len(rows),
                        "error": None,
                    }
                else:
                    conn.commit()
                    return {
                        "success": True,
                        "columns": [],
                        "rows": [],
                        "row_count": cur.rowcount,
                        "error": None,
                    }
    except Exception as e:
        return {
            "success": False,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "error": str(e),
        }


def test_connection() -> bool:
    """Quick check if PostgreSQL is reachable."""
    result = execute_sql("SELECT 1 AS ping")
    return result["success"]
