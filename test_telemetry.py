"""
Test telemetry agent against real PostgreSQL database.

Usage:
    python test_telemetry.py
"""

import sys
sys.path.insert(0, ".")

from agents.telemetry_agent import TelemetryAgent, load_cache
from config.settings import get_vessel_fk


def main():
    vessel = "Flora Schulte"
    fk = get_vessel_fk(vessel)
    print(f"=== Telemetry Agent Test ===")
    print(f"Vessel: {vessel} (fk_vessel={fk})\n")

    # Step 1: Check we can get payload keys from the embedding cache
    print("--- Fetching payload keys from tag cache ---")
    cache = load_cache()
    keys = list(cache["tags"].keys())
    print(f"Found {len(keys)} keys (from tag_cache.json)")
    print(f"Sample keys: {keys[:10]}")
    print()

    if not keys:
        print("ERROR: No keys found. Check DB connection.")
        return

    # Step 2: Simple query — current engine RPM
    print("--- Test 1: Current main engine RPM ---")
    agent = TelemetryAgent()
    result = agent.run("What is the current main engine RPM?", vessel)
    print(f"Answer: {result['answer']}")
    print(f"Keys used: {result.get('selected_keys', [])}")
    print(f"SQL: {result['query_used']}")
    print()

    # Step 3: Exhaust temperature check
    print("--- Test 2: Exhaust gas temperatures ---")
    result2 = agent.run(
        "What are the exhaust gas temperatures after each cylinder? Is there any deviation from average greater than 30 degrees?",
        vessel
    )
    print(f"Answer: {result2['answer']}")
    print(f"Condition met: {result2['condition_met']}")
    print(f"Evidence: {result2['evidence']}")
    print(f"Keys used: {result2.get('selected_keys', [])}")
    print()

    # Step 4: Scavenge air box temp check
    print("--- Test 3: Scavenge air box temperatures ---")
    result3 = agent.run(
        "Are any scavenge air box temperatures abnormally high?",
        vessel
    )
    print(f"Answer: {result3['answer']}")
    print(f"Evidence: {result3['evidence']}")
    print(f"Keys used: {result3.get('selected_keys', [])}")
    print(f"SQL: {result3.get('query_used', '')}")
    print(f"Raw data: {result3.get('raw_data', [])}")




if __name__ == "__main__":
    main()
