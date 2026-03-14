import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# --- Azure OpenAI ---
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
OPENAI_API_VERSION = os.getenv("OPENAI_API_VERSION", "2024-12-01-preview")
AZURE_OPENAI_MODEL = os.getenv("AZURE_OPENAI_MODEL", "gpt-4.1")
AZURE_OPENAI_EMBEDDING_MODEL = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

# --- Telemetry Database (PostgreSQL) ---
TELEMETRY_DB = {
    "host": os.getenv("TELEMETRY_DB_HOST", "localhost"),
    "port": int(os.getenv("TELEMETRY_DB_PORT", 5432)),
    "dbname": os.getenv("TELEMETRY_DB_NAME", "telemetry"),
    "user": os.getenv("TELEMETRY_DB_USER", "postgres"),
    "password": os.getenv("TELEMETRY_DB_PASSWORD", ""),
}

TELEMETRY_DB_URL = (
    f"postgresql://{TELEMETRY_DB['user']}:{TELEMETRY_DB['password']}"
    f"@{TELEMETRY_DB['host']}:{TELEMETRY_DB['port']}/{TELEMETRY_DB['dbname']}"
)

# --- CSV Datamart Paths ---
DATA_DIR = PROJECT_ROOT / "data"

CSV_DATAMARTS = {
    "job_plan": DATA_DIR / "Job_Plan.csv",
    "completed_jobs": DATA_DIR / "Job_History_Completed_Job.csv",
    "pending_jobs": DATA_DIR / "Job_History_Pending_Job.csv",
    "voyage_plan": DATA_DIR / "Voyage_Plan_Data.csv",
    "equipment": DATA_DIR / "Equipment_Query.csv",
    "running_hours": DATA_DIR / "Running_Hours.csv",
}

# --- Vessel ID Mapping (scalable — add new vessels here) ---
VESSEL_ID_MAP = {
    "Flora Schulte": 9,
    # "Franz Schulte": 10,  # add when ready
    # "Carl Schulte": 11,
}

# --- Vessel ---
VESSEL_NAME = os.getenv("VESSEL_NAME", "Flora Schulte")
VESSEL_IMO = os.getenv("VESSEL_IMO", "unknown")

# --- Agent Config ---
AGENT_CONFIG = {
    "max_sql_retries": 2,
    "tag_search_top_k": 5,
    "temperature": 0.0,
}


def get_vessel_fk(vessel_name: str) -> int | None:
    """Get the fk_vessel ID for a vessel name."""
    return VESSEL_ID_MAP.get(vessel_name)