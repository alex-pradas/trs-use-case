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

# Test case using the same input as USER_PROMPT_1 from process_loads.py
case1 = Case(
    name="Scenario 1: Process loads without previous loads",
    inputs="""\
I need to process some loads for ANSYS analysis.
the files are here: /Users/alex/repos/trs-use-case/solution/loads/03_01_new_loads.json
I do not have any previous loads to compare against.
""",
    evaluators=(
        # Check that the agent called the scale_loads tool (equivalent to factor(1.5))
        AgentCalledToolSimple(tool_name="scale_loads"),
        # Check that the agent called the export_to_ansys tool
        AgentCalledToolSimple(tool_name="export_to_ansys"),
        # Also check for load_from_json to ensure basic functionality
        AgentCalledToolSimple(tool_name="load_from_json"),
        # Check that convert_to was NOT called (loads should already be in Newtons)
        AgentDidNotCallTool(tool_name="convert_units"),
    )
)


# Create dataset
dataset = Dataset(
    cases=[case1],
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
    system_prompt = load_system_prompt()
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
            dataset_cases=len(dataset.cases),
            evaluators=[type(e).__name__ for e in case1.evaluators]
        )
        
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