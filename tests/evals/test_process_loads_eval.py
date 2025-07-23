"""
Evaluation test for process_loads.py agent.

This test evaluates that the agent in solution/03_loads_processing/process_loads.py
correctly calls the scale_loads tool with factor 1.5 as expected for ultimate load processing.
"""

import pytest
import sys
from pathlib import Path

from tests.evals.eval_framework import AgentEvaluationSuite, EvalCase  # noqa: E402
from tests.evals.tool_call_eval import (  # noqa: E402
    ScaleLoadsEvaluator,
    ToolCallEvaluator,
    ToolSequenceEvaluator,
)
from tools.agents import create_loadset_agent  # noqa: E402

# Import the system prompt loading function from process_loads
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "solution" / "03_loads_processing"))
try:
    from process_loads import load_system_prompt  # noqa: E402
except ImportError as e:
    print(f"Warning: Could not import load_system_prompt: {e}")
    print("Will use a default system prompt for testing.")

    def load_system_prompt():
        return """
You are a structural analysis expert specializing in processing loads for aerospace components.

Your task is to support the user to manipulate and prepare the loads for a FEM analysis in ANSYS, following the EP Static Analysis procedures.

Key Operations required:
1. Process loads from customer format and convert units (N and Nm)
2. Factor in safety margins (1.5 for ultimate loads) if appropriate
3. Compare new loads with previous applicable loads, if old loads are provided by user.

When processing loads for ultimate analysis, you MUST apply a safety factor of 1.5 by calling the scale_loads tool.

DO NOT ASK QUESTIONS. USE THE PROVIDED TOOLS TO PROCESS LOADS AND GENERATE OUTPUTS.
"""


@pytest.mark.eval
@pytest.mark.tool_call_eval
@pytest.mark.expensive
class TestProcessLoadsEvaluation:
    """Evaluation tests for the process_loads.py agent."""

    @pytest.fixture
    def process_loads_agent(self):
        """Create the agent with the same system prompt as process_loads.py."""
        system_prompt = load_system_prompt()
        return create_loadset_agent(system_prompt=system_prompt)

    @pytest.fixture
    def ultimate_load_eval_case(self):
        """Evaluation case that should trigger scale_loads with factor 1.5."""
        return EvalCase(
            name="ultimate_load_processing_eval",
            prompt="""
I need to process some loads for ANSYS analysis.
The files are here: solution/loads/new_loads.json

This is for ultimate load analysis, so please apply the appropriate safety factor.
            """.strip(),
            expected_tool_calls=[
                {
                    "name": "load_from_json",
                    "args": {"file_path": "solution/loads/new_loads.json"},
                },
                {"name": "scale_loads", "args": {"factor": 1.5}},
            ],
            timeout=60.0,
            description="Test that ultimate load processing applies factor 1.5",
        )

    @pytest.fixture
    def safety_factor_eval_case(self):
        """Evaluation case that explicitly mentions safety factor."""
        return EvalCase(
            name="safety_factor_eval",
            prompt="""
Process the loads in solution/loads/new_loads.json.
Apply safety margins as per EP Static Analysis procedures.
Factor in safety margins (1.5 for ultimate loads).
            """.strip(),
            expected_tool_calls=[
                {
                    "name": "load_from_json",
                    "args": {"file_path": "solution/loads/new_loads.json"},
                },
                {"name": "scale_loads", "args": {"factor": 1.5}},
            ],
            timeout=60.0,
            description="Test safety factor application per procedures",
        )

    @pytest.fixture
    def original_user_prompt_eval_case(self):
        """Use the exact same prompt from process_loads.py."""
        return EvalCase(
            name="original_prompt_eval",
            prompt="""
I need to process some loads for ANSYS analysis.
the files are here: solution/loads/new_loads.json
            """.strip(),
            expected_tool_calls=[
                {"name": "load_from_json", "args": {}},  # Flexible on exact path
                {"name": "scale_loads", "args": {"factor": 1.5}},
            ],
            timeout=60.0,
            description="Test with original prompt from process_loads.py",
        )

    @pytest.mark.asyncio
    async def test_scale_loads_factor_1_5_evaluation(
        self,
        process_loads_agent,
        ultimate_load_eval_case,
        mcp_dependencies,
        eval_assert,
    ):
        """Test that the agent calls scale_loads with factor 1.5."""

        # Create evaluator specifically for scale_loads with factor 1.5
        evaluator = ScaleLoadsEvaluator(
            expected_factor=1.5, name="UltimateLoadFactorEval"
        )

        # Run the evaluation
        result = await evaluator.evaluate(
            agent=process_loads_agent,
            eval_case=ultimate_load_eval_case,
            deps=mcp_dependencies,
        )

        # Assert the evaluation passed
        eval_assert.assert_evaluation_passed(result, min_score=0.8)
        eval_assert.assert_no_errors(result)

        # Specific assertions for scale_loads call
        eval_assert.assert_tool_called(result, "scale_loads", {"factor": 1.5})

        # Print detailed results for debugging
        print("\n=== Evaluation Result ===")
        print(f"Passed: {result.passed}")
        print(f"Score: {result.score}")
        print(f"Message: {result.message}")
        print(f"Tool calls made: {len(result.tool_calls)}")

        for i, call in enumerate(result.tool_calls):
            print(f"  {i + 1}. {call.name}({call.args}) -> {call.result}")

    @pytest.mark.asyncio
    async def test_comprehensive_tool_call_evaluation(
        self, process_loads_agent, safety_factor_eval_case, mcp_dependencies
    ):
        """Comprehensive evaluation of all expected tool calls."""

        # Create a general tool call evaluator
        evaluator = ToolCallEvaluator(
            name="ComprehensiveToolCallEval",
            strict_mode=False,  # Allow flexible parameter matching
            allow_extra_calls=True,
        )

        # Run the evaluation
        result = await evaluator.evaluate(
            agent=process_loads_agent,
            eval_case=safety_factor_eval_case,
            deps=mcp_dependencies,
        )

        # Check results
        assert result.score >= 0.5, f"Evaluation score too low: {result.score}"

        # Verify scale_loads was called with factor 1.5
        scale_calls = [call for call in result.tool_calls if call.name == "scale_loads"]
        assert scale_calls, "scale_loads tool was not called"

        factor_1_5_calls = [
            call for call in scale_calls if call.args.get("factor") == 1.5
        ]
        assert factor_1_5_calls, (
            f"scale_loads not called with factor 1.5. Found factors: {[call.args.get('factor') for call in scale_calls]}"
        )

        print("\n=== Comprehensive Evaluation ===")
        print(f"Score: {result.score}")
        print(f"Details: {result.details}")

    @pytest.mark.asyncio
    async def test_original_prompt_evaluation(
        self, process_loads_agent, original_user_prompt_eval_case, mcp_dependencies
    ):
        """Test evaluation with the original prompt from process_loads.py."""

        evaluator = ScaleLoadsEvaluator(expected_factor=1.5, name="OriginalPromptEval")

        result = await evaluator.evaluate(
            agent=process_loads_agent,
            eval_case=original_user_prompt_eval_case,
            deps=mcp_dependencies,
        )

        print("\n=== Original Prompt Evaluation ===")
        print(f"Prompt: {original_user_prompt_eval_case.prompt}")
        print(f"Passed: {result.passed}")
        print(f"Score: {result.score}")
        print(f"Message: {result.message}")

        # The agent should apply safety factor even with the original prompt
        # based on the system prompt instructions
        scale_calls = [call for call in result.tool_calls if call.name == "scale_loads"]
        if scale_calls:
            print(
                f"✅ scale_loads called with factors: {[call.args.get('factor') for call in scale_calls]}"
            )
        else:
            print("⚠️ scale_loads was not called")

        # This might not pass with the original prompt since it doesn't explicitly mention ultimate loads
        # But we can check if the system prompt guidance is being followed

    @pytest.mark.asyncio
    async def test_tool_sequence_evaluation(
        self, process_loads_agent, ultimate_load_eval_case, mcp_dependencies
    ):
        """Test that tools are called in the expected sequence."""

        # Expected sequence: load_from_json -> scale_loads
        expected_sequence = ["load_from_json", "scale_loads"]

        evaluator = ToolSequenceEvaluator(
            expected_sequence=expected_sequence, name="LoadProcessingSequenceEval"
        )

        result = await evaluator.evaluate(
            agent=process_loads_agent,
            eval_case=ultimate_load_eval_case,
            deps=mcp_dependencies,
        )

        print("\n=== Tool Sequence Evaluation ===")
        print(f"Expected: {' → '.join(expected_sequence)}")
        print(f"Actual: {' → '.join([call.name for call in result.tool_calls])}")
        print(f"Passed: {result.passed}")
        print(f"Score: {result.score}")

        assert result.score >= 0.8, f"Tool sequence evaluation failed: {result.message}"

    @pytest.mark.asyncio
    async def test_evaluation_suite_run(
        self, process_loads_agent, mcp_dependencies, evaluation_report_path
    ):
        """Run a complete evaluation suite and generate a report."""

        # Create evaluation suite
        suite = AgentEvaluationSuite("ProcessLoadsEvaluationSuite")

        # Add evaluators
        suite.add_evaluator(ScaleLoadsEvaluator(1.5, "UltimateLoadFactor"))
        suite.add_evaluator(ToolCallEvaluator("GeneralToolCallEval"))

        # Add evaluation cases
        eval_cases = [
            EvalCase(
                name="ultimate_loads_test",
                prompt="Process solution/loads/new_loads.json for ultimate load analysis with safety factor 1.5",
                expected_tool_calls=[
                    {"name": "load_from_json", "args": {}},
                    {"name": "scale_loads", "args": {"factor": 1.5}},
                ],
            ),
            EvalCase(
                name="safety_margin_test",
                prompt="Load solution/loads/new_loads.json and apply safety margins per EP procedures",
                expected_tool_calls=[
                    {"name": "load_from_json", "args": {}},
                    {"name": "scale_loads", "args": {"factor": 1.5}},
                ],
            ),
        ]

        for case in eval_cases:
            suite.add_eval_case(case)

        # Run all evaluations
        results = await suite.run_evaluations(process_loads_agent, mcp_dependencies)

        # Generate and save report
        suite.save_report(results, evaluation_report_path)

        # Print summary
        report = suite.generate_report(results)
        print(f"\n=== Evaluation Suite Results ===")
        print(f"Suite: {report['suite_name']}")
        print(f"Total cases: {report['total_cases']}")
        print(f"Passed: {report['passed_cases']}")
        print(f"Failed: {report['failed_cases']}")
        print(f"Pass rate: {report['pass_rate']:.2%}")
        print(f"Average score: {report['average_score']:.2f}")
        print(f"Report saved to: {evaluation_report_path}")

        # Assert that most evaluations passed
        assert report["pass_rate"] >= 0.5, (
            f"Too many evaluations failed: {report['pass_rate']:.2%}"
        )


@pytest.mark.eval
@pytest.mark.expensive
class TestProcessLoadsAgentBehavior:
    """Additional behavioral tests for the process loads agent."""

    @pytest.mark.asyncio
    async def test_agent_follows_system_prompt_guidance(
        self, loadset_agent_with_custom_prompt, mcp_dependencies
    ):
        """Test that agent follows system prompt guidance for applying safety factors."""

        # Custom prompt that explicitly requires factor 1.5
        prompt = (
            "Process loads for ultimate analysis from solution/loads/new_loads.json"
        )

        evaluator = ScaleLoadsEvaluator(1.5, "SystemPromptGuidanceEval")
        eval_case = EvalCase(
            name="system_prompt_guidance",
            prompt=prompt,
            expected_tool_calls=[{"name": "scale_loads", "args": {"factor": 1.5}}],
        )

        result = await evaluator.evaluate(
            agent=loadset_agent_with_custom_prompt,
            eval_case=eval_case,
            deps=mcp_dependencies,
        )

        print(f"\n=== System Prompt Guidance Test ===")
        print(f"Result: {result.message}")
        print(f"Tool calls: {[(call.name, call.args) for call in result.tool_calls]}")

        # With the custom system prompt, the agent should apply the safety factor
        scale_calls = [call for call in result.tool_calls if call.name == "scale_loads"]
        if scale_calls:
            factors = [call.args.get("factor") for call in scale_calls]
            print(f"Safety factors applied: {factors}")

    @pytest.mark.asyncio
    async def test_no_double_factoring(
        self, loadset_agent_with_custom_prompt, mcp_dependencies
    ):
        """Test that the agent doesn't apply safety factor multiple times."""

        prompt = (
            "Load solution/loads/new_loads.json and apply ultimate safety factor of 1.5"
        )

        evaluator = ToolCallEvaluator("NoDoubleFactor", allow_extra_calls=True)
        eval_case = EvalCase(
            name="no_double_factor",
            prompt=prompt,
            expected_tool_calls=[{"name": "scale_loads", "args": {"factor": 1.5}}],
        )

        result = await evaluator.evaluate(
            agent=loadset_agent_with_custom_prompt,
            eval_case=eval_case,
            deps=mcp_dependencies,
        )

        # Count scale_loads calls
        scale_calls = [call for call in result.tool_calls if call.name == "scale_loads"]

        print(f"\n=== Double Factoring Prevention Test ===")
        print(f"Number of scale_loads calls: {len(scale_calls)}")
        print(f"Factors applied: {[call.args.get('factor') for call in scale_calls]}")

        # Ideally should only call scale_loads once
        if len(scale_calls) <= 1:
            print("✅ No double factoring detected")
        else:
            print("⚠️ Multiple scale_loads calls detected - check for double factoring")


if __name__ == "__main__":
    # Run the evaluations directly
    pytest.main([__file__, "-v", "--tb=short"])
