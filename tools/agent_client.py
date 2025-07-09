"""
Pydantic-AI agent client for testing MCP server integration.

This module provides a simple agent client that can connect to the MCP server
and call tools to test the actual MCP protocol communication.
"""

import asyncio
from typing import Dict, Any, Optional
from fastmcp import FastMCP
from mcp_server import create_mcp_server
import json
import os


class MCPTestAgent:
    """
    A Pydantic-AI agent client for testing MCP server functionality.
    
    This agent can connect to the MCP server and call tools to test
    the actual MCP protocol communication.
    """
    
    def __init__(self, server: FastMCP):
        """Initialize the agent with an MCP server."""
        self.server = server
        self.agent = None
        
        # Only create pydantic-ai agent if API key is available
        if os.getenv("OPENAI_API_KEY"):
            try:
                from pydantic_ai import Agent
                self.agent = Agent(
                    'openai:gpt-4o-mini',
                    system_prompt="""
                    You are a test agent for the LoadSet MCP server. 
                    You have access to tools for loading, transforming, and exporting structural load data.
                    
                    Available tools:
                    - load_from_json: Load LoadSet data from JSON file
                    - convert_units: Convert units between N, kN, lbf, klbf
                    - scale_loads: Scale all loads by a factor
                    - export_to_ansys: Export to ANSYS format files
                    - get_load_summary: Get summary of current LoadSet
                    - list_load_cases: List all load cases
                    
                    Always call tools to perform the requested operations.
                    """
                )
                
                # Register MCP tools with the agent
                self._register_tools()
            except ImportError:
                self.agent = None
    
    def _register_tools(self):
        """Register MCP server tools with the Pydantic-AI agent."""
        # Get tools from the MCP server
        tools = self.server._tool_manager._tools
        
        for tool_name, tool_info in tools.items():
            # Create a wrapper function for each tool
            tool_fn = tool_info.fn
            
            # Register the tool with the agent
            self.agent.tool(tool_fn, name=tool_name)
    
    async def load_and_process_data(self, json_path: str, target_units: str, scale_factor: float) -> Dict[str, Any]:
        """
        Test workflow: Load data, convert units, and scale loads.
        
        Args:
            json_path: Path to JSON file
            target_units: Target units for conversion
            scale_factor: Factor to scale loads by
            
        Returns:
            Dict containing the results of each operation
        """
        try:
            # Use the agent to perform the workflow
            result = await self.agent.run(
                f"""
                Please perform the following operations:
                1. Load LoadSet data from: {json_path}
                2. Convert units to: {target_units}
                3. Scale loads by factor: {scale_factor}
                4. Get a summary of the final LoadSet
                
                Return the results of each operation.
                """
            )
            
            return {
                "success": True,
                "agent_response": result.data,
                "messages": [msg.content for msg in result.all_messages()]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def test_tool_call(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Test calling a specific tool through the agent.
        
        Args:
            tool_name: Name of the tool to call
            **kwargs: Tool arguments
            
        Returns:
            Dict containing the tool call result
        """
        try:
            # Create a prompt to call the specific tool
            prompt = f"Please call the {tool_name} tool with these parameters: {json.dumps(kwargs)}"
            
            result = await self.agent.run(prompt)
            
            return {
                "success": True,
                "tool_result": result.data,
                "messages": [msg.content for msg in result.all_messages()]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def call_tool_directly(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Call an MCP tool directly without the AI agent.
        
        Args:
            tool_name: Name of the tool to call
            **kwargs: Tool arguments
            
        Returns:
            Dict containing the tool result
        """
        try:
            tools = self.server._tool_manager._tools
            if tool_name not in tools:
                return {
                    "success": False,
                    "error": f"Tool '{tool_name}' not found"
                }
            
            tool_fn = tools[tool_name].fn
            result = tool_fn(**kwargs)
            
            return {
                "success": True,
                "tool_result": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_available_tools(self) -> Dict[str, Any]:
        """
        Get list of available tools from the MCP server.
        
        Returns:
            Dict containing tool information
        """
        try:
            tools = self.server._tool_manager._tools
            tool_info = {}
            
            for tool_name, tool_data in tools.items():
                tool_info[tool_name] = {
                    "name": tool_name,
                    "description": tool_data.fn.__doc__ or "No description available"
                }
            
            return {
                "success": True,
                "tools": tool_info
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


async def create_test_agent() -> MCPTestAgent:
    """
    Create a test agent connected to the MCP server.
    
    Returns:
        MCPTestAgent: Configured test agent
    """
    server = create_mcp_server()
    agent = MCPTestAgent(server)
    return agent


# Synchronous wrapper functions for testing
def run_agent_test(coro):
    """Run an async agent test synchronously."""
    return asyncio.run(coro)


def create_test_agent_sync() -> MCPTestAgent:
    """Create a test agent synchronously."""
    return run_agent_test(create_test_agent())