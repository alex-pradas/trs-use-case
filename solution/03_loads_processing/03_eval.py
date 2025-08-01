from os import wait
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
I have the following previous (old)loads to compare against: /Users/alex/repos/trs-use-case/use_case_definition/data/loads/03_old_loads.json
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
    ToolCalled(tool_name="load_from_json"),  
    ToolCalled(tool_name="convert_units"),  
    ToolNotCalled(tool_name="scale_loads"),
    ToolCalled(tool_name="load_second_loadset"), 
    ToolCalled(tool_name="compare_loadsets"), 
    ToolCalled(tool_name="generate_comparison_charts"), 
   
    # Numerical validation of point extremes (using LoadSet data from tool call response)
    ExtremesValidated(
        point_name="Point A",
        component="fx",
        extreme_type="max",
        expected_value=6.6539613983178,
        expected_loadcase="landing_011"
    ),
    ExtremesValidated(
        point_name="Point A", 
        component="my",
        extreme_type="min",
        expected_value=0.28902923412327,
        expected_loadcase="cruise2_098"
    ),
    ExtremesValidated(
        point_name="Point B",
        component="fy", 
        extreme_type="max",
        expected_value=6.506338232562691,
        expected_loadcase="landing_012"
    ),
)

# Create test cases using list comprehension

k=5  # Number of iterations for test cases (pass^k)
cases_03A = [
    Case(
        name=f"Activity 03A - iteration {i}",
        inputs=ACTIVITY_03A_INPUTS,
    )
    for i in range(1, k+1)
]

cases_03B = [
    Case(
        name=f"Activity 03B - iteration {i}",
        inputs=ACTIVITY_03B_INPUTS,
    )
    for i in range(1, k+1)
]

# Create datasets
dataset_03A = Dataset(
    cases=list(cases_03A),
    evaluators=ACTIVITY_03A_EVALUATORS
)

dataset_03B = Dataset(
    cases=list(cases_03B),
    evaluators=ACTIVITY_03B_EVALUATORS
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

SIMPLE_SYSTEM_PROMPT = """\
You are a structural analysis expert specializing in processing loads for aerospace components.

Your task is to support the user to manipulate and prepare the loads for a FEM analysis in ANSYS.

## Loads Processing (General Context)

If no information about the loads exist, they should be assumed that they are limit loads and therefore be multiplied by a safety factor of 1.5 to obtain the ultimate loads. This is an important step: limit loads have been used for an ultimate analysis in the past because it was assumed that the loads were ultimate.
Paying attention to loads units is critical. Our FEM models uses SI units (N N/m). If loads are provided in other units, they must always be converted to N and Nm for forces and moments respectively. The conversion factor is 1 klb = 4448.22 N and 1 klb-ft = 1.35582 Nm.
It is standard practice to always check new loads and compare it with a pre-existing set of previous applicable loads delivered by the customer. If they exceed, we need to perform a new analysis. But if none of the loads exceed and the geometry and all other inputs are the same, a complete analysis is not needed, simply the loads comparison results and an statement instead. 
If the new loads exceed in any direction, then the envelope of old and new files need to be performed and that will be the collection of load cases that will be evaluated in the FEM analysis. If no loads exceed, no new analysis is needed and the final report shall contain the load comparison results and a statement indicating that no further analysis is needed.
The loads needs to be translated from the customer format to an ANSYS format readable by ANSYS. Each load case is stored in an individual file and then read directly, one by one, into ANSYS in a load-solve-release loop iteration.
The complete load set shall be reduced by applying a envelope operation, typically done during the loads processing activities. This operation dowselects the load cases as it remove those that are not max or min in any force or moment direction. It is best to create only the ansys load files corresponding to the envelope of the load set, as this will reduce the number of load cases to be evaluated in the FEM analysis.

Care shall be taken to ensure that the coordinates provided by the customer match the coordinates used in the FEM model. If they do not match, the loads must be transformed to the FEM model coordinates.

## Specific instructions for Loads Processing

Based on this context, you will help process loads and perform structural analysis tasks according to the EP Static Analysis procedures.
You have access to the LoadSet MCP server functions.

Key Operations required:
1. Process loads from customer format and convert units IF REQUIRED to our internal convention of N and Nm.
2. Factor in safety margins (1.5 for ultimate loads) if appropriate
3. Envelope loadset to reduce the number of load cases
4. Compare new loads with previous applicable loads, if old loads are provided by user.
5. Determine if detailed analysis is needed (if old loads are provided)
    6a. If a new analysis is needed, create an envelope of the loadset and generate the ANSYS input files
    6b. If no exceedances, provide comparison results and no-analysis statement
"""

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
    
    system_prompt = SIMPLE_SYSTEM_PROMPT
    agent = create_loadset_agent(system_prompt=system_prompt)
    provider = LoadSetMCPProvider()
    
    # Run the agent asynchronously
    result = await agent.run(inputs, deps=provider)
    return result.output


async def main(activities: list[str] = ["03A", "03B"]):
    """Main function to run the evaluation for specified activities."""
    import logfire
    import asyncio
    
    # Activity mapping
    activity_config = {
        "03A": {
            "dataset": dataset_03A,
            "evaluators": ACTIVITY_03A_EVALUATORS
        },
        "03B": {
            "dataset": dataset_03B,
            "evaluators": ACTIVITY_03B_EVALUATORS
        }
    }
    
    with logfire.span("load_processing_evaluation"):
        logfire.info("Starting evaluation for load processing agent", activities=activities)
        print(f"Running evaluation for activities: {', '.join(activities)}")
        
        reports = {}
        wait_time = 120  # Waiting time to avoid hitting token limits at anthropic
        
        for i, activity in enumerate(activities):
            if activity not in activity_config:
                print(f"Warning: Unknown activity '{activity}', skipping...")
                continue
                
            config = activity_config[activity]
            dataset = config["dataset"]
            evaluators = config["evaluators"]
            
            # Add wait time between activities (but not before the first one)
            if i > 0:
                print(f"Waiting {wait_time} seconds before starting Activity {activity}...")
                await asyncio.sleep(wait_time)
            
            # Evaluate the activity
            print(f"\n=== Activity {activity} Evaluation ===")
            logfire.info(
                f"Activity {activity} evaluation setup",
                dataset_cases=len(dataset.cases),
                evaluators=[type(e).__name__ for e in evaluators]
            )
            
            report = await dataset.evaluate(agent_task)
            
            logfire.info(
                f"Activity {activity} evaluation completed",
                total_cases=len(report.cases)
            )
            
            print(f"\n=== Activity {activity} Report ===")
            report.print()
            
            reports[activity] = report
        
        return reports


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
    
    # Configure which activities to run
    # activities = ["03A", "03B"]  # Change this list to run specific activities
    # activities = ["03A"]      # Run only Activity 03A
    activities = ["03B"]      # Run only Activity 03B
    
    asyncio.run(main(activities))