"""
State that flows through the diagnostic pipeline.
Each agent reads from and writes to this shared state.
"""

from typing import TypedDict, Optional


class StepResult(TypedDict):
    step_number: int
    datamart: str
    question: str
    answer: str
    condition_met: Optional[bool]
    evidence: str
    query_used: str


class DiagnosticState(TypedDict):
    # Input
    user_input: str
    vessel_name: str

    # Decomposed steps from user input
    steps: list[dict]  # [{step_number, datamart, question, condition, if_yes, if_no}]

    # Current position in the chain
    current_step_index: int

    # Accumulated results from each completed step
    step_results: list[StepResult]

    # Final action to take (if chain completes)
    recommended_action: str

    # Status
    status: str  # "running", "action_needed", "no_action", "error"
    error: Optional[str]
