"""
Quick test — run this to verify your CSV datamarts load correctly.

Usage:
    python test_datamarts.py
    
Before running, copy your CSVs to the data/ folder:
    data/Job_Plan.csv
    data/Job_History_Pending_Job.csv
    data/Job_History_Completed_Job.csv
    data/Voyage_Plan_Data.csv
    data/Equipment_Query.csv
    data/Running_Hours.csv
"""

import sys
sys.path.insert(0, ".")

from datamarts.csv_reader import load_datamart, get_vessel_names, execute_pandas_query
from datamarts.executor import list_datamarts, get_schema_description


def main():
    print("=== Datamart Connection Test ===\n")

    # 1. List all datamarts
    print("Available datamarts:")
    for dm in list_datamarts():
        print(f"  [{dm['source']}] {dm['name']}")
    print()

    # 2. Try loading each CSV datamart
    csv_datamarts = ["job_plan", "pending_jobs", "completed_jobs", "voyage_plan", "equipment", "running_hours"]
    
    for name in csv_datamarts:
        try:
            df = load_datamart(name)
            vessels = get_vessel_names(name)
            print(f"✅ {name}: {len(df)} rows, {len(df.columns)} columns")
            if vessels:
                print(f"   Vessels: {', '.join(vessels[:5])}")
        except FileNotFoundError:
            print(f"⬜ {name}: CSV not found (add it to data/ folder)")
        except Exception as e:
            print(f"❌ {name}: {e}")
    
    print()

    # 3. Test a sample query
    print("--- Sample Query Test ---")
    try:
        result = execute_pandas_query(
            "pending_jobs",
            "df[df['Vessel_Name'].str.contains('Flora', na=False)][['Job_title', 'Equipment_Name', 'Next_Due_Date']].head(5)"
        )
        if result["success"]:
            print(f"✅ Query returned {result['row_count']} rows")
            for row in result["rows"][:3]:
                print(f"   {row}")
        else:
            print(f"❌ Query failed: {result['error']}")
    except FileNotFoundError:
        print("⬜ Skipped — pending_jobs CSV not found")

    print()

    # 4. Show schema description (what the LLM will see)
    print("--- Schema Description (LLM sees this) ---")
    print(get_schema_description("pending_jobs")[:500])
    print("...")


if __name__ == "__main__":
    main()
