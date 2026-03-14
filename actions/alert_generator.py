"""
Alert Generator — produces the final action card from diagnostic results.
"""

import json
from config.llm_client import chat


def generate_alert(recommended_action: str, step_results: list, vessel_name: str) -> str:
    """
    Generate a formatted alert card based on diagnostic chain results.
    
    Returns:
        Formatted alert string
    """
    # Build evidence summary
    evidence_summary = []
    for r in step_results:
        evidence_summary.append({
            "step": r["step_number"],
            "check": r["question"],
            "result": r["answer"],
            "evidence": r["evidence"],
        })

    messages = [
        {
            "role": "system",
            "content": """You are a marine maintenance alert generator.
Based on diagnostic chain results, generate a clear alert card.

Format the alert as:
ALERT CARD
Title: [title]
Vessel: [vessel name]
Priority: [High/Medium/Low based on findings]
Summary: [2-3 sentence summary of what was found]
Evidence:
- [key finding 1]
- [key finding 2]
Recommended Action: [clear action to take]

Return ONLY the formatted alert text."""
        },
        {
            "role": "user",
            "content": f"""Vessel: {vessel_name}
Recommended action from user: {recommended_action}

Diagnostic evidence:
{json.dumps(evidence_summary, indent=2, default=str)}"""
        }
    ]

    try:
        return chat(messages, temperature=0.0)
    except Exception as e:
        # Fallback — plain text alert
        return f"""ALERT CARD
Title: {recommended_action}
Vessel: {vessel_name}
Priority: Medium
Summary: Diagnostic chain completed. Action recommended based on findings.
Recommended Action: {recommended_action}"""
