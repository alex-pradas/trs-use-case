"""
Simplified pydantic-ai agents following best practices.

This module implements the new simplified agent architecture using:
- MCPServerStdio for out-of-process tool execution (standard MCP pattern)
- RunContext for accessing dependencies in tools
- Structured Pydantic models for responses
- Centralized error handling via pydantic-ai
- Elimination of MCP bridge abstraction

Expected code reduction: 60% (from 400 to ~160 lines)
"""

import sys
from pathlib import Path
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio

from tools.model_config import get_model_name
from tools.model_configs import create_model_from_key, is_valid_model_key

# Path to the MCP server script
MCP_SERVER_SCRIPT = Path(__file__).parent / "mcps" / "loads_mcp_server.py"


def create_default_server() -> MCPServerStdio:
    """Create a default MCPServerStdio instance pointing to the loads MCP server."""
    return MCPServerStdio(
        str(sys.executable),
        args=[str(MCP_SERVER_SCRIPT), "stdio"],
    )


def create_loadset_agent(
    system_prompt: str | None = None,
    model_override: str | None = None,
    server: MCPServerStdio | None = None,
) -> Agent[None, str]:
    """
    Create a LoadSet processing agent using MCPServerStdio.
    
    Args:
        system_prompt: Optional custom system prompt
        model_override: Optional model name to override default
        server: Optional MCPServerStdio instance. If None, a new one is created.
               Note: If you create a new server here, you should manage its lifecycle
               (e.g. using `async with agent:` or `async with server:`).
    """
    default_prompt = "You are an expert aerospace structural loads analyst with access to LoadSet processing tools. Use available tools for operations and provide clear explanations."

    # Use model override if provided, otherwise use default
    model_name = model_override if model_override else get_model_name()
    
    # Use provided server or create a default one
    toolsets = [server] if server else [create_default_server()]
    
    agent = Agent(
        model_name,
        toolsets=toolsets,
        system_prompt=system_prompt or default_prompt,
    )

    return agent


def create_loadset_agent_with_model(
    model_key: str,
    system_prompt: str | None = None,
    server: MCPServerStdio | None = None,
) -> Agent[None, str]:
    """
    Create a LoadSet processing agent using a simple model key.
    
    Args:
        model_key: Simple string key for model (e.g., 'haiku', 'kimi', 'qwen-thinking')
        system_prompt: Optional custom system prompt
        server: Optional MCPServerStdio instance
        
    Returns:
        Configured agent with appropriate model setup
        
    Raises:
        ValueError: If model_key is not recognized
    """
    if not is_valid_model_key(model_key):
        from tools.model_configs import list_available_models
        available = list(list_available_models().keys())
        raise ValueError(f"Unknown model key: {model_key}. Available: {available}")
    
    # Create model instance based on key
    model = create_model_from_key(model_key)
    
    default_prompt = "You are an expert aerospace structural loads analyst with access to LoadSet processing tools. Use available tools for operations and provide clear explanations."
    
    # Use provided server or create a default one
    toolsets = [server] if server else [create_default_server()]
    
    agent = Agent(
        model,
        toolsets=toolsets,
        system_prompt=system_prompt or default_prompt,
    )

    return agent


__all__ = [
    "create_loadset_agent",
    "create_loadset_agent_with_model",
    "create_default_server",
]
