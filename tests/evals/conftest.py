"""
Pytest fixtures for evaluation testing.

This module provides common fixtures and utilities for running
AI agent evaluations.
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Generator, Any
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project paths for imports
project_root = Path(__file__).parent.parent.parent
tools_path = project_root / "tools"
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(tools_path) not in sys.path:
    sys.path.insert(0, str(tools_path))

from tools.agents import create_loadset_agent  # noqa: E402
from tools.mcps.loads_mcp_server import LoadSetMCPProvider  # noqa: E402
from tools.model_config import validate_model_config  # noqa: E402


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_output_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for evaluation outputs."""
    temp_dir = tempfile.mkdtemp(prefix="eval_output_")
    output_path = Path(temp_dir)

    try:
        yield output_path
    finally:
        if output_path.exists():
            shutil.rmtree(output_path)


@pytest.fixture(autouse=True)
def reset_mcp_state():
    """Reset MCP server state before each test - no longer needed in new architecture."""
    # No global state to reset with new architecture
    yield


@pytest.fixture
def loadset_agent():
    """Create a loadset agent for testing."""
    return create_loadset_agent()


@pytest.fixture
def mcp_dependencies():
    """Create LoadSet MCP provider."""
    return LoadSetMCPProvider()


@pytest.fixture
def custom_system_prompt():
    """Provide a custom system prompt for testing specific behaviors."""
    return """
You are a structural analysis expert specializing in processing loads for aerospace components.

Your task is to support the user to manipulate and prepare the loads for a FEM analysis in ANSYS.

Key Operations required:
1. Process loads from customer format and convert units (N and Nm)
2. Factor in safety margins (1.5 for ultimate loads) if appropriate
3. Compare new loads with previous applicable loads, if old loads are provided by user.

When processing loads for ultimate analysis, you MUST apply a safety factor of 1.5 by calling the scale_loads tool.

DO NOT ASK QUESTIONS. USE THE PROVIDED TOOLS TO PROCESS LOADS AND GENERATE OUTPUTS.
"""


@pytest.fixture
def loadset_agent_with_custom_prompt(custom_system_prompt):
    """Create a loadset agent with custom system prompt for specific testing."""
    return create_loadset_agent(system_prompt=custom_system_prompt)


@pytest.fixture
def test_data_paths():
    """Provide paths to test data files."""
    return {
        "new_loads": "solution/loads/new_loads.json",
        "old_loads": "solution/loads/old_loads.json",
        "output_dir": "solution/output/",
    }


@pytest.fixture(scope="session")
def model_config_check():
    """Check if model configuration is valid before running evaluations."""
    is_valid, error = validate_model_config()
    if not is_valid:
        pytest.skip(f"Model configuration error: {error}")
    return True


@pytest.fixture
def evaluation_config():
    """Provide configuration for evaluations."""
    return {
        "timeout": 60.0,
        "max_retries": 2,
        "expected_score_threshold": 0.8,
        "capture_tool_calls": True,
        "save_detailed_logs": True,
    }


@pytest.fixture
def sample_eval_cases():
    """Provide sample evaluation cases for testing."""
    from tests.evals.eval_framework import EvalCase

    return [
        EvalCase(
            name="basic_load_processing",
            prompt="Load the file solution/loads/new_loads.json and process it.",
            expected_tool_calls=[
                {
                    "name": "load_from_json",
                    "args": {"file_path": "solution/loads/new_loads.json"},
                }
            ],
            description="Test basic load file loading",
        ),
        EvalCase(
            name="ultimate_load_processing",
            prompt="Load solution/loads/new_loads.json and apply ultimate load factor of 1.5.",
            expected_tool_calls=[
                {
                    "name": "load_from_json",
                    "args": {"file_path": "solution/loads/new_loads.json"},
                },
                {"name": "scale_loads", "args": {"factor": 1.5}},
            ],
            description="Test ultimate load processing with safety factor",
        ),
        EvalCase(
            name="full_workflow",
            prompt="Process loads from solution/loads/new_loads.json with ultimate factor 1.5, convert to klbf, and export to ANSYS.",
            expected_tool_calls=[
                {
                    "name": "load_from_json",
                    "args": {"file_path": "solution/loads/new_loads.json"},
                },
                {"name": "scale_loads", "args": {"factor": 1.5}},
                {"name": "convert_units", "args": {"target_units": "klbf"}},
                {"name": "export_to_ansys", "args": {}},
            ],
            description="Test complete load processing workflow",
        ),
    ]


@pytest.fixture
def evaluation_report_path(temp_output_dir):
    """Provide path for saving evaluation reports."""
    return temp_output_dir / "evaluation_report.json"


class EvaluationAssertion:
    """Helper class for making assertions on evaluation results."""

    @staticmethod
    def assert_tool_called(
        result, tool_name: str, expected_args: dict[str, Any] = None
    ):
        """Assert that a specific tool was called."""
        tool_calls = [call for call in result.tool_calls if call.name == tool_name]
        assert tool_calls, f"Tool '{tool_name}' was not called"

        if expected_args:
            matching_calls = [
                call
                for call in tool_calls
                if all(call.args.get(k) == v for k, v in expected_args.items())
            ]
            assert matching_calls, (
                f"Tool '{tool_name}' was not called with expected args {expected_args}"
            )

    @staticmethod
    def assert_evaluation_passed(result, min_score: float = 0.8):
        """Assert that an evaluation passed with minimum score."""
        assert result.passed, f"Evaluation failed: {result.message}"
        assert result.score >= min_score, (
            f"Score {result.score} below minimum {min_score}"
        )

    @staticmethod
    def assert_no_errors(result):
        """Assert that no errors occurred during evaluation."""
        error_calls = [call for call in result.tool_calls if call.error]
        assert not error_calls, (
            f"Tool calls had errors: {[call.error for call in error_calls]}"
        )


@pytest.fixture
def eval_assert():
    """Provide evaluation assertion helper."""
    return EvaluationAssertion()


# Pytest markers for evaluation tests
def pytest_configure(config):
    """Configure pytest markers for evaluation tests."""
    config.addinivalue_line("markers", "eval: mark test as an evaluation test")
    config.addinivalue_line(
        "markers", "tool_call_eval: mark test as a tool call evaluation"
    )
    config.addinivalue_line(
        "markers", "expensive: mark test as expensive (requires AI model calls)"
    )
    config.addinivalue_line("markers", "integration: mark test as integration test")


# Skip evaluations if model not configured
def pytest_collection_modifyitems(config, items):
    """Modify test collection to skip evaluations if model not configured."""
    is_valid, error = validate_model_config()

    if not is_valid:
        skip_eval = pytest.mark.skip(reason=f"Model configuration error: {error}")
        for item in items:
            if "eval" in item.keywords:
                item.add_marker(skip_eval)
