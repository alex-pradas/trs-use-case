"""
Dependency injection for simplified agent architecture.

This module provides typed dependencies for MCP servers, following pydantic-ai
best practices for dependency injection.
"""

from dataclasses import dataclass
from pathlib import Path
import tempfile

from tools.mcps.loads_mcp_server import create_mcp_server as create_loads_server
from tools.mcps.python_exec_mcp_server import create_mcp_server as create_python_server
from tools.mcps.script_exec_mcp_server import create_mcp_server as create_script_server


@dataclass
class MCPServerProvider:
    """
    Dependency provider for MCP servers.

    This class provides configured MCP servers as dependencies for agent tools,
    eliminating the need for the MCP bridge abstraction.
    """

    loads_timeout: int = 30
    python_timeout: int = 30
    script_timeout: int = 60
    base_workspace_dir: Path | None = None

    def __post_init__(self):
        """Initialize MCP servers after dataclass creation."""
        if self.base_workspace_dir is None:
            self.base_workspace_dir = Path(tempfile.gettempdir())

        # Create MCP servers with configuration
        self._loads_server = create_loads_server()
        self._python_server = create_python_server()
        self._script_server = create_script_server(
            base_workspace_dir=self.base_workspace_dir,
            execution_timeout=self.script_timeout,
        )

    @property
    def loads_server(self):
        """Get the LoadSet MCP server."""
        return self._loads_server

    @property
    def python_server(self):
        """Get the Python execution MCP server."""
        return self._python_server

    @property
    def script_server(self):
        """Get the Script execution MCP server."""
        return self._script_server

    def get_server(self, server_type: str):
        """
        Get a specific server by type.

        Args:
            server_type: One of 'loads', 'python', 'script'

        Returns:
            The requested MCP server

        Raises:
            ValueError: If server_type is not recognized
        """
        if server_type == "loads":
            return self.loads_server
        elif server_type == "python":
            return self.python_server
        elif server_type == "script":
            return self.script_server
        else:
            raise ValueError(f"Unknown server type: {server_type}")


# Global default provider instance
_default_provider: MCPServerProvider | None = None


def get_default_mcp_provider() -> MCPServerProvider:
    """
    Get the default MCP server provider.

    Creates a default provider if none exists.

    Returns:
        The default MCPServerProvider instance
    """
    global _default_provider
    if _default_provider is None:
        _default_provider = MCPServerProvider()
    return _default_provider


def set_default_mcp_provider(provider: MCPServerProvider) -> None:
    """
    Set a custom default MCP server provider.

    Args:
        provider: The MCPServerProvider to use as default
    """
    global _default_provider
    _default_provider = provider
