"""
MCP Server Bridge for pydantic-ai agents.

This module provides a clean interface for agents to interact with MCP servers,
completely independent of the LLM provider choice.
"""

from typing import Dict, Any, Optional
from functools import lru_cache


# Global MCP server registry
_mcp_servers: Dict[str, Any] = {}


def register_mcp_server(name: str, server: Any) -> None:
    """
    Register an MCP server for use by agents.
    
    Args:
        name: Server identifier (e.g., "loads", "python", "script")
        server: MCP server instance
    """
    _mcp_servers[name] = server


def get_mcp_server(name: str) -> Any:
    """
    Get a registered MCP server by name.
    
    Args:
        name: Server identifier
        
    Returns:
        MCP server instance
        
    Raises:
        KeyError: If server not found
    """
    if name not in _mcp_servers:
        raise KeyError(f"MCP server '{name}' not registered. Available: {list(_mcp_servers.keys())}")
    return _mcp_servers[name]


def call_mcp_tool(server_name: str, tool_name: str, **kwargs) -> Dict[str, Any]:
    """
    Call an MCP tool on a registered server.
    
    This is the main interface for agents to interact with MCP tools.
    It's completely provider-agnostic and works with any LLM.
    
    Args:
        server_name: Name of the MCP server
        tool_name: Name of the tool to call
        **kwargs: Tool arguments
        
    Returns:
        Tool result as dictionary
        
    Raises:
        KeyError: If server or tool not found
        Exception: If tool execution fails
    """
    try:
        server = get_mcp_server(server_name)
        tools = server._tool_manager._tools
        
        if tool_name not in tools:
            available_tools = list(tools.keys())
            raise KeyError(f"Tool '{tool_name}' not found on server '{server_name}'. Available: {available_tools}")
        
        tool_fn = tools[tool_name].fn
        result = tool_fn(**kwargs)
        
        return {"success": True, "result": result}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_available_tools(server_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get information about available tools.
    
    Args:
        server_name: Optional server name to filter tools
        
    Returns:
        Dictionary of tool information
    """
    if server_name:
        # Get tools for specific server
        try:
            server = get_mcp_server(server_name)
            tools = server._tool_manager._tools
            return {
                server_name: {
                    tool_name: {
                        "name": tool_name,
                        "description": tool_data.fn.__doc__ or "No description available",
                        "function": tool_data.fn.__name__,
                    }
                    for tool_name, tool_data in tools.items()
                }
            }
        except KeyError:
            return {}
    else:
        # Get tools for all servers
        all_tools = {}
        for name, server in _mcp_servers.items():
            tools = server._tool_manager._tools
            all_tools[name] = {
                tool_name: {
                    "name": tool_name,
                    "description": tool_data.fn.__doc__ or "No description available",
                    "function": tool_data.fn.__name__,
                }
                for tool_name, tool_data in tools.items()
            }
        return all_tools


def list_registered_servers() -> list[str]:
    """Get list of registered MCP server names."""
    return list(_mcp_servers.keys())


def is_server_registered(name: str) -> bool:
    """Check if an MCP server is registered."""
    return name in _mcp_servers


@lru_cache(maxsize=128)
def get_tool_signature(server_name: str, tool_name: str) -> Optional[str]:
    """
    Get the function signature for a tool (cached for performance).
    
    Args:
        server_name: Name of the MCP server
        tool_name: Name of the tool
        
    Returns:
        Function signature string or None if not found
    """
    try:
        server = get_mcp_server(server_name)
        tools = server._tool_manager._tools
        
        if tool_name in tools:
            tool_fn = tools[tool_name].fn
            import inspect
            return str(inspect.signature(tool_fn))
        return None
        
    except Exception:
        return None


# Convenience functions for common servers
def call_loads_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """Call a tool on the LoadSet MCP server."""
    return call_mcp_tool("loads", tool_name, **kwargs)


def call_python_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """Call a tool on the Python execution MCP server."""
    return call_mcp_tool("python", tool_name, **kwargs)


def call_script_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """Call a tool on the Script execution MCP server."""
    return call_mcp_tool("script", tool_name, **kwargs)


# Auto-setup functions for common MCP servers
def setup_default_servers() -> None:
    """
    Set up default MCP servers for common use cases.
    
    This is a convenience function that registers the standard MCP servers
    used in this project. Can be called during application startup.
    """
    try:
        # Import and register LoadSet MCP server
        from tools.mcps.loads_mcp_server import create_mcp_server, reset_global_state
        reset_global_state()
        loads_server = create_mcp_server()
        register_mcp_server("loads", loads_server)
        
        # Import and register Python execution MCP server
        from tools.mcps.python_exec_mcp_server import create_mcp_server as create_python_server
        python_server = create_python_server()
        register_mcp_server("python", python_server)
        
        # Import and register Script execution MCP server
        from tools.mcps.script_exec_mcp_server import create_mcp_server as create_script_server
        script_server = create_script_server()
        register_mcp_server("script", script_server)
        
    except ImportError as e:
        print(f"Warning: Could not set up default MCP servers: {e}")


if __name__ == "__main__":
    print("🔗 MCP Bridge Test")
    print("=" * 20)
    
    # Test setup
    setup_default_servers()
    
    print(f"Registered servers: {list_registered_servers()}")
    
    # Show available tools
    tools = get_available_tools()
    for server_name, server_tools in tools.items():
        print(f"\n📋 {server_name} server tools:")
        for tool_name, tool_info in server_tools.items():
            print(f"  - {tool_name}: {tool_info['description']}")