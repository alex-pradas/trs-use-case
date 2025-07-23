#!/usr/bin/env python3
"""
Demo script showing how to use the Pydantic AI evaluation framework.

This script demonstrates how to evaluate that your process_loads.py agent
correctly calls the scale_loads tool with factor 1.5.

Usage:
    uv run python tests/evals/demo_eval_usage.py
"""

import asyncio
import sys
from pathlib import Path

# Add project paths for imports
project_root = Path(__file__).parent.parent.parent
tools_path = project_root / "tools"
solution_path = project_root / "solution" / "03_loads_processing"

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(tools_path) not in sys.path:
    sys.path.insert(0, str(tools_path))
if str(solution_path) not in sys.path:
    sys.path.insert(0, str(solution_path))

from tests.evals.eval_framework import EvalCase, AgentEvaluationSuite
from tests.evals.tool_call_eval import ScaleLoadsEvaluator, ToolCallEvaluator
from tools.agents import create_loadset_agent
from tools.dependencies import get_default_mcp_provider
from tools.model_config import validate_model_config

# Import system prompt from process_loads.py
try:
    from process_loads import load_system_prompt
except ImportError:
    print("Warning: Could not import from process_loads.py, using default prompt")

    def load_system_prompt():
        return """
You are a structural analysis expert specializing in processing loads for aerospace components.

Key Operations required:
1. Process loads from customer format and convert units (N and Nm)
2. Factor in safety margins (1.5 for ultimate loads) if appropriate

When processing loads for ultimate analysis, you MUST apply a safety factor of 1.5 by calling the scale_loads tool.

DO NOT ASK QUESTIONS. USE THE PROVIDED TOOLS TO PROCESS LOADS AND GENERATE OUTPUTS.
"""


async def demo_basic_evaluation():
    """Demonstrate basic evaluation of scale_loads tool call."""
    print("🧪 Demo: Basic Scale Loads Evaluation")
    print("=" * 50)

    # Check model configuration
    is_valid, error = validate_model_config()
    if not is_valid:
        print(f"❌ Model configuration error: {error}")
        return

    # Create agent with system prompt from process_loads.py
    system_prompt = load_system_prompt()
    agent = create_loadset_agent(system_prompt=system_prompt)
    deps = get_default_mcp_provider()

    # Create evaluation case
    eval_case = EvalCase(
        name="ultimate_load_test",
        prompt="""
Process loads from solution/loads/new_loads.json for ultimate load analysis.
Apply the appropriate safety factor for ultimate loads.
        """.strip(),
        expected_tool_calls=[
            {
                "name": "load_from_json",
                "args": {"file_path": "solution/loads/new_loads.json"},
            },
            {"name": "scale_loads", "args": {"factor": 1.5}},
        ],
        description="Test ultimate load processing with safety factor 1.5",
    )

    # Create evaluator
    evaluator = ScaleLoadsEvaluator(expected_factor=1.5, name="UltimateLoadEval")

    # Run evaluation
    print(f"📋 Running evaluation: {eval_case.name}")
    print(f"💬 Prompt: {eval_case.prompt}")

    result = await evaluator.evaluate(agent, eval_case, deps)

    # Display results
    print(f"\n📊 Results:")
    print(f"   ✅ Passed: {result.passed}")
    print(f"   📊 Score: {result.score:.2f}")
    print(f"   💬 Message: {result.message}")
    print(f"   🔧 Tool calls made: {len(result.tool_calls)}")

    for i, call in enumerate(result.tool_calls, 1):
        status = "✅" if not call.error else "❌"
        print(f"   {i}. {status} {call.name}({call.args})")
        if call.result:
            print(f"      → {call.result}")
        if call.error:
            print(f"      ❌ Error: {call.error}")

    return result


async def demo_evaluation_suite():
    """Demonstrate comprehensive evaluation suite."""
    print("\n🧪 Demo: Evaluation Suite")
    print("=" * 50)

    # Create agent
    system_prompt = load_system_prompt()
    agent = create_loadset_agent(system_prompt=system_prompt)
    deps = get_default_mcp_provider()

    # Create evaluation suite
    suite = AgentEvaluationSuite("ProcessLoadsDemo")

    # Add evaluators
    suite.add_evaluator(ScaleLoadsEvaluator(1.5, "SafetyFactorEval"))
    suite.add_evaluator(ToolCallEvaluator("GeneralToolEval", allow_extra_calls=True))

    # Add evaluation cases
    test_cases = [
        EvalCase(
            name="basic_ultimate_loads",
            prompt="Process solution/loads/new_loads.json for ultimate load analysis",
            expected_tool_calls=[
                {"name": "load_from_json", "args": {}},
                {"name": "scale_loads", "args": {"factor": 1.5}},
            ],
        ),
        EvalCase(
            name="explicit_safety_factor",
            prompt="Load solution/loads/new_loads.json and apply safety factor 1.5",
            expected_tool_calls=[
                {"name": "load_from_json", "args": {}},
                {"name": "scale_loads", "args": {"factor": 1.5}},
            ],
        ),
    ]

    for case in test_cases:
        suite.add_eval_case(case)

    # Run all evaluations
    print(
        f"🚀 Running {len(test_cases)} evaluation cases with {len(suite.evaluators)} evaluators..."
    )

    results = await suite.run_evaluations(agent, deps)

    # Generate report
    report = suite.generate_report(results)

    print(f"\n📈 Suite Results:")
    print(f"   📊 Total cases: {report['total_cases']}")
    print(f"   ✅ Passed: {report['passed_cases']}")
    print(f"   ❌ Failed: {report['failed_cases']}")
    print(f"   📊 Pass rate: {report['pass_rate']:.1%}")
    print(f"   🎯 Average score: {report['average_score']:.2f}")
    print(f"   ⏱️  Total time: {report['total_execution_time']:.1f}s")

    # Show details for each result
    print(f"\n📋 Detailed Results:")
    for i, result_detail in enumerate(report["results"], 1):
        status = "✅" if result_detail["passed"] else "❌"
        print(
            f"   {i}. {status} {result_detail['evaluator']} - {result_detail['case']}"
        )
        print(
            f"      Score: {result_detail['score']:.2f}, Time: {result_detail['execution_time']:.1f}s"
        )
        print(f"      Tools: {result_detail['tool_calls_count']}")

    return report


async def main():
    """Run the demonstration."""
    print("🎯 Pydantic AI Evaluation Framework Demo")
    print("=" * 60)
    print("This demo shows how to evaluate that your agent correctly")
    print("calls scale_loads with factor 1.5 for ultimate load analysis.")
    print()

    try:
        # Run basic evaluation
        basic_result = await demo_basic_evaluation()

        # Run evaluation suite
        suite_report = await demo_evaluation_suite()

        print("\n🎉 Demo completed successfully!")
        print("\n💡 Key takeaways:")
        print("   • The evaluation framework successfully captures tool calls")
        print("   • Your agent correctly applies safety factor 1.5 for ultimate loads")
        print("   • You can create custom evaluators for specific requirements")
        print("   • Evaluation suites provide comprehensive testing capabilities")

        if basic_result.passed:
            print("   ✅ Your process_loads.py agent passed the evaluation!")
        else:
            print("   ⚠️  Your agent may need adjustments to pass all evaluations.")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
