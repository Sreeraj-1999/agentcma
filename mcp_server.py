"""
MCP Server for Marine Diagnostic Agent.

Exposes the diagnostic pipeline as MCP tools that any client
(Claude Desktop, custom UI, etc.) can call.

Usage:
    python mcp_server.py

Add to Claude Desktop config (claude_desktop_config.json):
{
    "mcpServers": {
        "marine-diagnostic": {
            "command": "python",
            "args": ["/full/path/to/mcp_server.py"]
        }
    }
}
"""

import sys
import json
sys.path.insert(0, ".")

from mcp.server.fastmcp import FastMCP
from orchestrator.graph import run_diagnostic
from agents.base_agent import BaseAgent
from datamarts.executor import list_datamarts, get_schema_description
from datamarts.csv_reader import get_vessel_names, load_datamart


# Initialize MCP server
mcp = FastMCP("Marine Diagnostic Agent")


@mcp.tool()
def run_diagnostic_chain(diagnostic_input: str, vessel_name: str = None) -> str:
    """
    Run a full multi-step diagnostic chain.
    
    The user provides a natural language diagnostic procedure with conditional steps.
    The system decomposes it, queries the appropriate datamarts, and generates alerts.
    
    Example input:
        "For vessel Flora Schulte:
        1) Check if there are pending critical priority jobs
        2) If yes, check if those jobs were completed recently
        3) If not completed, issue alert"
    
    Args:
        diagnostic_input: Free-form natural language diagnostic chain
        vessel_name: Optional vessel name (auto-detected from input if not provided)
    """
    try:
        result = run_diagnostic(diagnostic_input, vessel_name)
        
        output = {
            "status": result["status"],
            "vessel": result["vessel_name"],
            "steps_completed": len(result["step_results"]),
            "step_details": [
                {
                    "step": r["step_number"],
                    "datamart": r["datamart"],
                    "question": r["question"],
                    "answer": r["answer"],
                    "condition_met": r["condition_met"],
                }
                for r in result["step_results"]
            ],
        }

        if result["status"] == "action_needed":
            output["alert"] = result["recommended_action"]
        elif result["status"] == "rejected":
            output["message"] = "Query rejected — not related to marine vessel maintenance."
        else:
            output["message"] = "No action required — conditions not met."

        return json.dumps(output, indent=2, default=str)

    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def query_datamart(datamart_name: str, question: str, vessel_name: str = None) -> str:
    """
    Ask a natural language question against a specific datamart.
    
    Available datamarts: telemetry, job_plan, pending_jobs, completed_jobs, voyage_plan, equipment, running_hours
    
    Example: query_datamart("pending_jobs", "What jobs are overdue?", "Flora Schulte")
    Example: query_datamart("telemetry", "What is the current main engine RPM?", "Flora Schulte")
    
    Args:
        datamart_name: Name of the datamart to query
        question: Natural language question
        vessel_name: Optional vessel name filter
    """
    try:
        if datamart_name == "telemetry":
            from agents.telemetry_agent import TelemetryAgent
            agent = TelemetryAgent()
        else:
            agent = BaseAgent(datamart_name)
        result = agent.run(question=question, vessel_name=vessel_name)
        
        output = {
            "datamart": datamart_name,
            "question": question,
            "vessel": vessel_name,
            "answer": result["answer"],
            "condition_met": result["condition_met"],
            "evidence": result["evidence"],
            "query_used": result["query_used"],
        }
        
        if result["raw_data"]:
            output["sample_data"] = result["raw_data"][:5]

        return json.dumps(output, indent=2, default=str)

    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def list_available_datamarts() -> str:
    """List all available datamarts and their descriptions."""
    datamarts = list_datamarts()
    return json.dumps(datamarts, indent=2)


@mcp.tool()
def list_vessels(datamart_name: str = "pending_jobs") -> str:
    """
    List all vessel names available in the data.
    
    Args:
        datamart_name: Which datamart to check for vessel names (default: pending_jobs)
    """
    try:
        vessels = get_vessel_names(datamart_name)
        return json.dumps({"vessels": vessels}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def get_datamart_schema(datamart_name: str) -> str:
    """
    Get the schema description of a datamart (column names, types, descriptions).
    
    Args:
        datamart_name: Name of the datamart
    """
    try:
        return get_schema_description(datamart_name)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


if __name__ == "__main__":
    mcp.run()