"""
MCP (Model Context Protocol) server for trs-use-case.

This package contains the LoadSet FastMCP server for external MCP protocol access.
For direct agent usage, use LoadSetMCPProvider directly.
"""

from .loads_mcp_server import create_mcp_server as create_loads_mcp_server

__all__ = [
    "create_loads_mcp_server",
]
