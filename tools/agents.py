"""
Simplified pydantic-ai agents following best practices.

This module implements the new simplified agent architecture using:
- Dependency injection for MCP servers
- RunContext for accessing dependencies in tools
- Structured Pydantic models for responses
- Centralized error handling via pydantic-ai
- Elimination of MCP bridge abstraction

Expected code reduction: 60% (from 400 to ~160 lines)
"""

from pydantic_ai import Agent, RunContext

from tools.model_config import get_model_name
from tools.dependencies import MCPServerProvider, get_default_mcp_provider
from tools.response_models import (
    LoadSetResponse,
    ConversionResponse,
    ExecutionResponse,
    ScriptResponse,
    ComparisonResponse,
    ExportResponse,
    SessionResponse,
    FileOperationResponse,
    WorkspaceResponse,
)


def create_loadset_agent(
    system_prompt: str | None = None,
) -> Agent[MCPServerProvider, str]:
    """Create a LoadSet processing agent with dependency injection."""
    default_prompt = "You are an expert aerospace structural loads analyst with access to LoadSet processing tools. Use available tools for operations and provide clear explanations."

    agent = Agent(
        get_model_name(),
        deps_type=MCPServerProvider,
        system_prompt=system_prompt or default_prompt,
    )

    @agent.tool
    def load_from_json(
        ctx: RunContext[MCPServerProvider], file_path: str
    ) -> LoadSetResponse:
        """Load a LoadSet from a JSON file."""
        result = ctx.deps.loads_server._tool_manager._tools["load_from_json"].fn(
            file_path=file_path
        )

        # Check if the MCP server returned an error
        if not result.get("success", True):
            return LoadSetResponse(
                success=False,
                message=result.get("error", "Failed to load LoadSet"),
                data=result,
                load_cases_count=None,
            )

        return LoadSetResponse(
            success=True,
            message=f"LoadSet loaded from {file_path}",
            data=result,
            load_cases_count=len(result.get("load_cases", [])) if result else None,
        )

    @agent.tool
    def convert_units(
        ctx: RunContext[MCPServerProvider], target_units: str
    ) -> ConversionResponse:
        """Convert the current LoadSet to different units."""
        result = ctx.deps.loads_server._tool_manager._tools["convert_units"].fn(
            target_units=target_units
        )

        # Check if the MCP server returned an error
        if not result.get("success", True):
            return ConversionResponse(
                success=False,
                message=result.get("error", "Unit conversion failed"),
                original_units={},
                target_units={},
                conversion_factor=1.0,
            )

        return ConversionResponse(
            success=True,
            message=f"Units converted to {target_units}",
            original_units=result.get("original_units", {}),
            target_units=result.get("new_units", {}),
            conversion_factor=result.get("conversion_factor", 1.0),
        )

    @agent.tool
    def scale_loads(
        ctx: RunContext[MCPServerProvider], factor: float
    ) -> LoadSetResponse:
        """Scale all loads in the current LoadSet by a factor."""
        result = ctx.deps.loads_server._tool_manager._tools["scale_loads"].fn(
            factor=factor
        )

        # Check if the MCP server returned an error
        if not result.get("success", True):
            return LoadSetResponse(
                success=False,
                message=result.get("error", "Failed to scale loads"),
                data=result,
            )

        return LoadSetResponse(
            success=True, message=f"Loads scaled by factor {factor}", data=result
        )

    @agent.tool
    def export_to_ansys(
        ctx: RunContext[MCPServerProvider], folder_path: str, name_stem: str
    ) -> ExportResponse:
        """Export the current LoadSet to ANSYS format files."""
        result = ctx.deps.loads_server._tool_manager._tools["export_to_ansys"].fn(
            folder_path=folder_path, name_stem=name_stem
        )

        # Check if the MCP server returned an error
        if not result.get("success", True):
            return ExportResponse(
                success=False,
                message=result.get("error", "Failed to export to ANSYS format"),
                files_created=[],
                export_format="ANSYS",
                output_location=folder_path,
                file_count=0,
            )

        return ExportResponse(
            success=True,
            message="LoadSet exported to ANSYS format",
            files_created=result.get("files_created", []),
            export_format="ANSYS",
            output_location=folder_path,
            file_count=len(result.get("files_created", [])),
        )

    @agent.tool
    def compare_loadsets(ctx: RunContext[MCPServerProvider]) -> ComparisonResponse:
        """Compare two LoadSets with detailed analysis. Requires to load the two loadsets first"""
        result = ctx.deps.loads_server._tool_manager._tools["compare_loadsets"].fn()

        # Check if the MCP server returned an error
        if not result.get("success", True):
            return ComparisonResponse(
                success=False,
                message=result.get("error", "Comparison failed"),
                total_differences=0,
                points_compared=0,
                components_compared=[],
            )

        return ComparisonResponse(
            success=True,
            message="LoadSet comparison completed",
            total_differences=result.get("total_differences", 0),
            points_compared=result.get("points_compared", 0),
            components_compared=result.get("components_compared", []),
        )

    return agent


def create_python_agent() -> Agent[MCPServerProvider, str]:
    """Create a Python execution agent with dependency injection."""
    agent = Agent(
        get_model_name(),
        deps_type=MCPServerProvider,
        system_prompt="You are an expert Python programmer with access to a persistent Python execution environment. Break down complex tasks into steps and execute code incrementally.",
    )

    @agent.tool
    def execute_code(
        ctx: RunContext[MCPServerProvider], code: str
    ) -> ExecutionResponse:
        """Execute Python code in the persistent session."""
        result = ctx.deps.python_server._tool_manager._tools["execute_code"].fn(
            code=code
        )
        return ExecutionResponse(
            success=result.get("success", False),
            message="Code executed successfully"
            if result.get("success")
            else "Code execution failed",
            stdout=result.get("stdout", ""),
            stderr=result.get("stderr", ""),
            execution_time=result.get("execution_time", 0.0),
            variables_count=len(result.get("variables", {})),
        )

    @agent.tool
    def list_variables(ctx: RunContext[MCPServerProvider]) -> SessionResponse:
        """List all variables in the current session namespace."""
        result = ctx.deps.python_server._tool_manager._tools["list_variables"].fn()
        return SessionResponse(
            success=True,
            message="Variables listed successfully",
            session_state="active",
            execution_count=result.get("execution_count", 0),
        )

    @agent.tool
    def reset_session(ctx: RunContext[MCPServerProvider]) -> SessionResponse:
        """Reset the Python session, clearing all variables and history."""
        ctx.deps.python_server._tool_manager._tools["reset_session"].fn()
        return SessionResponse(
            success=True,
            message="Session reset successfully",
            session_state="reset",
            execution_count=0,
        )

    return agent


def create_script_agent() -> Agent[MCPServerProvider, str]:
    """Create a script generation and execution agent with dependency injection."""
    agent = Agent(
        get_model_name(),
        deps_type=MCPServerProvider,
        system_prompt="You are an expert Python script generator with access to script execution tools. Create complete, self-contained Python scripts with proper error handling.",
    )

    @agent.tool
    def execute_python_script(
        ctx: RunContext[MCPServerProvider],
        script_content: str,
        script_name: str = "generated_script.py",
    ) -> ScriptResponse:
        """Execute a complete Python script in isolated workspace."""
        result = ctx.deps.script_server._tool_manager._tools[
            "execute_python_script"
        ].fn(script_content=script_content, script_name=script_name)
        execution_result = result.get("execution_result", {})
        return ScriptResponse(
            success=execution_result.get("success", False),
            message="Script executed successfully"
            if execution_result.get("success")
            else "Script execution failed",
            script_hash=execution_result.get("script_hash", ""),
            output_files=execution_result.get("output_files", []),
            execution_time=execution_result.get("execution_time", 0.0),
            workspace_path=execution_result.get("workspace_path", ""),
            exit_code=execution_result.get("exit_code", None),
        )

    @agent.tool
    def download_file(
        ctx: RunContext[MCPServerProvider], file_path: str, output_format: str = "auto"
    ) -> FileOperationResponse:
        """Download files from workspace as base64 or text."""
        result = ctx.deps.script_server._tool_manager._tools["download_file"].fn(
            file_path=file_path, encoding=output_format
        )
        return FileOperationResponse(
            success=result.get("success", False),
            message="File downloaded successfully"
            if result.get("success")
            else "File download failed",
            file_path=file_path,
            file_size=result.get("size", None),
            encoding=result.get("encoding", None),
            content_preview=result.get("content", "")[:100]
            if result.get("content")
            else None,
        )

    @agent.tool
    def reset_workspace(ctx: RunContext[MCPServerProvider]) -> WorkspaceResponse:
        """Clean up execution workspace."""
        result = ctx.deps.script_server._tool_manager._tools["reset_workspace"].fn()
        return WorkspaceResponse(
            success=result.get("success", False),
            message="Workspace reset successfully"
            if result.get("success")
            else "Workspace reset failed",
            workspace_path=None,
            files_count=0,
            is_active=False,
        )

    return agent


# Export the response models for easy access
__all__ = [
    "create_loadset_agent",
    "create_python_agent",
    "create_script_agent",
    "LoadSetResponse",
    "ConversionResponse",
    "ExecutionResponse",
    "ScriptResponse",
    "ComparisonResponse",
    "ExportResponse",
    "SessionResponse",
    "FileOperationResponse",
    "WorkspaceResponse",
]
