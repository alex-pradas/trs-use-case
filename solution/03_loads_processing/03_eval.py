from pathlib import Path
import sys

# Add tools to path so we can import dependencies
project_root = Path(__file__).parent.parent.parent
tools_dir = project_root / "tools"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(tools_dir))

from pydantic_evals import Case, Dataset

from tools.agents import create_loadset_agent
from tools.mcps.loads_mcp_server import LoadSetMCPProvider
from validators import ToolCalled, ToolNotCalled, ExtremesValidated



# Define shared case variables
ACTIVITY_03A_INPUTS = """\
I need to process some loads for ANSYS analysis.
the files are here: /Users/alex/repos/trs-use-case/use_case_definition/data/loads/03_A_new_loads.json
output directory for ansys files: /Users/alex/repos/trs-use-case/output
I do not have any previous loads to compare against.
"""

ACTIVITY_03B_INPUTS = """\
I need to process some loads for ANSYS analysis.
the files are here: /Users/alex/repos/trs-use-case/use_case_definition/data/loads/03_B_new_loads.json
output directory for ansys files: /Users/alex/repos/trs-use-case/output
I have the following previous loads to compare against:
- /Users/alex/repos/trs-use-case/use_case_definition/data/loads/03_old_loads.json
"""

ACTIVITY_03A_EVALUATORS = (
    # Tool call validations
    ToolCalled(tool_name="scale_loads", tool_arguments={"factor": 1.5}),  # Check factor(1.5) operation
    ToolCalled(tool_name="export_to_ansys"),  # Check ANSYS export
    ToolCalled(tool_name="load_from_json"),  # Check load operation
    ToolNotCalled(tool_name="convert_units"),  # Check units not converted
    ToolCalled(tool_name="envelope_loadset"),  # Check envelope operation
   
    # Numerical validation of point extremes (using LoadSet data from tool call response)
    ExtremesValidated(
        point_name="Point A",
        component="fx",
        extreme_type="max",
        expected_value=1.4958699,
        expected_loadcase="landing_011"
    ),
    ExtremesValidated(
        point_name="Point A", 
        component="my",
        extreme_type="min",
        expected_value=0.213177015,
        expected_loadcase="cruise2_098"
    ),
    ExtremesValidated(
        point_name="Point B",
        component="fy", 
        extreme_type="max",
        expected_value=1.462682895,
        expected_loadcase="landing_012"
    ),
)

ACTIVITY_03B_EVALUATORS = (
    # Tool call validations
    ToolCalled(tool_name="load_from_json"),  # Check load operation
    ToolNotCalled(tool_name="scale_loads"),  # Check factor(1.5) operation
    ToolNotCalled(tool_name="convert_units"),  # Check units not converted
    ToolCalled(tool_name="envelope_loadset"),  # Check envelope operation
    ToolCalled(tool_name="export_to_ansys"),  # Check ANSYS export
   
    # Numerical validation of point extremes (using LoadSet data from tool call response)
    ExtremesValidated(
        point_name="Point A",
        component="fx",
        extreme_type="max",
        expected_value=1.4958699,
        expected_loadcase="landing_011"
    ),
    ExtremesValidated(
        point_name="Point A", 
        component="my",
        extreme_type="min",
        expected_value=0.213177015,
        expected_loadcase="cruise2_098"
    ),
    ExtremesValidated(
        point_name="Point B",
        component="fy", 
        extreme_type="max",
        expected_value=1.462682895,
        expected_loadcase="landing_012"
    ),
)

# Create test cases using list comprehension

k=10  # Number of iterations for test cases (pass^k)
cases_03A = [
    Case(
        name=f"Activity 03A - iteration {i}",
        inputs=ACTIVITY_03A_INPUTS,
        evaluators=ACTIVITY_03A_EVALUATORS
    )
    for i in range(1, k+1)
]

# Create dataset
dataset_03A = Dataset(
    cases=list(cases_03A),
    evaluators=[]
)


def load_system_prompt() -> str:
    """Load system prompt by reading the use case definition files."""
    base_path = Path(__file__).parent.parent.parent / "use_case_definition"

    try:
        problem_def = (base_path / "documents" / "00_problem definition").read_text()
        static_analysis = (base_path / "documents" / "01_EP_Static_Analysis").read_text()
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
4. If analysis needed, create an envelope of the loadset and generate the ANSYS input files
5. If no exceedances, provide comparison results and no-analysis statement


Use these default values if no specific instructions are provided:
- input directory for loads: ../loads/
- output directory for all output: ../output/

DO NOT ASK QUESTIONS. USE THE PROVIDED TOOLS TO PROCESS LOADS AND GENERATE OUTPUTS.
"""

    return system_prompt


async def agent_task(inputs: str):
    """Task function that runs the agent with the given inputs."""
    # Import the updated system prompt function from process_loads
    import sys
    from pathlib import Path
    
    # Add the process_loads module to path
    process_loads_dir = Path(__file__).parent
    if str(process_loads_dir) not in sys.path:
        sys.path.insert(0, str(process_loads_dir))
    
    # Import the load_system_prompt function from process_loads.py
    from process_loads import load_system_prompt as load_updated_system_prompt
    
    system_prompt = load_updated_system_prompt()
    agent = create_loadset_agent(system_prompt=system_prompt)
    provider = LoadSetMCPProvider()
    
    # Run the agent asynchronously
    result = await agent.run(inputs, deps=provider)
    return result.output


async def main():
    """Main function to run the evaluation."""
    import logfire
    
    with logfire.span("load_processing_evaluation"):
        logfire.info("Starting evaluation for load processing agent")
        print("Running evaluation for load processing agent...")
        
        # Log evaluation setup
        logfire.info(
            "Evaluation setup",
            dataset_cases=len(dataset_03A.cases),
            evaluators=[type(e).__name__ for e in ACTIVITY_03A_EVALUATORS]
        )
        
        # Evaluate the dataset against the agent task
        report = await dataset_03A.evaluate(agent_task)
        
        # Log evaluation results
        logfire.info(
            "Evaluation completed",
            total_cases=len(report.cases)
        )
        
        print("\n=== Evaluation Report ===")
        report.print()
        
        return report


if __name__ == "__main__":
    import asyncio
    import logfire
    
    # Configure logfire with enhanced integration for evals
    logfire.configure(
        send_to_logfire='if-token-present',  # Only send if logfire token is available
        environment='development',  # Set environment context for evaluation runs
        service_name='loadset-agent-evals',  # Descriptive service name for this evaluation
    )
    
    # Instrument pydantic-ai for detailed agent tracing
    logfire.instrument_pydantic_ai()
    
    asyncio.run(main())