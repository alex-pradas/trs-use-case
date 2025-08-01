from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

from pyparsing import with_attribute

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
    """Simplified evaluator to check if a specific tool was called (without agent name)."""
    tool_name: str
    tool_arguments: dict[str, Any] | None = None

    def _extract_tool_arguments(self, span) -> dict[str, Any] | None:
        """Extract and parse tool_arguments from span attributes."""
        if not (hasattr(span, 'attributes') and 'tool_arguments' in span.attributes):
            return None
            
        tool_arguments_attr = span.attributes['tool_arguments']
        
        # Handle different attribute value types
        if isinstance(tool_arguments_attr, dict):
            return tool_arguments_attr
        elif isinstance(tool_arguments_attr, str):
            try:
                import json
                return json.loads(tool_arguments_attr)
            except json.JSONDecodeError:
                return None
        
        return None

    def evaluate(self, ctx: EvaluatorContext) -> bool:
        import logfire
        
        with logfire.span(f"evaluate_tool_called_{self.tool_name}"):
            # If no tool_arguments specified, use the original simple logic
            if self.tool_arguments is None:
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
                    f"AgentCalledTool evaluation for '{self.tool_name}' (no argument checking)",
                    tool_name=self.tool_name,
                    result=result
                )
                
                return result
            
            # If tool_arguments are specified, we need to find spans and check arguments manually
            tool_spans = ctx.span_tree.find(
                SpanQuery(
                    name_equals='running tool',
                    has_attributes={'gen_ai.tool.name': self.tool_name},
                )
            )
            
            if not tool_spans:
                logfire.info(
                    f"AgentCalledTool evaluation for '{self.tool_name}' - no tool spans found",
                    tool_name=self.tool_name,
                    expected_arguments=self.tool_arguments,
                    result=False
                )
                return False
            
            # Check if any of the tool calls have the expected arguments
            for span in tool_spans:
                actual_arguments = self._extract_tool_arguments(span)
                
                if actual_arguments:
                    # Check if all expected arguments match
                    arguments_match = all(
                        actual_arguments.get(key) == expected_value
                        for key, expected_value in self.tool_arguments.items()
                    )
                    
                    if arguments_match:
                        logfire.info(
                            f"AgentCalledTool evaluation for '{self.tool_name}' - arguments match found",
                            tool_name=self.tool_name,
                            expected_arguments=self.tool_arguments,
                            actual_arguments=actual_arguments,
                            result=True
                        )
                        return True
            
            # No matching tool call with correct arguments found
            logfire.info(
                f"AgentCalledTool evaluation for '{self.tool_name}' - tool was called but no matching arguments found",
                tool_name=self.tool_name,
                expected_arguments=self.tool_arguments,
                result=False
            )
            
            return False


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
class LoadSetExtremesEvaluator(Evaluator):
    """Evaluator to validate specific point extreme values from LoadSet data in tool call response."""
    point_name: str
    component: str  # fx, fy, fz, mx, my, mz
    extreme_type: str  # max or min
    expected_value: float
    expected_loadcase: str
    tolerance: float = 0.0001

    def evaluate(self, ctx: EvaluatorContext) -> bool:
        import logfire
        
        with logfire.span(f"evaluate_loadset_extremes_{self.point_name}_{self.component}_{self.extreme_type}"):
            try:
                # First verify that export_to_ansys was called
                export_tool_called = ctx.span_tree.any(
                    SpanQuery(
                        name_equals='running tool',
                        has_attributes={'gen_ai.tool.name': 'export_to_ansys'}
                    )
                )
                
                if not export_tool_called:
                    logfire.warning("export_to_ansys tool was not called")
                    return False
                
                # Find the export_to_ansys tool call spans  
                export_spans = ctx.span_tree.find(
                    SpanQuery(
                        name_equals='running tool',
                        has_attributes={'gen_ai.tool.name': 'export_to_ansys'}
                    )
                )
                
                if not export_spans:
                    logfire.error("export_to_ansys tool span not found")
                    return False
                
                export_span = export_spans[0]  # Get the first matching span
                
                # Extract tool_response from span attributes
                tool_response = None
                if hasattr(export_span, 'attributes') and 'tool_response' in export_span.attributes:
                    tool_response_attr = export_span.attributes['tool_response']
                    
                    # Handle different attribute value types
                    if isinstance(tool_response_attr, dict):
                        tool_response = tool_response_attr
                        logfire.info("Successfully extracted tool_response as dict from span")
                    elif isinstance(tool_response_attr, str):
                        try:
                            import json
                            tool_response = json.loads(tool_response_attr)
                            logfire.info("Successfully extracted tool_response as parsed JSON from span")
                        except json.JSONDecodeError as e:
                            logfire.error(f"Failed to parse tool_response JSON: {e}")
                            return False
                    else:
                        logfire.error(f"Unexpected tool_response type: {type(tool_response_attr)}")
                        return False
                else:
                    logfire.error(
                        "tool_response not found in export_to_ansys span attributes",
                        available_attributes=list(export_span.attributes.keys()) if hasattr(export_span, 'attributes') else None
                    )
                    return False
                
                # Validate tool call was successful
                if not tool_response.get('success', False):
                    logfire.error(f"export_to_ansys tool call failed: {tool_response.get('message', 'Unknown error')}")
                    return False
                
                # Extract loadset extremes from the tool response
                loadset_extremes = tool_response.get('loadset_extremes')
                if not loadset_extremes:
                    logfire.error("No loadset_extremes found in export_to_ansys tool response")
                    return False
                
                logfire.info(
                    f"Successfully extracted LoadSet extremes for validation",
                    evaluator_type="LoadSetExtremesEvaluator",
                    point_name=self.point_name,
                    component=self.component,
                    extreme_type=self.extreme_type,
                    num_points=len(loadset_extremes)
                )
                
                # Validate the expected point exists
                if self.point_name not in loadset_extremes:
                    logfire.error(
                        f"Point '{self.point_name}' not found in loadset extremes",
                        available_points=list(loadset_extremes.keys())
                    )
                    return False
                
                point_data = loadset_extremes[self.point_name]
                
                # Validate the expected component exists
                if self.component not in point_data:
                    logfire.error(
                        f"Component '{self.component}' not found for point '{self.point_name}'",
                        available_components=list(point_data.keys())
                    )
                    return False
                
                component_data = point_data[self.component]
                
                # Validate the expected extreme type exists
                if self.extreme_type not in component_data:
                    logfire.error(
                        f"Extreme type '{self.extreme_type}' not found for component '{self.component}'",
                        available_extreme_types=list(component_data.keys())
                    )
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
                    f"LoadSetExtremesEvaluator for {self.point_name}.{self.component}.{self.extreme_type}",
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
                )
                
                return result
                
            except Exception as e:
                logfire.error(f"Error in LoadSetExtremesEvaluator: {e}", exc_info=True)
                return False



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
    AgentCalledTool(tool_name="scale_loads", tool_arguments={"factor": 1.5}),  # Check factor(1.5) operation
    AgentCalledTool(tool_name="export_to_ansys"),  # Check ANSYS export
    AgentCalledTool(tool_name="load_from_json"),  # Check load operation
    AgentDidNotCallTool(tool_name="convert_units"),  # Check units not converted
    AgentCalledTool(tool_name="envelope_loadset"),  # Check envelope operation
   
    # Numerical validation of point extremes (using LoadSet data from tool call response)
    LoadSetExtremesEvaluator(
        point_name="Point A",
        component="fx",
        extreme_type="max",
        expected_value=1.4958699,
        expected_loadcase="landing_011"
    ),
    LoadSetExtremesEvaluator(
        point_name="Point A", 
        component="my",
        extreme_type="min",
        expected_value=0.213177015,
        expected_loadcase="cruise2_098"
    ),
    LoadSetExtremesEvaluator(
        point_name="Point B",
        component="fy", 
        extreme_type="max",
        expected_value=1.462682895,
        expected_loadcase="landing_012"
    ),
)

ACTIVITY_03B_EVALUATORS = (
    # Tool call validations
    AgentCalledTool(tool_name="load_from_json"),  # Check load operation
    AgentDidNotCallTool(tool_name="scale_loads"),  # Check factor(1.5) operation
    AgentDidNotCallTool(tool_name="convert_units"),  # Check units not converted
    AgentCalledTool(tool_name="envelope_loadset"),  # Check envelope operation
    AgentCalledTool(tool_name="export_to_ansys"),  # Check ANSYS export
   
    # Numerical validation of point extremes (using LoadSet data from tool call response)
    LoadSetExtremesEvaluator(
        point_name="Point A",
        component="fx",
        extreme_type="max",
        expected_value=1.4958699,
        expected_loadcase="landing_011"
    ),
    LoadSetExtremesEvaluator(
        point_name="Point A", 
        component="my",
        extreme_type="min",
        expected_value=0.213177015,
        expected_loadcase="cruise2_098"
    ),
    LoadSetExtremesEvaluator(
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