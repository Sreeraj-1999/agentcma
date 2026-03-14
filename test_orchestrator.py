"""
Test the full diagnostic pipeline end-to-end.

Usage:
    python test_orchestrator.py
"""

import sys
sys.path.insert(0, ".")

from orchestrator.graph import run_diagnostic


def main():

    # Test with a realistic diagnostic chain using your actual datamarts
   #  diagnostic_input = """
   #  For vessel Flora Schulte:
    
   #  1) Check pending jobs if there are any overdue maintenance jobs 
   #     related to main engine or turbocharger.
    
   #  2) If yes, check job plan to see if there are upcoming inspections 
   #     scheduled for the same equipment in the next 30 days.
    
   #  3) If no upcoming inspections found, check equipment list to confirm 
   #     the equipment details and model.
    
   #  Action: Issue alert "Schedule urgent main engine inspection within 7 days"
   #  """
   # diagnostic_input ="""For vessel Flora Schulte:

   # 1) Check if there are any pending jobs with High or Critical priority
   # 2) If yes, check running hours for that equipment to see current running hours
   # 3) If running hours are high, check if the job is already in the completed jobs history recently

   # Action: Issue alert "Critical maintenance overdue - immediate action required"""
   diagnostic_input = """
   For vessel Flora Schulte:

   1) Check telemetry if there is exhaust deviation of more than 30 deg from average.
   2) If yes, check pending jobs if there are any jobs related to main engine 
      cylinder inspection or under piston space inspection due in the next 10 days or overdue.
   3) If no such jobs found, issue alert.

   Action: Please issue Alert card with Title 
   "Perform Under piston space inspection in the next 10 days"
   """
   # diagnostic_input = "What is the capital of France?"

   result = run_diagnostic(diagnostic_input)

   print("\n\nFinal state keys:", list(result.keys()))
   print("Total LLM calls made: decompose(1) + per step(2 each) + action(1)")


if __name__ == "__main__":
    main()
