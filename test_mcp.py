"""
Test MCP tools directly — no Claude Desktop needed.
This imports and calls the same functions the MCP server exposes.

Usage:
    python test_mcp.py
"""

import sys
sys.path.insert(0, ".")

from mcp_server import (
    list_available_datamarts,
    list_vessels,
    query_datamart,
    run_diagnostic_chain,
)


def main():
    print("=== MCP Tools Test ===\n")

    # Tool 1: List datamarts
    print("--- Tool: list_available_datamarts ---")
    print(list_available_datamarts())
    print()

    # Tool 2: List vessels
    print("--- Tool: list_vessels ---")
    print(list_vessels())
    print()

    # Tool 3: Single datamart query
    print("--- Tool: query_datamart ---")
    result = query_datamart("pending_jobs", "What critical priority jobs are pending?", "Flora Schulte")
    print(result)
    print()

    # Tool 4: Full diagnostic chain
    print("--- Tool: run_diagnostic_chain ---")
    result = run_diagnostic_chain(
        """For vessel Franz Schulte:
        1) Check voyage plan - what is the next port?
        2) Check pending jobs due before arrival
        Action: Issue pre-arrival checklist""",
        "Franz Schulte"
    )
    print(result)


if __name__ == "__main__":
    main()