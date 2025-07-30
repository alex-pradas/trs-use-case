from dataclasses import dataclass
from pathlib import Path
import sys

# Add tools to path so we can import dependencies
project_root = Path(__file__).parent.parent.parent
tools_dir = project_root / "tools"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(tools_dir))

from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import Evaluator, EvaluatorContext
from pydantic_evals.otel import SpanQuery

from tools.agents import create_loadset_agent
from tools.mcps.loads_mcp_server import LoadSetMCPProvider


@dataclass
class AgentCalledTool(Evaluator):
    """Evaluator to check if a specific tool was called by the agent."""
    agent_name: str
    tool_name: str

    def evaluate(self, ctx: EvaluatorContext) -> bool:
        import logfire
        
        with logfire.span(f"evaluate_agent_called_tool_{self.tool_name}"):
            result = ctx.span_tree.any(
                SpanQuery(
                    name_equals='agent run',
                    has_attributes={'agent_name': self.agent_name},
                    stop_recursing_when=SpanQuery(name_equals='agent run'),
                    some_descendant_has=SpanQuery(
                        name_equals='running tool',
                        has_attributes={'gen_ai.tool.name': self.tool_name},
                    ),
                )
            )
            
            logfire.info(
                f"AgentCalledTool evaluation for '{self.tool_name}'",
                agent_name=self.agent_name,
                tool_name=self.tool_name,
                result=result
            )
            
            return result


@dataclass
class AgentCalledToolSimple(Evaluator):
    """Simplified evaluator to check if a specific tool was called (without agent name)."""
    tool_name: str

    def evaluate(self, ctx: EvaluatorContext) -> bool:
        import logfire
        
        with logfire.span(f"evaluate_tool_called_{self.tool_name}"):
            result = ctx.span_tree.any(
                SpanQuery(
                    name_equals='agent run',
                    stop_recursing_when=SpanQuery(name_equals='agent run'),
                    some_descendant_has=SpanQuery(
                        name_equals='running tool',
                        has_attributes={'gen_ai.tool.name': self.tool_name},
                    ),
                )
            )
            
            logfire.info(
                f"AgentCalledToolSimple evaluation for '{self.tool_name}'",
                tool_name=self.tool_name,
                result=result
            )
            
            return result


@dataclass
class AgentDidNotCallTool(Evaluator):
    """Evaluator to check that a specific tool was NOT called by the agent."""
    tool_name: str

    def evaluate(self, ctx: EvaluatorContext) -> bool:
        import logfire
        
        with logfire.span(f"evaluate_tool_NOT_called_{self.tool_name}"):
            # Check if the tool was called (opposite of what we want)
            tool_was_called = ctx.span_tree.any(
                SpanQuery(
                    name_equals='agent run',
                    stop_recursing_when=SpanQuery(name_equals='agent run'),
                    some_descendant_has=SpanQuery(
                        name_equals='running tool',
                        has_attributes={'gen_ai.tool.name': self.tool_name},
                    ),
                )
            )
            
            # Return the opposite - True if tool was NOT called
            result = not tool_was_called
            
            logfire.info(
                f"AgentDidNotCallTool evaluation for '{self.tool_name}'",
                tool_name=self.tool_name,
                tool_was_called=tool_was_called,
                result=result,
                expectation="Tool should NOT be called"
            )
            
            return result


@dataclass
class PointExtremesEvaluator(Evaluator):
    """Evaluator to validate specific point extreme values by reading actual ANSYS files."""
    point_name: str
    component: str  # fx, fy, fz, mx, my, mz
    extreme_type: str  # max or min
    expected_value: float
    expected_loadcase: str
    tolerance: float = 0.0001

    def evaluate(self, ctx: EvaluatorContext) -> bool:
        import logfire
        from pathlib import Path
        from tools.loads import LoadSet, Units
        
        with logfire.span(f"evaluate_point_extremes_{self.point_name}_{self.component}_{self.extreme_type}"):
            try:
                # First check if export_to_ansys tool was called
                export_tool_called = ctx.span_tree.any(
                    SpanQuery(
                        name_equals='running tool',
                        has_attributes={'gen_ai.tool.name': 'export_to_ansys'}
                    )
                )
                
                if not export_tool_called:
                    logfire.warning("export_to_ansys tool was not called")
                    return False
                
                # Define output directory constant
                output_dir = Path("/Users/alex/repos/trs-use-case/output")
                
                if not output_dir.exists():
                    logfire.error(f"Output directory does not exist: {output_dir}")
                    return False
                
                # Read all ANSYS files in the output directory
                ansys_files = list(output_dir.glob("*.inp"))
                
                if not ansys_files:
                    logfire.error(f"No ANSYS files found in {output_dir}")
                    return False
                
                logfire.info(f"Found {len(ansys_files)} ANSYS files: {[f.name for f in ansys_files]}")
                
                # Create a consolidated LoadSet by reading all ANSYS files
                all_load_cases = []
                units = Units(forces="N", moments="Nm")  # Default units
                
                for ansys_file in ansys_files:
                    try:
                        # Read each ANSYS file as a separate LoadSet
                        temp_loadset = LoadSet.read_ansys(ansys_file, units)
                        # Add the load case to our consolidated list
                        all_load_cases.extend(temp_loadset.load_cases)
                        
                        logfire.info(f"Successfully read {ansys_file.name} with {len(temp_loadset.load_cases)} load cases")
                        
                    except Exception as e:
                        logfire.error(f"Error reading ANSYS file {ansys_file}: {e}")
                        continue
                
                if not all_load_cases:
                    logfire.error("No load cases could be read from ANSYS files")
                    return False
                
                # Create consolidated LoadSet
                consolidated_loadset = LoadSet(
                    name="Consolidated from ANSYS files",
                    description="LoadSet created from all ANSYS files for evaluation",
                    version=1,
                    units=units,
                    load_cases=all_load_cases
                )
                
                # Get point extremes from the consolidated LoadSet
                extremes = consolidated_loadset.get_point_extremes()
                
                logfire.info(f"Point extremes calculated for {len(extremes)} points")
                
                # Check if the expected point exists
                if self.point_name not in extremes:
                    logfire.error(f"Point '{self.point_name}' not found in extremes")
                    return False
                
                point_data = extremes[self.point_name]
                
                # Check if the expected component exists
                if self.component not in point_data:
                    logfire.error(f"Component '{self.component}' not found for point '{self.point_name}'")
                    return False
                
                component_data = point_data[self.component]
                
                # Check if the expected extreme type exists
                if self.extreme_type not in component_data:
                    logfire.error(f"Extreme type '{self.extreme_type}' not found for component '{self.component}'")
                    return False
                
                extreme_data = component_data[self.extreme_type]
                actual_value = extreme_data["value"]
                actual_loadcase = extreme_data["loadcase"]
                
                # Validate the value within tolerance
                value_diff = abs(actual_value - self.expected_value)
                value_match = value_diff <= self.tolerance
                
                # Validate the load case
                loadcase_match = actual_loadcase == self.expected_loadcase
                
                result = value_match and loadcase_match
                
                logfire.info(
                    f"PointExtremesEvaluator for {self.point_name}.{self.component}.{self.extreme_type}",
                    point_name=self.point_name,
                    component=self.component,
                    extreme_type=self.extreme_type,
                    expected_value=self.expected_value,
                    actual_value=actual_value,
                    value_diff=value_diff,
                    tolerance=self.tolerance,
                    value_match=value_match,
                    expected_loadcase=self.expected_loadcase,
                    actual_loadcase=actual_loadcase,
                    loadcase_match=loadcase_match,
                    result=result,
                    total_ansys_files=len(ansys_files),
                    total_load_cases=len(all_load_cases)
                )
                
                return result
                
            except Exception as e:
                logfire.error(f"Error in PointExtremesEvaluator: {e}", exc_info=True)
                return False



# Define shared case variables
SCENARIO_1_INPUTS = """\
I need to process some loads for ANSYS analysis.
the files are here: /Users/alex/repos/trs-use-case/solution/loads/03_01_new_loads.json
output directory for ansys files: /Users/alex/repos/trs-use-case/output
I do not have any previous loads to compare against.
"""

SCENARIO_1_EVALUATORS = (
    # Tool call validations
    AgentCalledToolSimple(tool_name="scale_loads"),  # Check factor(1.5) operation
    AgentCalledToolSimple(tool_name="export_to_ansys"),  # Check ANSYS export
    AgentCalledToolSimple(tool_name="load_from_json"),  # Check load operation
    AgentDidNotCallTool(tool_name="convert_units"),  # Check units not converted
    
    # Numerical validation of point extremes (based on actual ANSYS file values)
    PointExtremesEvaluator(
        point_name="Point A",
        component="fx",
        extreme_type="max",
        expected_value=1.496,
        expected_loadcase="landing_011"
    ),
    PointExtremesEvaluator(
        point_name="Point A", 
        component="my",
        extreme_type="min",
        expected_value=0.2132,
        expected_loadcase="cruise2_098"
    ),
    PointExtremesEvaluator(
        point_name="Point B",
        component="fy", 
        extreme_type="max",
        expected_value=1.463,
        expected_loadcase="landing_012"
    ),
)

# Create test cases using list comprehension
cases = [
    Case(
        name=f"Scenario 1- iteration {i}",
        inputs=SCENARIO_1_INPUTS,
        evaluators=SCENARIO_1_EVALUATORS
    )
    for i in range(1, 6)
]

# Create dataset
dataset = Dataset(
    cases=list(cases),
    evaluators=[]
)


def load_system_prompt() -> str:
    """Load system prompt by reading the use case definition files."""
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

        

        
        # Evaluate the dataset against the agent task
        report = await dataset.evaluate(agent_task)

        
        
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