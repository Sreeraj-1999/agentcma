"""
Test the base agent — first real Azure GPT-4.1 call.

Usage:
    python test_agent.py
"""

import sys
sys.path.insert(0, ".")

from agents.base_agent import BaseAgent


def main():
    print("=== Base Agent Test ===\n")

    # Test 1: Pending jobs agent
    print("--- Test 1: Pending jobs for Flora Schulte ---")
    agent = BaseAgent("pending_jobs")
    result = agent.run(
        question="Are there any pending jobs related to main engine or turbocharger due in the next 10 days?",
        vessel_name="Flora Schulte"
    )
    print(f"Answer: {result['answer']}")
    print(f"Condition met: {result['condition_met']}")
    print(f"Evidence: {result['evidence']}")
    print(f"Query used: {result['query_used']}")
    if result['error']:
        print(f"Error: {result['error']}")
    print()

    # Test 2: Equipment lookup
    print("--- Test 2: Equipment lookup ---")
    agent2 = BaseAgent("equipment")
    result2 = agent2.run(
        question="What main engine equipment does this vessel have?",
        vessel_name="Flora Schulte"
    )
    print(f"Answer: {result2['answer']}")
    print(f"Evidence: {result2['evidence']}")
    print(f"Query used: {result2['query_used']}")
    print()

    # Test 3: With context from previous step
    print("--- Test 3: Job plan with context ---")
    agent3 = BaseAgent("job_plan")
    result3 = agent3.run(
        question="Are there any inspection jobs due for this equipment?",
        vessel_name="Flora Schulte",
        context={
            "previous_step": "Equipment ME TURBOCHARGER identified",
            "equipment_name": "ME TURBOCHARGER",
        }
    )
    print(f"Answer: {result3['answer']}")
    print(f"Condition met: {result3['condition_met']}")
    print(f"Evidence: {result3['evidence']}")
    print(f"Query used: {result3['query_used']}")


if __name__ == "__main__":
    main()
