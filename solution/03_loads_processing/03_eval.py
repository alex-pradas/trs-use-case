from os import wait
from pathlib import Path
import sys

# Add tools to path so we can import dependencies
project_root = Path(__file__).parent.parent.parent
tools_dir = project_root / "tools"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(tools_dir))

# pydantic_evals imports are now handled by the activities package

from tools.agents import create_loadset_agent
from tools.mcps.loads_mcp_server import LoadSetMCPProvider
from activities import ActivityRegistry  # This triggers auto-registration of all activities


# All activity definitions are now in the activities/ package
# Activities are auto-registered when the activities package is imported


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
4. If old loads are provided by user, compare new loads with previous applicable loads.
5. Determine if detailed analysis is needed based on load exceedance (if old loads are provided)
    6a. If a new analysis is needed, create an envelope of the loadset and generate the ANSYS input files
    6b. If no exceedances, provide comparison results and no-analysis statement

DO NOT ASK QUESTIONS. USE THE PROVIDED TOOLS TO PROCESS LOADS AND GENERATE OUTPUTS.
"""

async def agent_task(inputs: str, model_override: str | None = None):
    """Task function that runs the agent with the given inputs."""
    # Import the updated system prompt function from process_loads
    import sys
    from pathlib import Path
    
    # Add the process_loads module to path
    process_loads_dir = Path(__file__).parent
    if str(process_loads_dir) not in sys.path:
        sys.path.insert(0, str(process_loads_dir))
    
    # Using SIMPLE_SYSTEM_PROMPT for consistent behavior
    system_prompt = SIMPLE_SYSTEM_PROMPT
    agent = create_loadset_agent(system_prompt=system_prompt, model_override=model_override)
    provider = LoadSetMCPProvider()
    
    # Run the agent asynchronously
    result = await agent.run(inputs, deps=provider)
    return result.output


async def main(activities: list[str] | None = None, model_name: str | None = None):
    """Main function to run the evaluation for specified activities."""
    import logfire
    import asyncio
    
    # Auto-discover available activities if none specified
    if activities is None:
        activities = ActivityRegistry.list_activities()
        print(f"Auto-discovered activities: {activities}")
    
    with logfire.span("load_processing_evaluation"):
        logfire.info("Starting evaluation for load processing agent", activities=activities)
        print(f"Running evaluation for activities: {', '.join(activities)}")
        
        reports = {}
        wait_time = 0  # Waiting time to avoid hitting token limits at anthropic
        
        for i, activity in enumerate(activities):
            try:
                # Get dataset and evaluators from registry
                dataset = ActivityRegistry.create_dataset(activity)
                evaluators = ActivityRegistry.get_evaluators(activity)
                
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
                
                # Create a wrapper function with model override if specified
                if model_name:
                    # Create a wrapper that captures the model_name
                    current_model = model_name  # Capture in closure
                    async def task_func(inputs: str):
                        return await agent_task(inputs, model_override=current_model)
                else:
                    task_func = agent_task
                
                report = await dataset.evaluate(task_func)
                
                logfire.info(
                    f"Activity {activity} evaluation completed",
                    total_cases=len(report.cases)
                )
                
                print(f"\n=== Activity {activity} Report ===")
                report.print()
                
                reports[activity] = report
                
            except ValueError as e:
                print(f"Error: {e}")
                continue
        
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
    
    # ===============================================
    # MODEL CONFIGURATION
    # ===============================================
    # Uncomment ONE of the following model configurations:
    
    # 1. Anthropic Claude Haiku (Current Default)
    model_name = "anthropic:claude-3-haiku-20240307"  # Uses default from environment
    
    # 2. Anthropic Sonnet 4
    # model_name = "anthropic:claude-4-sonnet-20250514"
    
    # 3. Built-in Local Model (Ollama example)
    # model_name = "openai:qwen2.5-coder:7b"
    # Note: You need to configure Ollama and update OpenAIProvider base_url
    
    # 4. Kimi K2 (requires proper provider configuration)
    # model_name = "openai:kimi-k2"
    # Note: You need to configure the provider for Kimi API
    
    # ===============================================
    # ACTIVITY CONFIGURATION
    # ===============================================
    # Configure which activities to run
    activities = ["03B"]  # Run specific activities
    # activities = ["03A"]      # Run only Activity 03A
    # activities = ["03B"]      # Run only Activity 03B
    # activities = None         # Auto-discover all available activities
    
    # Print configuration
    if model_name:
        print(f"🤖 Using model override: {model_name}")
    else:
        print("🤖 Using default model from environment")
    
    asyncio.run(main(activities, model_name))