"""
Pydantic response models for simplified agent architecture.

These models provide type-safe, structured responses from agent tools,
replacing raw dictionary returns with validated data structures.
"""

from typing import Any
from pydantic import BaseModel, Field


class LoadSetResponse(BaseModel):
    """Response model for LoadSet operations."""

    success: bool = Field(description="Whether the operation succeeded")
    message: str = Field(description="Human-readable status message")
    data: dict[str, Any] | None = Field(default=None, description="LoadSet data")
    load_cases_count: int | None = Field(
        default=None, description="Number of load cases"
    )
    units: dict[str, str] | None = Field(default=None, description="Current units")


class ConversionResponse(BaseModel):
    """Response model for unit conversion operations."""

    success: bool = Field(description="Whether the conversion succeeded")
    message: str = Field(description="Human-readable status message")
    original_units: dict[str, str] = Field(description="Original units")
    target_units: dict[str, str] = Field(description="Target units after conversion")
    conversion_factor: float = Field(description="Conversion factor applied")
    affected_components: list[str] | None = Field(
        default=None, description="Components that were converted"
    )


class ExecutionResponse(BaseModel):
    """Response model for Python code execution."""

    success: bool = Field(description="Whether the execution succeeded")
    message: str = Field(description="Human-readable status message")
    stdout: str = Field(default="", description="Standard output from execution")
    stderr: str = Field(default="", description="Standard error from execution")
    execution_time: float = Field(description="Execution time in seconds")
    variables_count: int | None = Field(
        default=None, description="Number of variables in session"
    )
    return_value: Any | None = Field(
        default=None, description="Return value from execution"
    )


class ScriptResponse(BaseModel):
    """Response model for script execution operations."""

    success: bool = Field(description="Whether the script execution succeeded")
    message: str = Field(description="Human-readable status message")
    script_hash: str = Field(description="Unique hash identifying the script")
    output_files: list[str] = Field(
        default_factory=list, description="Files created during execution"
    )
    execution_time: float = Field(description="Script execution time in seconds")
    workspace_path: str = Field(description="Path to the execution workspace")
    exit_code: int | None = Field(default=None, description="Script exit code")


class ComparisonResponse(BaseModel):
    """Response model for LoadSet comparison operations."""

    success: bool = Field(description="Whether the comparison succeeded")
    message: str = Field(description="Human-readable status message")
    total_differences: int = Field(description="Total number of differences found")
    points_compared: int = Field(description="Number of points compared")
    components_compared: list[str] = Field(
        description="Force/moment components compared"
    )
    max_difference_percent: float | None = Field(
        default=None, description="Maximum percentage difference"
    )
    summary_stats: dict[str, Any] | None = Field(
        default=None, description="Summary statistics"
    )


class ExportResponse(BaseModel):
    """Response model for data export operations."""

    success: bool = Field(description="Whether the export succeeded")
    message: str = Field(description="Human-readable status message")
    files_created: list[str] = Field(
        default_factory=list, description="Files that were created"
    )
    export_format: str = Field(description="Export format used (e.g., 'ANSYS', 'JSON')")
    output_location: str = Field(description="Location where files were exported")
    file_count: int = Field(description="Number of files created")


class VariableInfo(BaseModel):
    """Response model for variable information."""

    name: str = Field(description="Variable name")
    type_name: str = Field(description="Variable type")
    value_preview: str = Field(description="String preview of the value")
    size_info: str | None = Field(
        default=None, description="Size information if applicable"
    )
    is_callable: bool = Field(description="Whether the variable is callable")


class SessionResponse(BaseModel):
    """Response model for session management operations."""

    success: bool = Field(description="Whether the session operation succeeded")
    message: str = Field(description="Human-readable status message")
    variables: list[VariableInfo] | None = Field(
        default=None, description="Variables in session"
    )
    session_state: str = Field(description="Current session state")
    execution_count: int = Field(description="Number of executions in this session")


class FileOperationResponse(BaseModel):
    """Response model for file operations."""

    success: bool = Field(description="Whether the file operation succeeded")
    message: str = Field(description="Human-readable status message")
    file_path: str = Field(description="Path to the file")
    file_size: int | None = Field(default=None, description="File size in bytes")
    encoding: str | None = Field(default=None, description="File encoding used")
    content_preview: str | None = Field(
        default=None, description="Preview of file content"
    )


class WorkspaceResponse(BaseModel):
    """Response model for workspace operations."""

    success: bool = Field(description="Whether the workspace operation succeeded")
    message: str = Field(description="Human-readable status message")
    workspace_path: str | None = Field(
        default=None, description="Current workspace path"
    )
    files_count: int = Field(description="Number of files in workspace")
    total_size: int | None = Field(
        default=None, description="Total size of workspace in bytes"
    )
    is_active: bool = Field(description="Whether workspace is currently active")
