# Pydantic AI Evaluation Framework

This directory contains a proof-of-concept evaluation framework for testing Pydantic AI agent behavior, specifically designed to verify that agents call the correct tools with expected parameters.

## Overview

The evaluation framework provides:

- **Tool Call Verification**: Test that agents call specific tools with expected parameters
- **Behavioral Testing**: Verify agent follows system prompt guidance
- **Sequence Validation**: Ensure tools are called in the correct order
- **Comprehensive Reporting**: Detailed evaluation reports with scores and metrics

## Quick Start

### Run the Demo

```bash
uv run python tests/evals/demo_eval_usage.py
```

This demo shows how to evaluate that your `process_loads.py` agent correctly calls `scale_loads` with `factor=1.5`.

### Run the Full Test Suite

```bash
uv run python -m pytest tests/evals/ -v -m eval
```

## Core Components

### 1. Evaluation Framework (`eval_framework.py`)

- `BaseEvaluator`: Abstract base class for all evaluators
- `EvalCase`: Defines individual test cases with prompts and expectations
- `AgentEvaluationSuite`: Runs multiple evaluations and generates reports
- `MockableAgentRunner`: Captures tool calls during agent execution

### 2. Tool Call Evaluators (`tool_call_eval.py`)

- `ToolCallEvaluator`: General-purpose tool call verification
- `ScaleLoadsEvaluator`: Specialized for testing `scale_loads` with specific factors
- `SpecificToolEvaluator`: Tests individual tool calls
- `ToolSequenceEvaluator`: Validates tool call sequences

### 3. Test Fixtures (`conftest.py`)

Provides pytest fixtures for:
- Agent creation with custom system prompts
- MCP server dependencies
- Temporary directories for outputs
- Sample evaluation cases

## Example Usage

### Basic Tool Call Evaluation

```python
from tests.evals.tool_call_eval import ScaleLoadsEvaluator
from tests.evals.eval_framework import EvalCase

# Create evaluator
evaluator = ScaleLoadsEvaluator(expected_factor=1.5)

# Define test case
eval_case = EvalCase(
    name="ultimate_load_test",
    prompt="Process loads for ultimate analysis with safety factor",
    expected_tool_calls=[
        {"name": "scale_loads", "args": {"factor": 1.5}}
    ]
)

# Run evaluation
result = await evaluator.evaluate(agent, eval_case, deps)

# Check results
assert result.passed
assert result.score >= 0.8
```

### Comprehensive Evaluation Suite

```python
from tests.evals.eval_framework import AgentEvaluationSuite

# Create suite
suite = AgentEvaluationSuite("MyEvaluationSuite")
suite.add_evaluator(ScaleLoadsEvaluator(1.5))
suite.add_eval_case(eval_case)

# Run all evaluations
results = await suite.run_evaluations(agent, deps)

# Generate report
report = suite.generate_report(results)
suite.save_report(results, "evaluation_report.json")
```

## Test Cases Included

### 1. Scale Loads Factor Evaluation
- **Purpose**: Verify agent calls `scale_loads` with `factor=1.5`
- **Test**: `test_scale_loads_factor_1_5_evaluation`
- **Expected**: Agent applies safety factor for ultimate loads

### 2. Comprehensive Tool Call Evaluation
- **Purpose**: Validate all expected tool calls are made
- **Test**: `test_comprehensive_tool_call_evaluation`
- **Expected**: Multiple tool calls with correct parameters

### 3. Original Prompt Evaluation
- **Purpose**: Test with the exact prompt from `process_loads.py`
- **Test**: `test_original_prompt_evaluation`
- **Expected**: Agent infers need for safety factor from system prompt

### 4. Tool Sequence Evaluation
- **Purpose**: Verify tools are called in correct order
- **Test**: `test_tool_sequence_evaluation`
- **Expected**: `load_from_json` → `scale_loads` sequence

### 5. Evaluation Suite Test
- **Purpose**: Demonstrate comprehensive testing capabilities
- **Test**: `test_evaluation_suite_run`
- **Expected**: Multiple evaluations with detailed reporting

## Key Features

### 🎯 Tool Call Capture
The framework uses dependency injection wrapping to capture tool calls without modifying agent code:

```python
# Captured tool calls include:
ToolCall(
    name="scale_loads",
    args={"factor": 1.5},
    timestamp=1234567890.0,
    result={"success": True, "message": "Loads scaled by factor 1.5"}
)
```

### 📊 Flexible Scoring
- **Strict Mode**: Exact parameter matching
- **Flexible Mode**: Allows small numerical differences and case variations
- **Partial Credit**: Scores based on how well calls match expectations

### 🔍 Detailed Reporting
Evaluation results include:
- Pass/fail status and numerical scores
- Detailed tool call information
- Execution timing
- Comprehensive error reporting

### ⚙️ Extensible Design
Easy to create custom evaluators:

```python
class MyCustomEvaluator(BaseEvaluator):
    async def evaluate(self, agent, eval_case, deps):
        # Custom evaluation logic
        return EvalResult(passed=True, score=1.0, message="Custom test passed")
```

## Integration with Process Loads

The evaluation framework specifically tests the agent from `solution/03_loads_processing/process_loads.py`:

1. **System Prompt Integration**: Uses the same `load_system_prompt()` function
2. **Real Tool Testing**: Tests actual MCP server tool calls
3. **Behavioral Validation**: Verifies agent follows EP Static Analysis procedures
4. **Safety Factor Verification**: Confirms 1.5 factor application for ultimate loads

## Running Evaluations

### Individual Tests
```bash
# Run specific evaluation
uv run python -m pytest tests/evals/test_process_loads_eval.py::TestProcessLoadsEvaluation::test_scale_loads_factor_1_5_evaluation -v -s -m eval

# Run behavioral tests
uv run python -m pytest tests/evals/test_process_loads_eval.py::TestProcessLoadsAgentBehavior -v -m eval
```

### All Evaluations
```bash
# Run all evaluation tests
uv run python -m pytest tests/evals/ -v -m eval

# Run with detailed output
uv run python -m pytest tests/evals/ -v -s -m eval
```

## Results Interpretation

### Successful Evaluation Output
```
=== Evaluation Result ===
Passed: True
Score: 1.0
Message: ✅ scale_loads called with factor 1.5 as expected
Tool calls made: 3
  1. load_from_json({'file_path': 'solution/loads/new_loads.json'}) -> success
  2. scale_loads({'factor': 1.5}) -> success  
  3. export_to_ansys(...) -> success
```

### Evaluation Report
```json
{
  "suite_name": "ProcessLoadsEvaluationSuite",
  "total_cases": 4,
  "passed_cases": 2,
  "pass_rate": 0.5,
  "average_score": 0.75,
  "results": [...]
}
```

## Future Enhancements

Potential extensions to the framework:

1. **Output Content Evaluation**: Verify agent response content quality
2. **Performance Metrics**: Track execution time and efficiency
3. **Regression Testing**: Compare against baseline performance
4. **Multi-Agent Evaluation**: Test agent interactions
5. **Continuous Integration**: Automated evaluation in CI/CD pipelines

## Contributing

To add new evaluators:

1. Extend `BaseEvaluator` class
2. Implement the `evaluate` method
3. Add test cases to the test suite
4. Update documentation

This evaluation framework provides a robust foundation for testing AI agent behavior and ensuring consistent, reliable performance in production environments.