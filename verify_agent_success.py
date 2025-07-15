#!/usr/bin/env python3
"""
Verify that the AI agent successfully completed the aerospace load processing workflow.
"""

from tools.mcps.python_exec_mcp_server import create_mcp_server
from tests.test_python_exec_agent_integration import PythonExecutionMCPTestAgent
import json


def main():
    # Create the same agent setup as the test
    server = create_mcp_server()
    agent = PythonExecutionMCPTestAgent(server, disable_security=True)

    print("🔍 Checking what the AI agent accomplished...\n")

    # Get execution history
    history = agent.call_tool_directly("get_execution_history", limit=10)
    if not history["success"]:
        print("❌ Failed to get execution history")
        return

    executions = history["tool_result"]["history"]
    print(f"📊 Total code executions: {len(executions)}")
    print(f"✅ Successful executions: {sum(1 for e in executions if e['success'])}")
    print(f"❌ Failed executions: {sum(1 for e in executions if not e['success'])}")

    # Show what the agent did
    print("\n🤖 AI Agent's Code Generation and Execution:")
    for i, entry in enumerate(executions, 1):
        status = "✅" if entry["success"] else "❌"
        print(
            f"\n{status} Execution {i} ({'SUCCESS' if entry['success'] else 'FAILED'}):"
        )
        print("Code:")
        print(entry["code"])

        if entry["stdout"]:
            print("Output:")
            print(entry["stdout"])

        if entry["error"]:
            print("Error:")
            print(entry["error"])

        print("-" * 50)

    # Check current variables
    variables = agent.call_tool_directly("list_variables")
    if variables["success"]:
        var_names = list(variables["tool_result"]["variables"].keys())
        print(f"\n📋 Variables created by agent: {len(var_names)}")
        for name in var_names:
            var_info = variables["tool_result"]["variables"][name]
            print(f"  - {name}: {var_info['type']}")

        # Look for LoadSet-related variables
        loadset_vars = [v for v in var_names if "load" in v.lower()]
        if loadset_vars:
            print(f"\n🚀 LoadSet variables found: {loadset_vars}")

            # Get details on a LoadSet variable if available
            for var in loadset_vars:
                if "LoadSet" in variables["tool_result"]["variables"][var]["type"]:
                    var_detail = agent.call_tool_directly("get_variable", name=var)
                    if var_detail["success"]:
                        print(f"\n📊 {var} details:")
                        print(
                            f"  Type: {var_detail['tool_result']['variable_info']['type']}"
                        )
                        print(
                            f"  Value preview: {var_detail['tool_result']['variable_info']['value'][:200]}..."
                        )

    # Check for workflow evidence
    all_code = " ".join([e["code"] for e in executions]).lower()
    workflow_elements = [
        ("LoadSet.read_json", "Load data from JSON"),
        ("convert_to", "Unit conversion"),
        ("factor", "Load scaling"),
        ("compare_to", "LoadSet comparison"),
        ("json", "JSON operations"),
    ]

    print(f"\n🔍 Workflow Analysis:")
    for element, description in workflow_elements:
        found = element.lower() in all_code
        status = "✅" if found else "❌"
        print(f"  {status} {description}: {'Found' if found else 'Not found'}")

    print(f"\n🎯 Agent Performance Summary:")
    successful_elements = sum(
        1 for element, _ in workflow_elements if element.lower() in all_code
    )
    print(
        f"  - Workflow completeness: {successful_elements}/{len(workflow_elements)} elements"
    )
    print(
        f"  - Code execution success rate: {sum(1 for e in executions if e['success'])}/{len(executions)}"
    )

    if successful_elements >= 3 and sum(1 for e in executions if e["success"]) >= 3:
        print(
            f"\n🎉 SUCCESS: AI Agent successfully demonstrated autonomous aerospace load processing!"
        )
        print(f"    - Generated and executed Python code for real aerospace data")
        print(f"    - Performed unit conversions and load scaling")
        print(f"    - Worked with LoadSet objects and methods")
        print(f"    - Maintained persistent state across multiple executions")
    else:
        print(
            f"\n⚠️  Partial success: Agent made progress but didn't complete full workflow"
        )


if __name__ == "__main__":
    main()
