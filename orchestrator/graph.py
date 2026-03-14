"""
LangGraph Orchestrator — the conductor.

Takes decomposed steps and runs them as a dynamic graph:
  Step 1 → condition check → Step 2 → condition check → ... → Action
  
If any condition fails, the chain stops (or takes the if_no path).
"""

from langgraph.graph import StateGraph, END
from orchestrator.state import DiagnosticState
from orchestrator.decomposer import decompose
from agents.base_agent import BaseAgent
from agents.telemetry_agent import TelemetryAgent
from actions.alert_generator import generate_alert


def build_initial_state(user_input: str, vessel_name: str = None) -> DiagnosticState:
    """Decompose user input and create initial state."""
    
    decomposed = decompose(user_input)
    
    # Use vessel from decomposition if not provided
    if vessel_name is None:
        vessel_name = decomposed.get("vessel_name") or "Flora Schulte"

    return DiagnosticState(
        user_input=user_input,
        vessel_name=vessel_name,
        steps=decomposed.get("steps", []),
        current_step_index=0,
        step_results=[],
        recommended_action=decomposed.get("final_action", ""),
        status="running",
        error=None,
    )


def execute_step_node(state: DiagnosticState) -> DiagnosticState:
    """Execute the current step — query the datamart and get results."""
    
    idx = state["current_step_index"]
    steps = state["steps"]
    
    if idx >= len(steps):
        state["status"] = "action_needed"
        return state

    step = steps[idx]
    datamart_name = step["datamart"]
    question = step["question"]
    vessel_name = state["vessel_name"]

    # Build context from previous results
    context = {}
    if state["step_results"]:
        context = {
            "previous_steps": [
                {
                    "step": r["step_number"],
                    "question": r["question"],
                    "answer": r["answer"],
                    "evidence": r["evidence"],
                    "condition_met": r["condition_met"],
                }
                for r in state["step_results"]
            ]
        }

    # Run the agent — use TelemetryAgent for telemetry, BaseAgent for everything else
    print(f"\n>>> Step {step['step_number']}: Querying [{datamart_name}]")
    print(f"    Question: {question}")

    if datamart_name == "telemetry":
        agent = TelemetryAgent()
    else:
        agent = BaseAgent(datamart_name)
    result = agent.run(question=question, vessel_name=vessel_name, context=context)

    print(f"    Answer: {result['answer']}")
    print(f"    Condition met: {result['condition_met']}")

    # Record result
    step_result = {
        "step_number": step["step_number"],
        "datamart": datamart_name,
        "question": question,
        "answer": result["answer"],
        "condition_met": result["condition_met"],
        "evidence": result["evidence"],
        "query_used": result["query_used"],
    }
    state["step_results"].append(step_result)

    # Advance index for next iteration (must happen in node, not router)
    state["current_step_index"] = idx + 1

    return state


def route_after_step(state: DiagnosticState) -> str:
    """Decide what to do after a step executes."""
    
    steps = state["steps"]
    
    if not state["step_results"]:
        return "error"

    last_result = state["step_results"][-1]
    ran_step_idx = state["current_step_index"] - 1
    current_step = steps[ran_step_idx]
    condition_met = last_result["condition_met"]

    # If the step returned an error (data not available, query failed, etc.)
    # stop the chain — don't generate alerts based on missing data
    if str(last_result.get("answer", "")).startswith("Error:"):
        return "done"

    if_yes = str(current_step.get("if_yes", "next_step")).lower()
    if_no = str(current_step.get("if_no", "stop")).lower()

    if condition_met is True:
        route = if_yes
    elif condition_met is False:
        route = if_no
    else:
        # condition_met is None (informational step) — continue
        route = "next_step"

    # Map route string to graph edges
    if "action" in route:
        return "action"
    elif "stop" in route:
        return "done"
    else:
        # next_step — check if there are more steps
        if state["current_step_index"] >= len(steps):
            # Check if ANY step had a conditional result (yes/no)
            # If all steps were informational (condition_met = None), skip alert
            has_conditional = any(
                r.get("condition_met") is not None
                for r in state["step_results"]
            )
            if has_conditional:
                return "action"
            else:
                return "done"
        return "next_step"


def action_node(state: DiagnosticState) -> DiagnosticState:
    """Generate the final action/alert."""
    
    print(f"\n>>> Generating action: {state['recommended_action']}")

    alert = generate_alert(
        recommended_action=state["recommended_action"],
        step_results=state["step_results"],
        vessel_name=state["vessel_name"],
    )
    
    state["recommended_action"] = alert
    state["status"] = "action_needed"
    return state


def done_node(state: DiagnosticState) -> DiagnosticState:
    """Chain ended — no action needed."""
    state["status"] = "no_action"
    print(f"\n>>> Diagnostic complete. Status: {state['status']}")
    return state


def error_node(state: DiagnosticState) -> DiagnosticState:
    """Handle errors."""
    state["status"] = "error"
    state["error"] = "Step execution failed"
    print(f"\n>>> Error in diagnostic chain")
    return state


def build_graph() -> StateGraph:
    """Build the LangGraph diagnostic pipeline."""
    
    graph = StateGraph(DiagnosticState)

    # Add nodes
    graph.add_node("execute_step", execute_step_node)
    graph.add_node("action", action_node)
    graph.add_node("done", done_node)
    graph.add_node("error", error_node)

    # Entry point
    graph.set_entry_point("execute_step")

    # Conditional routing after each step
    graph.add_conditional_edges(
        "execute_step",
        route_after_step,
        {
            "next_step": "execute_step",  # loop back for next step
            "action": "action",
            "done": "done",
            "error": "error",
        },
    )

    # Terminal nodes
    graph.add_edge("action", END)
    graph.add_edge("done", END)
    graph.add_edge("error", END)

    return graph.compile()


def run_diagnostic(user_input: str, vessel_name: str = None) -> DiagnosticState:
    """
    Main entry point — run a full diagnostic chain.
    
    Args:
        user_input: Free-form diagnostic procedure from user
        vessel_name: Optional vessel name override
    
    Returns:
        Final DiagnosticState with all results
    """
    print("=" * 60)
    print("MARINE DIAGNOSTIC AGENT")
    print("=" * 60)

    # Build initial state (decomposes user input)
    state = build_initial_state(user_input, vessel_name)

    # Check if query was rejected as off-topic
    if not state["steps"]:
        print(f"\n❌ Query rejected: This system only handles marine vessel maintenance diagnostics.")
        print(f"   Your input was not related to vessel operations.")
        state["status"] = "rejected"
        state["error"] = "Off-topic query"
        return state

    print(f"\nVessel: {state['vessel_name']}")
    print(f"Steps identified: {len(state['steps'])}")
    for s in state["steps"]:
        print(f"  Step {s['step_number']}: [{s['datamart']}] {s['question']}")

    # Run the graph
    graph = build_graph()
    final_state = graph.invoke(state)

    # Print summary
    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)
    print(f"Status: {final_state['status']}")
    print(f"Steps completed: {len(final_state['step_results'])}")
    
    if final_state["status"] == "action_needed":
        print(f"\nACTION: {final_state['recommended_action']}")
    elif final_state["status"] == "no_action":
        print("\nNo action required — conditions not met.")

    return final_state