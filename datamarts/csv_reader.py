"""
CSV datamart reader.
Loads CSV files into pandas DataFrames and executes queries on them.
The LLM generates pandas query code instead of SQL for CSV datamarts.
"""

import pandas as pd
from pathlib import Path
from config.settings import CSV_DATAMARTS

# Cache loaded dataframes so we don't re-read CSVs every query
_df_cache: dict[str, pd.DataFrame] = {}


def load_datamart(name: str) -> pd.DataFrame:
    """
    Load a CSV datamart by name. Caches after first load.
    
    Args:
        name: One of the keys in CSV_DATAMARTS 
              (job_plan, pending_jobs, completed_jobs, voyage_plan, equipment, running_hours)
    """
    if name in _df_cache:
        return _df_cache[name]

    path = CSV_DATAMARTS.get(name)
    if path is None:
        raise ValueError(f"Unknown datamart: {name}. Available: {list(CSV_DATAMARTS.keys())}")

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    df = pd.read_csv(path, encoding="utf-8-sig")

    # Parse date columns automatically
    for col in df.columns:
        if "date" in col.lower() or col in ("ATA_LT", "ATB_LT", "ATS_LT", "ETB", "ETS"):
            try:
                df[col] = pd.to_datetime(df[col], errors="coerce")
            except Exception:
                pass

    _df_cache[name] = df
    return df


def execute_pandas_query(datamart_name: str, query_code: str) -> dict:
    """
    Execute a pandas query string against a CSV datamart.
    
    The LLM generates query_code like:
        "df[df['Vessel_Name'] == 'Flora Schulte'][['Job_title', 'Next_Due_Date']].head(10)"
    
    We provide `df` as the loaded DataFrame.
    
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
        df = load_datamart(datamart_name)

        # Execute the pandas query with df available
        # Also provide pd for things like pd.Timestamp
        local_vars = {"df": df, "pd": pd}
        result = eval(query_code, {"__builtins__": {}}, local_vars)

        # Convert result to standard format
        if isinstance(result, pd.DataFrame):
            rows = result.to_dict(orient="records")
            columns = list(result.columns)
        elif isinstance(result, pd.Series):
            rows = [result.to_dict()]
            columns = list(result.index)
        else:
            # Scalar result (count, mean, etc.)
            rows = [{"result": result}]
            columns = ["result"]

        return {
            "success": True,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
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


def get_datamart_info(name: str) -> dict:
    """
    Get basic info about a datamart — column names, types, row count, sample values.
    Used by agents to understand the data before generating queries.
    """
    df = load_datamart(name)
    
    info = {
        "name": name,
        "row_count": len(df),
        "columns": {},
    }
    
    for col in df.columns:
        info["columns"][col] = {
            "dtype": str(df[col].dtype),
            "null_count": int(df[col].isna().sum()),
            "sample_values": [str(v) for v in df[col].dropna().unique()[:5]],
        }
    
    return info


def get_vessel_names(name: str) -> list[str]:
    """Get list of unique vessel names in a datamart."""
    df = load_datamart(name)
    vessel_col = None
    for col in ("Vessel_Name", "Vessel", "vessel_name"):
        if col in df.columns:
            vessel_col = col
            break
    if vessel_col is None:
        return []
    return sorted(df[vessel_col].dropna().unique().tolist())


def clear_cache():
    """Clear the DataFrame cache. Call if CSVs are updated."""
    _df_cache.clear()
