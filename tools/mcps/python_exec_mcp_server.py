"""
FastMCP server for Python code execution with persistent sessions.

This module provides MCP tools for executing Python code in a persistent
IPython-based environment, allowing iterative development workflows.
"""

from fastmcp import FastMCP
from typing import Optional, Dict, Any, List
import sys
import io
import traceback
import subprocess
import json
import base64
import signal
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
import time
import re

# Add the tools directory to Python path so we can import loads
tools_dir = Path(__file__).parent.parent  # Go up one level from mcps to tools
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

try:
    from IPython.core.interactiveshell import InteractiveShell
    from IPython.core.magic import Magics, magics_class
    from IPython.utils.capture import capture_output

    IPYTHON_AVAILABLE = True
except ImportError:
    IPYTHON_AVAILABLE = False
    InteractiveShell = None


class ExecutionResult:
    """Container for code execution results."""

    def __init__(
        self,
        success: bool,
        result: Any = None,
        stdout: str = "",
        stderr: str = "",
        error: str = "",
        execution_time: float = 0.0,
        plots: List[str] = None,
        display_data: List[Dict] = None,
    ):
        self.success = success
        self.result = result
        self.stdout = stdout
        self.stderr = stderr
        self.error = error
        self.execution_time = execution_time
        self.plots = plots or []
        self.display_data = display_data or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "result": self._serialize_result(self.result),
            "stdout": self.stdout,
            "stderr": self.stderr,
            "error": self.error,
            "execution_time": self.execution_time,
            "plots": self.plots,
            "display_data": self.display_data,
        }

    def _serialize_result(self, obj: Any) -> Any:
        """Serialize result for JSON output."""
        if obj is None:
            return None

        # Handle pandas DataFrames
        try:
            import pandas as pd

            if isinstance(obj, pd.DataFrame):
                return {
                    "type": "DataFrame",
                    "shape": obj.shape,
                    "columns": obj.columns.tolist(),
                    "data": obj.head(10).to_dict("records"),  # Show first 10 rows
                    "full_repr": str(obj)
                    if len(obj) <= 100
                    else f"{str(obj[:5])}\\n...\\n{str(obj[-5:])}",
                }
        except ImportError:
            pass

        # Handle numpy arrays
        try:
            import numpy as np

            if isinstance(obj, np.ndarray):
                return {
                    "type": "ndarray",
                    "shape": obj.shape,
                    "dtype": str(obj.dtype),
                    "data": obj.tolist()
                    if obj.size <= 100
                    else "Array too large to display",
                    "full_repr": repr(obj),
                }
        except ImportError:
            pass

        try:
            # Try to represent the object as string
            return repr(obj)
        except Exception:
            return str(type(obj))


class PythonExecutorMCPProvider:
    """Provider class for Python code execution MCP operations with persistent sessions."""

    # Dangerous imports to filter
    DANGEROUS_IMPORTS = {
        "os",
        "subprocess",
        "sys",
        "shutil",
        "socket",
        "urllib",
        "requests",
        "http",
        "ftplib",
        "smtplib",
        "poplib",
        "imaplib",
        "telnetlib",
        "webbrowser",
        "__import__",
        "eval",
        "exec",
        "compile",
    }

    def __init__(self, enable_security: bool = True, execution_timeout: int = 30):
        self._shell: Optional[InteractiveShell] = None
        self._execution_history: List[Dict[str, Any]] = []
        self._execution_count = 0
        self._enable_security = enable_security
        self._execution_timeout = execution_timeout
        self._initialize_session()

    def _initialize_session(self):
        """Initialize the IPython interactive shell."""
        if not IPYTHON_AVAILABLE:
            raise ImportError(
                "IPython is required for Python execution. Install with: uv add ipython"
            )

        # Create IPython shell instance
        self._shell = InteractiveShell.instance()

        # Set up the namespace with project imports
        self._shell.user_ns.update(
            {
                "__execution_count__": 0,
                "__history__": [],
            }
        )

        # Try to import LoadSet classes if available
        try:
            self._shell.run_cell(
                "from loads import LoadSet, LoadCase, PointLoad, ForceMoment"
            )
            self._shell.run_cell("import numpy as np")
            self._shell.run_cell("import matplotlib")
            self._shell.run_cell("matplotlib.use('Agg')")  # Use non-interactive backend
            self._shell.run_cell("import matplotlib.pyplot as plt")
            self._shell.run_cell("plt.ioff()")  # Turn off interactive mode for plots
        except Exception:
            pass  # Imports are optional

    def _check_security(self, code: str) -> tuple[bool, str]:
        """Check code for security issues."""
        if not self._enable_security:
            return True, ""

        # Check for dangerous imports
        import_pattern = r"(?:^|\s)(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*)"
        imports = re.findall(import_pattern, code, re.MULTILINE)

        dangerous_found = [imp for imp in imports if imp in self.DANGEROUS_IMPORTS]
        if dangerous_found:
            return False, f"Dangerous imports detected: {', '.join(dangerous_found)}"

        # Check for dangerous function calls
        dangerous_patterns = [
            r"\beval\s*\(",
            r"\bexec\s*\(",
            r"\b__import__\s*\(",
            r"\bopen\s*\(",  # File operations
            r"\.system\s*\(",
            r"\.popen\s*\(",
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, code):
                return False, f"Dangerous operation detected: {pattern}"

        return True, ""

    def _capture_plots(self) -> List[str]:
        """Capture matplotlib plots as base64 encoded PNG images."""
        plots = []
        try:
            import matplotlib.pyplot as plt

            # Get all figures
            for fig_num in plt.get_fignums():
                fig = plt.figure(fig_num)

                # Save to bytes buffer
                buffer = io.BytesIO()
                fig.savefig(buffer, format="png", bbox_inches="tight", dpi=100)
                buffer.seek(0)

                # Encode as base64
                plot_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
                plots.append(plot_data)

                # Close the figure to free memory
                plt.close(fig)

        except ImportError:
            pass  # matplotlib not available
        except Exception:
            pass  # Other plotting errors

        return plots

    def _capture_execution(self, code: str) -> ExecutionResult:
        """Execute code and capture all outputs."""
        if self._shell is None:
            return ExecutionResult(success=False, error="IPython shell not initialized")

        # Security check
        secure, security_error = self._check_security(code)
        if not secure:
            return ExecutionResult(
                success=False, error=f"Security check failed: {security_error}"
            )

        start_time = time.time()

        # Capture stdout and stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Execute the code
                result = self._shell.run_cell(code, silent=False)

                execution_time = time.time() - start_time

                # Capture any plots that were created
                plots = self._capture_plots()

                if result.success:
                    return ExecutionResult(
                        success=True,
                        result=result.result,
                        stdout=stdout_capture.getvalue(),
                        stderr=stderr_capture.getvalue(),
                        execution_time=execution_time,
                        plots=plots,
                    )
                else:
                    error_msg = ""
                    if result.error_before_exec:
                        error_msg = str(result.error_before_exec)
                    elif result.error_in_exec:
                        error_msg = str(result.error_in_exec)

                    return ExecutionResult(
                        success=False,
                        stdout=stdout_capture.getvalue(),
                        stderr=stderr_capture.getvalue(),
                        error=error_msg,
                        execution_time=execution_time,
                        plots=plots,
                    )

        except Exception as e:
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue(),
                error=f"Execution error: {str(e)}",
                execution_time=execution_time,
            )

    def execute_code(self, code: str) -> dict:
        """
        Execute Python code in the persistent session.

        Args:
            code: Python code to execute

        Returns:
            dict: Execution result with output and any errors
        """
        try:
            self._execution_count += 1

            # Execute the code
            result = self._capture_execution(code)

            # Store in history
            history_entry = {
                "execution_count": self._execution_count,
                "code": code,
                "timestamp": time.time(),
                **result.to_dict(),
            }
            self._execution_history.append(history_entry)

            # Keep history manageable (last 100 executions)
            if len(self._execution_history) > 100:
                self._execution_history = self._execution_history[-100:]

            return {
                "success": True,
                "execution_count": self._execution_count,
                **result.to_dict(),
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Code execution failed: {str(e)}",
                "execution_count": self._execution_count,
            }

    def list_variables(self) -> dict:
        """
        List all variables in the current session namespace.

        Returns:
            dict: Dictionary of variable names and their types/values
        """
        if self._shell is None:
            return {"success": False, "error": "IPython shell not initialized"}

        try:
            variables = {}
            user_ns = self._shell.user_ns

            # Filter out built-ins and private variables
            for name, value in user_ns.items():
                if (
                    not name.startswith("_")
                    and not callable(value)
                    or name in ["LoadSet", "LoadCase", "PointLoad", "ForceMoment"]
                ):
                    try:
                        variables[name] = {
                            "type": type(value).__name__,
                            "value": repr(value)[:200]
                            + ("..." if len(repr(value)) > 200 else ""),
                            "module": getattr(type(value), "__module__", "builtins"),
                        }
                    except Exception:
                        variables[name] = {
                            "type": type(value).__name__,
                            "value": "<repr failed>",
                            "module": getattr(type(value), "__module__", "builtins"),
                        }

            return {
                "success": True,
                "variables": variables,
                "total_count": len(variables),
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to list variables: {str(e)}"}

    def get_variable(self, name: str) -> dict:
        """
        Get detailed information about a specific variable.

        Args:
            name: Variable name to inspect

        Returns:
            dict: Detailed variable information
        """
        if self._shell is None:
            return {"success": False, "error": "IPython shell not initialized"}

        try:
            if name not in self._shell.user_ns:
                return {
                    "success": False,
                    "error": f"Variable '{name}' not found in namespace",
                }

            value = self._shell.user_ns[name]

            info = {
                "name": name,
                "type": type(value).__name__,
                "module": getattr(type(value), "__module__", "builtins"),
                "value": repr(value),
                "doc": getattr(value, "__doc__", None),
            }

            # Add special handling for common types
            if hasattr(value, "shape"):  # numpy arrays, pandas dataframes
                info["shape"] = str(value.shape)
            if hasattr(value, "__len__") and not isinstance(value, str):
                try:
                    info["length"] = len(value)
                except Exception:
                    pass

            return {"success": True, "variable_info": info}

        except Exception as e:
            return {"success": False, "error": f"Failed to get variable info: {str(e)}"}

    def reset_session(self) -> dict:
        """
        Reset the Python session, clearing all variables and history.

        Returns:
            dict: Reset confirmation
        """
        try:
            # Clear the namespace but keep built-ins
            if self._shell:
                # Reset the shell
                self._shell.reset(new_session=False)

            # Reinitialize
            self._initialize_session()

            # Clear history
            self._execution_history.clear()
            self._execution_count = 0

            return {
                "success": True,
                "message": "Python session reset successfully",
                "execution_count": self._execution_count,
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to reset session: {str(e)}"}

    def install_package(self, package_name: str, dev: bool = False) -> dict:
        """
        Install a Python package using uv.

        Args:
            package_name: Name of the package to install
            dev: Whether to install as a development dependency

        Returns:
            dict: Installation result
        """
        try:
            # Build uv command
            cmd = ["uv", "add"]
            if dev:
                cmd.append("--dev")
            cmd.append(package_name)

            # Run the command
            result = subprocess.run(
                cmd,
                cwd=tools_dir.parent,  # Run from project root
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode == 0:
                # Try to import the package in the session
                try:
                    import importlib

                    importlib.invalidate_caches()

                    return {
                        "success": True,
                        "message": f"Package '{package_name}' installed successfully",
                        "stdout": result.stdout,
                        "package_name": package_name,
                        "dev_dependency": dev,
                    }
                except Exception as import_error:
                    return {
                        "success": True,
                        "message": f"Package '{package_name}' installed but import failed",
                        "stdout": result.stdout,
                        "import_warning": str(import_error),
                        "package_name": package_name,
                        "dev_dependency": dev,
                    }
            else:
                return {
                    "success": False,
                    "error": f"Package installation failed: {result.stderr}",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "package_name": package_name,
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Package installation timed out after 5 minutes",
                "package_name": package_name,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Installation error: {str(e)}",
                "package_name": package_name,
            }

    def get_execution_history(self, limit: int = 10) -> dict:
        """
        Get recent execution history.

        Args:
            limit: Maximum number of history entries to return

        Returns:
            dict: Recent execution history
        """
        try:
            # Get the most recent entries
            recent_history = (
                self._execution_history[-limit:]
                if limit > 0
                else self._execution_history
            )

            return {
                "success": True,
                "history": recent_history,
                "total_executions": len(self._execution_history),
                "current_execution_count": self._execution_count,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get execution history: {str(e)}",
            }

    def configure_security(
        self, enable_security: bool = True, execution_timeout: int = 30
    ) -> dict:
        """
        Configure security settings for code execution.

        Args:
            enable_security: Whether to enable security filtering
            execution_timeout: Maximum execution time in seconds

        Returns:
            dict: Configuration confirmation
        """
        try:
            self._enable_security = enable_security
            self._execution_timeout = execution_timeout

            return {
                "success": True,
                "message": "Security configuration updated",
                "enable_security": enable_security,
                "execution_timeout": execution_timeout,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to configure security: {str(e)}",
            }


def create_mcp_server() -> FastMCP:
    """
    Create and configure the FastMCP server for Python code execution.

    Returns:
        FastMCP: Configured MCP server instance
    """
    mcp = FastMCP("Python Executor MCP Server")
    provider = PythonExecutorMCPProvider()

    # Register all methods as tools
    mcp.tool(provider.execute_code)
    mcp.tool(provider.list_variables)
    mcp.tool(provider.get_variable)
    mcp.tool(provider.reset_session)
    mcp.tool(provider.install_package)
    mcp.tool(provider.get_execution_history)
    mcp.tool(provider.configure_security)

    return mcp


if __name__ == "__main__":
    import sys
    from typing import Literal

    # Check IPython availability
    if not IPYTHON_AVAILABLE:
        print("Error: IPython is required for Python execution.")
        print("Install with: uv add ipython")
        sys.exit(1)

    # Allow transport to be specified via command line argument
    transport: Literal["stdio", "http"] = "http"  # Default to HTTP

    # Check for command line argument
    if len(sys.argv) > 1 and sys.argv[1] in ["stdio", "http"]:
        transport = sys.argv[1]  # type: ignore

    server = create_mcp_server()
    server.run(transport=transport)
