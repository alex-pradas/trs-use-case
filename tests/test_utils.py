"""
Common test utilities for the TRS use case test suite.

This module provides shared utilities and base classes to reduce code duplication
across test files.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def setup_python_path():
    """
    Set up Python path to include project root and tools directory.

    This function should be called at the top of test files to ensure
    proper imports work.
    """
    # Get the tests directory (parent of this file)
    tests_dir = Path(__file__).parent

    # Add the project root to Python path
    project_root = tests_dir.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Add tools directory for clean architecture
    tools_path = project_root / "tools"
    if str(tools_path) not in sys.path:
        sys.path.insert(0, str(tools_path))

    return project_root, tools_path


class TempDirectoryTestBase:
    """Base class for tests that need temporary directories."""

    def setup_method(self):
        """Set up test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up temporary directory."""
        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def create_temp_file(self, name: str, content: str = "") -> Path:
        """
        Create a temporary file with given name and content.

        Args:
            name: File name
            content: File content

        Returns:
            Path to the created file
        """
        file_path = self.temp_path / name
        file_path.write_text(content)
        return file_path

    def create_temp_subdir(self, name: str) -> Path:
        """
        Create a temporary subdirectory.

        Args:
            name: Directory name

        Returns:
            Path to the created directory
        """
        dir_path = self.temp_path / name
        dir_path.mkdir(exist_ok=True)
        return dir_path


def validate_model_config_with_skip() -> tuple[bool, str | None]:
    """
    Validate model configuration and return skip message if invalid.

    This is a wrapper around the model_config validation that's suitable
    for use in pytest tests.

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        from tools.model_config import validate_model_config

        return validate_model_config()
    except ImportError:
        return False, "Could not import model_config module"


def skip_if_no_model_config(test_func):
    """
    Decorator to skip test if model configuration is invalid.

    Usage:
        @skip_if_no_model_config
        async def test_something():
            ...
    """
    import pytest
    import functools

    @functools.wraps(test_func)
    def wrapper(*args, **kwargs):
        is_valid, error = validate_model_config_with_skip()
        if not is_valid:
            pytest.skip(f"Model configuration error: {error}")
        return test_func(*args, **kwargs)

    return wrapper


def reset_mcp_state():
    """Reset MCP server global state if available."""
    try:
        from tools.mcps.loads_mcp_server import reset_global_state

        reset_global_state()
    except ImportError:
        pass


class MCPTestBase(TempDirectoryTestBase):
    """Base class for tests that use MCP servers."""

    def setup_method(self):
        """Set up test environment with MCP state reset."""
        super().setup_method()
        reset_mcp_state()

    def teardown_method(self):
        """Clean up test environment and reset MCP state."""
        super().teardown_method()
        reset_mcp_state()


def create_sample_loadset_data() -> dict:
    """
    Create sample LoadSet data for testing.

    Returns:
        Dictionary with sample LoadSet structure
    """
    return {
        "name": "Test Load Set",
        "version": 1,
        "description": "Test load set for unit testing",
        "units": {"forces": "N", "moments": "Nm"},
        "load_cases": [
            {
                "name": "Test Case 1",
                "description": "First test case",
                "point_loads": [
                    {
                        "name": "Point A",
                        "force_moment": {
                            "fx": 100.0,
                            "fy": 200.0,
                            "fz": 300.0,
                            "mx": 50.0,
                            "my": 75.0,
                            "mz": 100.0,
                        },
                    },
                    {
                        "name": "Point B",
                        "force_moment": {
                            "fx": 150.0,
                            "fy": 250.0,
                            "fz": 0.0,
                            "mx": 60.0,
                            "my": 0.0,
                            "mz": 0.0,
                        },
                    },
                ],
            },
            {
                "name": "Test Case 2",
                "description": "Second test case",
                "point_loads": [
                    {
                        "name": "Point A",
                        "force_moment": {
                            "fx": 80.0,
                            "fy": 120.0,
                            "fz": 160.0,
                            "mx": 40.0,
                            "my": 60.0,
                            "mz": 80.0,
                        },
                    }
                ],
            },
        ],
    }


def assert_valid_ansys_file(file_path: Path, expected_commands: list = None):
    """
    Assert that an ANSYS file has valid format and expected commands.

    Args:
        file_path: Path to ANSYS file
        expected_commands: Optional list of commands that should be present
    """
    assert file_path.exists(), f"ANSYS file {file_path} does not exist"

    content = file_path.read_text()

    # Basic ANSYS format checks
    assert "f,all," in content, "ANSYS file should contain force commands"
    assert "/TITLE," in content or "nsel," in content, (
        "ANSYS file should have valid commands"
    )

    # Check for expected commands if provided
    if expected_commands:
        for cmd in expected_commands:
            assert cmd in content, f"Expected command '{cmd}' not found in ANSYS file"


# Commonly used test marks
expensive = "pytest.mark.expensive"
slow = "pytest.mark.slow"
integration = "pytest.mark.integration"
unit = "pytest.mark.unit"
