"""
TRS Load Processing Agent with Dynamic System Prompt

This module implements a Pydantic AI agent for processing TRS loads according to EP Static Analysis procedures.
The system prompt is dynamically loaded from use case definition files to ensure it always reflects current procedures.
Uses the Loads MCP server for all load processing operations.
"""

from math import log
from pathlib import Path
import sys
from dotenv import load_dotenv

from pydantic_ai.messages import ToolCallPart

# Load environment variables
load_dotenv()

# Add tools to path so we can import dependencies
project_root = Path(__file__).parent.parent.parent
tools_dir = project_root / "tools"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(tools_dir))

# ruff: noqa: E402
from tools.agents import create_loadset_agent
from tools.mcps.loads_mcp_server import LoadSetMCPProvider


def load_system_prompt() -> str:
    """
    Load system prompt by reading the use case definition files.

    This ensures the system prompt always reflects the current state of:
    - Problem definition
    - EP Static Analysis procedures

    Returns:
        str: Combined system prompt from all three files
    """
    base_path = Path(__file__).parent.parent.parent / "use_case_definition"

    try:
        problem_def = (base_path / "00_problem definition").read_text()
        static_analysis = (base_path / "01_EP_Static_Analysis").read_text()
    except FileNotFoundError as e:
        raise ValueError(f"Could not load use case definition files: {e}") from e

    # Combine into comprehensive system prompt using modern f-string syntax
    system_prompt = f"""\
You are a structural analysis expert specializing in processing loads for aerospace components.

Your task is to support the user to manipulate and prepare the loads for a FEM analysis in ANSYS, following the EP Static Analysis procedures.

PROBLEM DEFINITION:
{problem_def}

STATIC ANALYSIS PROCEDURES:
{static_analysis}

Based on this context, you will help process loads and perform structural analysis tasks according to the EP Static Analysis procedures.
You have access to the LoadSet MCP server functions.

Key Operations required:
1. Process loads from customer format and convert units if required (N and Nm)
2. Factor in safety margins (1.5 for ultimate loads) if appropriate
2. Compare new loads with previous applicable loads, if old loads are provided by user.
3. Determine if detailed analysis is needed (if old loads are provided)
4. If analysis needed:
   4.1 Create an envelope of the loadset (via get_point_extremes) 
   4.2 Generate the ANSYS input files
5. If no exceedances, provide comparison results and no-analysis statement


Use these default values if no specific instructions are provided:
- input directory for loads: ../loads/
- output directory for all output: ../output/

DO NOT ASK QUESTIONS. USE THE PROVIDED TOOLS TO PROCESS LOADS AND GENERATE OUTPUTS.

Remember to call tool get_point_extremes!!!
"""

    return system_prompt


USER_PROMPT_1 = """\
I need to process some loads for ANSYS analysis.
the files are here: /Users/alex/repos/trs-use-case/solution/loads/03_01_new_loads.json
I do not have any previous loads to compare against.
"""

USER_PROMPT_2 = """\
I need to process some loads for ANSYS analysis.
the files are here: /Users/alex/repos/trs-use-case/solution/loads/03_02_new_loads.json
old files are here: /Users/alex/repos/trs-use-case/solution/loads/03_03_old_loads.json
"""

def main() -> None:
    """Main function to run the load processing workflow."""
    # Load custom system prompt
    system_prompt = load_system_prompt()

    # Create agent with custom system prompt and direct provider
    agent = create_loadset_agent(system_prompt=system_prompt)
    provider = LoadSetMCPProvider()

    logfire.log("info","Step 3, Scenario 1")
    # Run the agent with direct provider injection
    result = agent.run_sync(USER_PROMPT_1, deps=provider)

    print("\n=== Load Processing Results for USER_PROMPT_1 ===")

    # This codeblock is a prototype of testing what calls were made to the MCP server.
    messages = result.all_messages()
    tool_calls = [
        part for message in messages
        for part in message.parts
        if isinstance(part, ToolCallPart)
    ]
    if tool_calls:
        for tool_call in tool_calls:
            print(f"  * Called {tool_call.tool_name} with args: {tool_call.args}")

    print(f"Result: {result.output}")

    logfire.log("info", "Step 3, Scenario 2")
    # Run the agent with direct provider injection
    result = agent.run_sync(USER_PROMPT_2, deps=provider)

    print("\n=== Load Processing Results for USER_PROMPT_2 ===")
    print(f"Result: {result.output}")



if __name__ == "__main__":
    import logfire

    logfire.configure(environment='test')
    logfire.instrument_pydantic_ai()

    # Run the main function
    main()
