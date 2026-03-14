"""
Decomposer — takes free-form natural language diagnostic chain
and breaks it into structured steps the orchestrator can execute.
"""

import json
from config.llm_client import chat


DECOMPOSE_PROMPT = """You are a diagnostic chain planner for marine vessel maintenance.

The user will give you a free-form diagnostic procedure. Break it into ordered steps.

Available datamarts:
- telemetry: Sensor readings from vessel (PostgreSQL — skip if not relevant)
- job_plan: Planned maintenance jobs with schedules and frequencies
- pending_jobs: Pending/overdue maintenance job orders
- completed_jobs: Historical completed job records
- voyage_plan: Voyage legs, port calls, ETAs
- equipment: Equipment master list (makers, models, hierarchy codes)
- running_hours: Equipment running hour counter readings

For each step, identify:
1. Which datamart to query
2. What question to ask (natural language)
3. What condition determines yes/no
4. What happens on yes vs no

CRITICAL LOGIC RULES:
- if_yes and if_no must be one of: "next_step", "action", or "stop"
- Think carefully about WHEN the action should trigger.
- Sometimes the ABSENCE of something is the danger signal:
  Example: "If job NOT completed recently → issue alert" means if_no = "action"
  Example: "If no pending inspection found → take action" means if_no = "action"
- Sometimes the PRESENCE of something is the danger signal:
  Example: "If overdue jobs exist → issue alert" means if_yes = "action"
- The final step should usually route to "action" on the dangerous condition,
  and "stop" on the safe condition.
- Read the user's intent carefully: what situation triggers the alert?

Also extract:
- The vessel name if mentioned
- The final action/recommendation if mentioned

Respond with ONLY valid JSON in this exact format:
{
    "vessel_name": "vessel name or null if not specified",
    "steps": [
        {
            "step_number": 1,
            "datamart": "datamart_name",
            "question": "natural language question to ask this datamart",
            "condition": "what makes this step YES",
            "if_yes": "next_step or action or stop",
            "if_no": "stop or action or next_step"
        }
    ],
    "final_action": "the recommended action/alert if all conditions are met"
}

No markdown, no explanation. ONLY JSON.

IMPORTANT: If the user's input is NOT related to marine vessel maintenance, diagnostics, 
equipment, jobs, voyages, or any maritime operational topic, respond with:
{
    "vessel_name": null,
    "steps": [],
    "final_action": "",
    "rejected": true,
    "rejection_reason": "This system only handles marine vessel maintenance diagnostics."
}"""


def decompose(user_input: str) -> dict:
    """
    Break user's free-form diagnostic chain into structured steps.
    
    Returns:
        {
            "vessel_name": str or None,
            "steps": [...],
            "final_action": str
        }
    """
    messages = [
        {"role": "system", "content": DECOMPOSE_PROMPT},
        {"role": "user", "content": user_input},
    ]

    try:
        response = chat(messages, temperature=0.0)
        response = response.strip()
        response = response.removeprefix("```json").removeprefix("```")
        response = response.removesuffix("```")
        parsed = json.loads(response.strip())

        # Check if query was rejected as off-topic
        if parsed.get("rejected"):
            return {
                "vessel_name": None,
                "steps": [],
                "final_action": "",
                "rejected": True,
                "rejection_reason": parsed.get("rejection_reason", "Off-topic query"),
            }

        return parsed
    except Exception as e:
        return {
            "vessel_name": None,
            "steps": [],
            "final_action": "",
            "error": str(e),
        }