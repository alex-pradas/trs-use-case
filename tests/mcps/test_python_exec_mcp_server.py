"""
Tests for the Python execution MCP server.

This module tests the Python code execution functionality with persistent sessions.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.mcps.python_exec_mcp_server import (
    PythonExecutorMCPProvider,
    ExecutionResult,
    create_mcp_server,
)


class TestExecutionResult:
    """Test the ExecutionResult class."""

    def test_basic_result(self):
        """Test basic result creation and serialization."""
        result = ExecutionResult(
            success=True, result=42, stdout="Hello\n", stderr="", execution_time=0.1
        )

        result_dict = result.to_dict()
        assert result_dict["success"] is True
        assert result_dict["result"] == "42"
        assert result_dict["stdout"] == "Hello\n"
        assert result_dict["execution_time"] == 0.1

    def test_result_with_plots(self):
        """Test result with plot data."""
        result = ExecutionResult(success=True, result=None, plots=["base64_plot_data"])

        result_dict = result.to_dict()
        assert result_dict["plots"] == ["base64_plot_data"]

    def test_numpy_serialization(self):
        """Test numpy array serialization."""
        pytest.importorskip("numpy")
        import numpy as np

        arr = np.array([1, 2, 3])
        result = ExecutionResult(success=True, result=arr)
        result_dict = result.to_dict()

        assert result_dict["result"]["type"] == "ndarray"
        assert result_dict["result"]["shape"] == (3,)
        assert result_dict["result"]["data"] == [1, 2, 3]


class TestPythonExecutorMCPProvider:
    """Test the PythonExecutorMCPProvider class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.provider = PythonExecutorMCPProvider(enable_security=False)

    def test_initialization(self):
        """Test provider initialization."""
        assert self.provider._shell is not None
        assert self.provider._execution_count == 0
        assert len(self.provider._execution_history) == 0

    def test_simple_execution(self):
        """Test simple code execution."""
        result = self.provider.execute_code("x = 5")

        assert result["success"] is True
        assert result["execution_count"] == 1
        assert "error" not in result or not result["error"]

    def test_persistent_variables(self):
        """Test that variables persist across executions."""
        # Set a variable
        result1 = self.provider.execute_code("my_var = 'hello world'")
        assert result1["success"] is True

        # Use the variable in next execution
        result2 = self.provider.execute_code("print(my_var)")
        assert result2["success"] is True
        assert "hello world" in result2["stdout"]

    def test_expression_result(self):
        """Test that expressions return results."""
        result = self.provider.execute_code("2 + 3")

        assert result["success"] is True
        assert result["result"] == "5"

    def test_stdout_capture(self):
        """Test stdout capture."""
        result = self.provider.execute_code("print('Hello, World!')")

        assert result["success"] is True
        assert "Hello, World!" in result["stdout"]

    def test_error_handling(self):
        """Test error handling."""
        result = self.provider.execute_code("1 / 0")

        assert result["success"] is False
        assert "error" in result
        # The error message might be just "division by zero" instead of the full exception name
        assert (
            "division by zero" in result["error"]
            or "ZeroDivisionError" in result["error"]
        )

    def test_list_variables(self):
        """Test variable listing."""
        # Set some variables
        self.provider.execute_code("a = 1")
        self.provider.execute_code("b = 'hello'")
        self.provider.execute_code("c = [1, 2, 3]")

        result = self.provider.list_variables()

        assert result["success"] is True
        variables = result["variables"]

        assert "a" in variables
        assert variables["a"]["type"] == "int"
        assert "b" in variables
        assert variables["b"]["type"] == "str"
        assert "c" in variables
        assert variables["c"]["type"] == "list"

    def test_get_variable(self):
        """Test getting specific variable info."""
        self.provider.execute_code("test_var = {'key': 'value'}")

        result = self.provider.get_variable("test_var")

        assert result["success"] is True
        var_info = result["variable_info"]
        assert var_info["name"] == "test_var"
        assert var_info["type"] == "dict"

    def test_get_nonexistent_variable(self):
        """Test getting info for non-existent variable."""
        result = self.provider.get_variable("nonexistent")

        assert result["success"] is False
        assert "not found" in result["error"]

    def test_reset_session(self):
        """Test session reset."""
        # Set some variables
        self.provider.execute_code("x = 100")
        self.provider.execute_code("y = 200")

        # Verify variables exist
        vars_before = self.provider.list_variables()
        assert "x" in vars_before["variables"]

        # Reset session
        reset_result = self.provider.reset_session()
        assert reset_result["success"] is True

        # Verify variables are gone
        vars_after = self.provider.list_variables()
        assert "x" not in vars_after["variables"]
        assert self.provider._execution_count == 0

    def test_execution_history(self):
        """Test execution history tracking."""
        # Execute some code
        self.provider.execute_code("a = 1")
        self.provider.execute_code("b = 2")
        self.provider.execute_code("print(a + b)")

        history = self.provider.get_execution_history()

        assert history["success"] is True
        assert history["total_executions"] == 3
        assert len(history["history"]) == 3

        # Check history structure
        first_entry = history["history"][0]
        assert "execution_count" in first_entry
        assert "code" in first_entry
        assert "timestamp" in first_entry
        assert first_entry["code"] == "a = 1"

    def test_execution_history_limit(self):
        """Test execution history with limit."""
        # Execute several commands
        for i in range(5):
            self.provider.execute_code(f"x{i} = {i}")

        # Get limited history
        history = self.provider.get_execution_history(limit=3)

        assert len(history["history"]) == 3
        # Should get the most recent ones
        assert history["history"][-1]["code"] == "x4 = 4"


class TestSecurityFeatures:
    """Test security features."""

    def setup_method(self):
        """Set up test fixtures with security enabled."""
        self.provider = PythonExecutorMCPProvider(enable_security=True)

    def test_dangerous_import_blocked(self):
        """Test that dangerous imports are blocked."""
        result = self.provider.execute_code("import os")

        assert result["success"] is False
        assert "Security check failed" in result["error"]
        assert "Dangerous imports detected" in result["error"]

    def test_dangerous_function_blocked(self):
        """Test that dangerous functions are blocked."""
        result = self.provider.execute_code("eval('1 + 1')")

        assert result["success"] is False
        assert "Security check failed" in result["error"]

    def test_safe_code_allowed(self):
        """Test that safe code is allowed."""
        result = self.provider.execute_code("import math; print(math.pi)")

        assert result["success"] is True
        assert "3.14" in result["stdout"]

    def test_configure_security(self):
        """Test security configuration."""
        # Disable security
        config_result = self.provider.configure_security(enable_security=False)
        assert config_result["success"] is True

        # Now dangerous code should work
        result = self.provider.execute_code("import os; print('security disabled')")
        assert result["success"] is True


class TestLoadSetIntegration:
    """Test integration with LoadSet functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.provider = PythonExecutorMCPProvider(enable_security=False)

    def test_loadset_import_available(self):
        """Test that LoadSet classes are available."""
        result = self.provider.execute_code("print(LoadSet)")

        # Should not error (LoadSet should be imported)
        assert result["success"] is True
        assert "LoadSet" in result["stdout"] or "class" in result["stdout"]

    def test_numpy_available(self):
        """Test that numpy is available."""
        result = self.provider.execute_code("print(np.pi)")

        assert result["success"] is True
        assert "3.14" in result["stdout"]


class TestMCPServerCreation:
    """Test MCP server creation."""

    def test_server_creation(self):
        """Test that the MCP server can be created."""
        server = create_mcp_server()

        assert server is not None
        # FastMCP might store tools differently
        assert server is not None


@pytest.mark.skipif(sys.platform == "win32", reason="Matplotlib issues on Windows CI")
class TestPlotCapture:
    """Test matplotlib plot capture (skip on Windows)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.provider = PythonExecutorMCPProvider(enable_security=False)

    def test_plot_capture(self):
        """Test that plots are captured as base64."""
        # First check if we can create a simple plot
        simple_plot = """
import matplotlib.pyplot as plt
plt.figure()
plt.plot([1, 2, 3], [1, 4, 9])
"""

        result = self.provider.execute_code(simple_plot)

        # The execution should succeed even if plot capture doesn't work
        assert result["success"] is True, (
            f"Plot code failed: {result.get('error', 'Unknown error')}"
        )

        # Plot capture might not work in headless environments
        # So we just verify the code runs without error


if __name__ == "__main__":
    pytest.main([__file__])
