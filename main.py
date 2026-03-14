"""
Marine Diagnostic Agent
=======================
Multi-agent diagnostic pipeline for vessel engine maintenance.

Usage:
    python main.py

The user provides a natural language diagnostic chain, and the system:
1. Decomposes it into ordered conditional steps
2. Each step queries the appropriate datamart (PostgreSQL or Excel)
3. Results are evaluated and passed to the next step
4. Final output is an actionable alert/recommendation
"""

from config.settings import VESSEL_NAME, VESSEL_IMO


def main():
    print(f"=== Marine Diagnostic Agent ===")
    print(f"Vessel: {VESSEL_NAME} (IMO: {VESSEL_IMO})")
    print()

    # Example diagnostic chain — this will come from user input
    diagnostic_chain = """
    1) Check telemetry if there is exhaust deviation of more than 30 deg from average.
    2) If Yes, check scavenge inspection reports if carbon level > 3
    3) If yes check drain oil analysis reports (last three) and check trend Iron content. 
       If iron content is increasing more than 10 percent per month
    4) Check if job orders pending list or defect job pending list requiring scavenge, 
       under piston space inspection due in the next 10 days or overdue in list. 
       If no take action recommended.
    Action: Please issue Alert card with Title 
       "Perform Under piston space inspection in the next 10 days".
    """

    print("Diagnostic chain received:")
    print(diagnostic_chain)
    print()
    print("TODO: Wire up orchestrator → decomposer → agents → action")


if __name__ == "__main__":
    main()
