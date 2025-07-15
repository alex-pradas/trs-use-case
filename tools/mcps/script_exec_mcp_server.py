"""
FastMCP server for Python script execution with file I/O.

This module provides MCP tools for executing complete Python scripts
and transferring output files between agent and execution environment.
"""

from fastmcp import FastMCP
from typing import Optional, Dict, Any, List
import sys
import subprocess
import json
import base64
import tempfile
import shutil
import time
import signal
from pathlib import Path
from dataclasses import dataclass, asdict
import hashlib
import os

# Add the tools directory to Python path so we can import loads
tools_dir = Path(__file__).parent.parent  # Go up one level from mcps to tools
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))


@dataclass
class ExecutionResult:
    """Result of script execution."""

    success: bool
    exit_code: int
    stdout: str
    stderr: str
    error: str
    execution_time: float
    output_files: List[str]
    workspace_path: str
    script_hash: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class FileInfo:
    """Information about a file in the workspace."""

    name: str
    path: str
    size: int
    is_directory: bool
    modified_time: float
    file_hash: str


class ScriptExecutorMCPProvider:
    """Provider class for Python script execution with file I/O capabilities."""

    def __init__(
        self, base_workspace_dir: Optional[Path] = None, execution_timeout: int = 300
    ):
        """
        Initialize the script executor.

        Args:
            base_workspace_dir: Base directory for workspaces (defaults to temp)
            execution_timeout: Maximum execution time in seconds
        """
        self.base_workspace_dir = (
            base_workspace_dir or Path(tempfile.gettempdir()) / "script_exec_workspaces"
        )
        self.execution_timeout = execution_timeout
        self.current_workspace: Optional[Path] = None
        self.last_execution: Optional[ExecutionResult] = None

        # Ensure base directory exists
        self.base_workspace_dir.mkdir(parents=True, exist_ok=True)

        # LoadSet template imports for scripts
        # Get the absolute path to the tools directory from this server file
        server_tools_dir = Path(
            __file__
        ).parent.parent.absolute()  # Go up one level from mcps to tools

        self.loadset_imports = f'''
import sys
from pathlib import Path

# Add tools directory to path for LoadSet imports
tools_dir = Path(r"{server_tools_dir}")
sys.path.insert(0, str(tools_dir))

try:
    from loads import LoadSet, LoadCase, PointLoad, ForceMoment, ForceUnit
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
except ImportError as e:
    print(f"Import error: {{e}}")
    # Continue anyway
'''

    def _create_workspace(self) -> Path:
        """Create a new temporary workspace directory."""
        workspace_id = f"workspace_{int(time.time())}_{id(self)}"
        workspace_path = self.base_workspace_dir / workspace_id
        workspace_path.mkdir(parents=True, exist_ok=True)
        return workspace_path

    def _cleanup_workspace(self, workspace_path: Path) -> None:
        """Clean up a workspace directory."""
        try:
            if workspace_path.exists():
                shutil.rmtree(workspace_path)
        except Exception as e:
            print(f"Warning: Failed to cleanup workspace {workspace_path}: {e}")

    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file."""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception:
            return ""

    def _get_script_hash(self, script_content: str) -> str:
        """Calculate hash of script content."""
        return hashlib.sha256(script_content.encode()).hexdigest()[:16]

    def _find_output_files(self, workspace_path: Path, initial_files: set) -> List[str]:
        """Find new files created during execution."""
        output_files = []
        try:
            for file_path in workspace_path.rglob("*"):
                if file_path.is_file() and str(file_path) not in initial_files:
                    # Make path relative to workspace
                    relative_path = file_path.relative_to(workspace_path)
                    output_files.append(str(relative_path))
        except Exception as e:
            print(f"Warning: Error finding output files: {e}")
        return output_files

    def execute_python_script(
        self,
        script_content: str,
        script_name: str = "script.py",
        include_loadset_imports: bool = True,
        cleanup_workspace: bool = False,
    ) -> dict:
        """
        Execute a Python script in an isolated workspace.

        Args:
            script_content: The Python script code to execute
            script_name: Name for the script file
            include_loadset_imports: Whether to prepend LoadSet imports
            cleanup_workspace: Whether to cleanup workspace after execution

        Returns:
            dict: Execution result with output files information
        """
        workspace_path = self._create_workspace()
        self.current_workspace = workspace_path

        # Record initial files
        initial_files = {str(p) for p in workspace_path.rglob("*") if p.is_file()}

        try:
            # Prepare script content
            if include_loadset_imports:
                full_script = self.loadset_imports + "\n\n" + script_content
            else:
                full_script = script_content

            # Write script to workspace
            script_path = workspace_path / script_name
            script_path.write_text(full_script, encoding="utf-8")

            # Calculate script hash
            script_hash = self._get_script_hash(script_content)

            # Execute script
            start_time = time.time()

            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=self.execution_timeout,
            )

            execution_time = time.time() - start_time

            # Find output files
            output_files = self._find_output_files(workspace_path, initial_files)

            # Create execution result
            execution_result = ExecutionResult(
                success=result.returncode == 0,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                error=""
                if result.returncode == 0
                else f"Script failed with exit code {result.returncode}",
                execution_time=execution_time,
                output_files=output_files,
                workspace_path=str(workspace_path),
                script_hash=script_hash,
            )

            self.last_execution = execution_result

            # Cleanup if requested
            if cleanup_workspace:
                self._cleanup_workspace(workspace_path)
                self.current_workspace = None

            return {"success": True, "execution_result": execution_result.to_dict()}

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Script execution timed out after {self.execution_timeout} seconds",
                "workspace_path": str(workspace_path),
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Script execution failed: {str(e)}",
                "workspace_path": str(workspace_path),
            }

    def list_output_files(self) -> dict:
        """
        List all files in the current workspace.

        Returns:
            dict: List of files with metadata
        """
        if not self.current_workspace or not self.current_workspace.exists():
            return {"success": False, "error": "No active workspace"}

        try:
            files = []
            for file_path in self.current_workspace.rglob("*"):
                relative_path = file_path.relative_to(self.current_workspace)

                file_info = FileInfo(
                    name=file_path.name,
                    path=str(relative_path),
                    size=file_path.stat().st_size if file_path.is_file() else 0,
                    is_directory=file_path.is_dir(),
                    modified_time=file_path.stat().st_mtime,
                    file_hash=self._get_file_hash(file_path)
                    if file_path.is_file()
                    else "",
                )
                files.append(asdict(file_info))

            return {
                "success": True,
                "files": files,
                "workspace_path": str(self.current_workspace),
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to list files: {str(e)}"}

    def download_file(self, file_path: str, encoding: str = "base64") -> dict:
        """
        Download a file from the workspace.

        Args:
            file_path: Relative path to file in workspace
            encoding: Encoding format ("base64", "text", "binary")

        Returns:
            dict: File content and metadata
        """
        if not self.current_workspace or not self.current_workspace.exists():
            return {"success": False, "error": "No active workspace"}

        try:
            full_path = self.current_workspace / file_path
            if not full_path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}

            if not full_path.is_file():
                return {"success": False, "error": f"Path is not a file: {file_path}"}

            file_size = full_path.stat().st_size
            if file_size > 100 * 1024 * 1024:  # 100MB limit
                return {
                    "success": False,
                    "error": f"File too large: {file_size} bytes (max 100MB)",
                }

            # Read file content based on encoding
            if encoding == "base64":
                with open(full_path, "rb") as f:
                    content = base64.b64encode(f.read()).decode("utf-8")
            elif encoding == "text":
                content = full_path.read_text(encoding="utf-8")
            else:
                return {"success": False, "error": f"Unsupported encoding: {encoding}"}

            return {
                "success": True,
                "file_path": file_path,
                "content": content,
                "encoding": encoding,
                "size": file_size,
                "file_hash": self._get_file_hash(full_path),
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to download file: {str(e)}"}

    def upload_file(
        self, file_path: str, content: str, encoding: str = "base64"
    ) -> dict:
        """
        Upload a file to the workspace.

        Args:
            file_path: Relative path for the file in workspace
            content: File content
            encoding: Content encoding ("base64", "text")

        Returns:
            dict: Upload result
        """
        if not self.current_workspace:
            # Create workspace if needed
            self.current_workspace = self._create_workspace()

        try:
            full_path = self.current_workspace / file_path

            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file content based on encoding
            if encoding == "base64":
                with open(full_path, "wb") as f:
                    f.write(base64.b64decode(content))
            elif encoding == "text":
                full_path.write_text(content, encoding="utf-8")
            else:
                return {"success": False, "error": f"Unsupported encoding: {encoding}"}

            return {
                "success": True,
                "file_path": file_path,
                "size": full_path.stat().st_size,
                "workspace_path": str(self.current_workspace),
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to upload file: {str(e)}"}

    def get_execution_result(self) -> dict:
        """
        Get the result of the last script execution.

        Returns:
            dict: Last execution result
        """
        if not self.last_execution:
            return {"success": False, "error": "No execution result available"}

        return {"success": True, "execution_result": self.last_execution.to_dict()}

    def reset_workspace(self, cleanup_current: bool = True) -> dict:
        """
        Reset the workspace, optionally cleaning up the current one.

        Args:
            cleanup_current: Whether to delete the current workspace

        Returns:
            dict: Reset confirmation
        """
        try:
            old_workspace = self.current_workspace

            if cleanup_current and old_workspace:
                self._cleanup_workspace(old_workspace)

            self.current_workspace = None
            self.last_execution = None

            return {
                "success": True,
                "message": "Workspace reset successfully",
                "cleaned_up": str(old_workspace)
                if old_workspace and cleanup_current
                else None,
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to reset workspace: {str(e)}"}

    def get_workspace_info(self) -> dict:
        """
        Get information about the current workspace.

        Returns:
            dict: Workspace information
        """
        return {
            "success": True,
            "current_workspace": str(self.current_workspace)
            if self.current_workspace
            else None,
            "base_workspace_dir": str(self.base_workspace_dir),
            "execution_timeout": self.execution_timeout,
            "has_last_execution": self.last_execution is not None,
        }


def create_mcp_server(
    base_workspace_dir: Optional[Path] = None, execution_timeout: int = 300
) -> FastMCP:
    """
    Create and configure the FastMCP server for script execution.

    Args:
        base_workspace_dir: Base directory for workspaces
        execution_timeout: Script execution timeout in seconds

    Returns:
        FastMCP: Configured server instance
    """
    # Create MCP server
    mcp = FastMCP("Script Execution Server")

    # Create provider instance
    provider = ScriptExecutorMCPProvider(base_workspace_dir, execution_timeout)

    # Register tools
    mcp.tool(provider.execute_python_script)
    mcp.tool(provider.list_output_files)
    mcp.tool(provider.download_file)
    mcp.tool(provider.upload_file)
    mcp.tool(provider.get_execution_result)
    mcp.tool(provider.reset_workspace)
    mcp.tool(provider.get_workspace_info)

    return mcp


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Script Execution MCP Server")
    parser.add_argument(
        "transport",
        choices=["http", "stdio"],
        default="http",
        nargs="?",
        help="Transport type (default: http)",
    )
    parser.add_argument(
        "--port", type=int, default=8002, help="HTTP port (default: 8002)"
    )
    parser.add_argument(
        "--timeout", type=int, default=300, help="Execution timeout in seconds"
    )

    args = parser.parse_args()

    # Create server
    server = create_mcp_server(execution_timeout=args.timeout)

    if args.transport == "http":
        print(f"Starting Script Execution MCP server on HTTP port {args.port}")
        server.run(transport="http", port=args.port)
    else:
        print("Starting Script Execution MCP server on stdio")
        server.run()
