"""
FIREWORKS AI agent for MCP server integration.

This module provides agent classes that use FIREWORKS AI models
to interact with MCP servers, offering an alternative to Anthropic agents.
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from pydantic_ai import Agent

from fireworks_client import create_fireworks_agent, FireworksConfig

# Load environment variables
load_dotenv()


class FireworksMCPAgent:
    """
    A Pydantic-AI agent client using FIREWORKS models for MCP server interaction.

    This agent connects to MCP servers and uses FIREWORKS AI models
    as an alternative to Anthropic Claude models.
    """

    def __init__(self, server, model_name: str = FireworksConfig.DEFAULT_CODE_MODEL):
        """Initialize the agent with an MCP server and FIREWORKS model."""
        self.server = server
        self.model_name = model_name
        self.agent = None

        # Check if FIREWORKS API key is available
        if FireworksConfig.is_configured():
            try:
                self.agent = create_fireworks_agent(
                    system_prompt="""
                    You are a test agent for the LoadSet MCP server using FIREWORKS AI. 
                    You have access to tools for loading, transforming, and exporting structural load data.
                    
                    Available tools:
                    - load_from_json: Load LoadSet data from JSON file
                    - convert_units: Convert units between N, kN, lbf, klbf
                    - scale_loads: Scale all loads by a factor
                    - export_to_ansys: Export to ANSYS format files
                    - get_load_summary: Get summary of current LoadSet
                    - list_load_cases: List all load cases
                    
                    Always call tools to perform the requested operations.
                    Be precise and follow the user's instructions exactly.
                    Focus on providing clear, concise responses about the operations performed.
                    """,
                    model_name=model_name,
                )

                # Register MCP tools with the agent
                self._register_tools()

            except Exception as e:
                print(f"Failed to create FIREWORKS agent: {e}")
                self.agent = None

    def _register_tools(self):
        """Register MCP server tools with the Pydantic-AI agent."""

        @self.agent.tool_plain
        def load_from_json(file_path: str) -> dict:
            """Load a LoadSet from a JSON file."""
            return self.call_tool_directly("load_from_json", file_path=file_path)[
                "tool_result"
            ]

        @self.agent.tool_plain
        def convert_units(target_units: str) -> dict:
            """Convert the current LoadSet to different units."""
            return self.call_tool_directly("convert_units", target_units=target_units)[
                "tool_result"
            ]

        @self.agent.tool_plain
        def scale_loads(factor: float) -> dict:
            """Scale all loads in the current LoadSet by a factor."""
            return self.call_tool_directly("scale_loads", factor=factor)["tool_result"]

        @self.agent.tool_plain
        def export_to_ansys(folder_path: str, name_stem: str) -> dict:
            """Export the current LoadSet to ANSYS format files."""
            return self.call_tool_directly(
                "export_to_ansys", folder_path=folder_path, name_stem=name_stem
            )["tool_result"]

        @self.agent.tool_plain
        def get_load_summary() -> dict:
            """Get summary information about the current LoadSet."""
            return self.call_tool_directly("get_load_summary")["tool_result"]

        @self.agent.tool_plain
        def list_load_cases() -> dict:
            """List all load cases in the current LoadSet."""
            return self.call_tool_directly("list_load_cases")["tool_result"]

    async def process_user_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Process a user prompt through the FIREWORKS AI agent.

        Args:
            prompt: User's natural language prompt

        Returns:
            Dict containing the results of the agent's processing
        """
        if not self.agent:
            return {
                "success": False,
                "error": "FIREWORKS API key not available or agent creation failed",
            }

        try:
            result = await self.agent.run(prompt)

            return {
                "success": True,
                "agent_response": result.output,
                "messages": [str(msg) for msg in result.all_messages()],
                "tool_calls": [
                    msg for msg in result.all_messages() if hasattr(msg, "tool_calls")
                ],
                "model_used": self.model_name,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def load_and_process_workflow(
        self, json_path: str, target_units: str, scale_factor: float, output_folder: str
    ) -> Dict[str, Any]:
        """
        Test complete workflow: Load data, scale, convert units, and export.

        Args:
            json_path: Path to JSON file
            target_units: Target units for conversion
            scale_factor: Factor to scale loads by
            output_folder: Folder to export ANSYS files

        Returns:
            Dict containing the results of each operation
        """
        if not self.agent:
            return {
                "success": False,
                "error": "FIREWORKS API key not available or agent creation failed",
            }

        try:
            # Use the agent to perform the complete workflow
            result = await self.agent.run(
                f"""
                Please help me process the loads in {json_path}. 
                Factor by {scale_factor} and convert to {target_units}. 
                Generate files for ansys in a subfolder called {output_folder}.
                
                Please perform these steps:
                1. Load LoadSet data from: {json_path}
                2. Scale loads by factor: {scale_factor}
                3. Convert units to: {target_units}
                4. Export to ANSYS format in folder: {output_folder} with name_stem: "processed_loads"
                5. Get a summary of the final LoadSet
                
                For step 4, use export_to_ansys with folder_path="{output_folder}" and name_stem="processed_loads"
                
                Return the results of each operation.
                """
            )

            return {
                "success": True,
                "agent_response": result.output,
                "messages": [str(msg) for msg in result.all_messages()],
                "tool_calls": [
                    msg for msg in result.all_messages() if hasattr(msg, "tool_calls")
                ],
                "model_used": self.model_name,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

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
                return {"success": False, "error": f"Tool '{tool_name}' not found"}

            tool_fn = tools[tool_name].fn
            result = tool_fn(**kwargs)

            return {"success": True, "tool_result": result}

        except Exception as e:
            return {"success": False, "error": str(e)}

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
                    "description": tool_data.fn.__doc__ or "No description available",
                }

            return {"success": True, "tools": tool_info}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def is_configured(self) -> bool:
        """Check if the agent is properly configured."""
        return self.agent is not None


class FireworksPythonExecutionAgent:
    """
    FIREWORKS AI agent for Python execution MCP server interaction.

    This agent connects to the Python execution MCP server and uses FIREWORKS AI
    to generate and execute Python code autonomously.
    """

    def __init__(self, server, model_name: str = FireworksConfig.DEFAULT_CODE_MODEL):
        """Initialize the agent with a Python execution MCP server."""
        self.server = server
        self.model_name = model_name
        self.agent = None

        # Only create pydantic-ai agent if FIREWORKS API key is available
        if FireworksConfig.is_configured():
            try:
                self.agent = create_fireworks_agent(
                    system_prompt="""
                    You are a Python programming assistant using FIREWORKS AI with access to a persistent Python execution environment.
                    
                    Available tools for Python code execution:
                    - execute_code: Execute Python code in a persistent session
                    - list_variables: List all variables in the current session
                    - get_variable: Get detailed information about a specific variable
                    - reset_session: Clear all variables and start fresh
                    - install_package: Install Python packages using uv
                    - get_execution_history: View recent code executions
                    - configure_security: Adjust security settings
                    
                    Key capabilities:
                    - Variables persist across multiple code executions
                    - You can build on previous code executions
                    - LoadSet, numpy, and matplotlib are pre-imported
                    - Generate and execute code to solve problems step by step
                    
                    IMPORTANT LoadSet API reference:
                    - LoadSet.read_json(file_path) - Load from JSON file (NOT from_json)
                    - loadset.convert_to(target_units) - Convert units ("N", "kN", "lbf", "klbf")
                    - loadset.factor(scale_factor) - Scale all loads by factor
                    - loadset.compare_to(other_loadset) - Compare two LoadSets
                    - Use Path() for file paths when needed for JSON writing
                    
                    When asked to solve problems:
                    1. Break down the problem into steps
                    2. Write and execute code incrementally
                    3. Check results and build on them
                    4. Use variables to store intermediate results
                    
                    Always execute the code you write to demonstrate the solution.
                    """,
                    model_name=model_name,
                )

                # Register MCP tools with the agent
                self._register_tools()

            except Exception as e:
                print(f"Failed to create FIREWORKS Python execution agent: {e}")
                self.agent = None

    def _register_tools(self):
        """Register MCP server tools with the Pydantic-AI agent."""

        @self.agent.tool_plain
        def execute_code(code: str) -> dict:
            """Execute Python code in the persistent session."""
            return self.call_tool_directly("execute_code", code=code)["tool_result"]

        @self.agent.tool_plain
        def list_variables() -> dict:
            """List all variables in the current session namespace."""
            return self.call_tool_directly("list_variables")["tool_result"]

        @self.agent.tool_plain
        def get_variable(name: str) -> dict:
            """Get detailed information about a specific variable."""
            return self.call_tool_directly("get_variable", name=name)["tool_result"]

        @self.agent.tool_plain
        def reset_session() -> dict:
            """Reset the Python session, clearing all variables and history."""
            return self.call_tool_directly("reset_session")["tool_result"]

        @self.agent.tool_plain
        def install_package(package_name: str, dev: bool = False) -> dict:
            """Install a Python package using uv."""
            return self.call_tool_directly(
                "install_package", package_name=package_name, dev=dev
            )["tool_result"]

        @self.agent.tool_plain
        def get_execution_history(limit: int = 10) -> dict:
            """Get recent execution history."""
            return self.call_tool_directly("get_execution_history", limit=limit)[
                "tool_result"
            ]

        @self.agent.tool_plain
        def configure_security(
            enable_security: bool = True, execution_timeout: int = 30
        ) -> dict:
            """Configure security settings for code execution."""
            return self.call_tool_directly(
                "configure_security",
                enable_security=enable_security,
                execution_timeout=execution_timeout,
            )["tool_result"]

    async def solve_programming_challenge(self, challenge: str) -> Dict[str, Any]:
        """
        Ask the agent to solve a programming challenge using the execution environment.

        Args:
            challenge: Programming challenge description

        Returns:
            Dict containing the agent's response and execution results
        """
        if not self.agent:
            return {
                "success": False,
                "error": "FIREWORKS API key not available or agent creation failed",
            }

        try:
            result = await self.agent.run(challenge)

            # Count tool calls from messages
            tool_calls_count = 0
            for msg in result.all_messages():
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    tool_calls_count += len(msg.tool_calls)
                elif "tool:" in str(msg) or "execute_code" in str(msg):
                    tool_calls_count += 1

            return {
                "success": True,
                "agent_response": result.output,
                "messages": [str(msg) for msg in result.all_messages()],
                "tool_calls_count": tool_calls_count,
                "model_used": self.model_name,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

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
                return {"success": False, "error": f"Tool '{tool_name}' not found"}

            tool_fn = tools[tool_name].fn
            result = tool_fn(**kwargs)

            return {"success": True, "tool_result": result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def is_configured(self) -> bool:
        """Check if the agent is properly configured."""
        return self.agent is not None


if __name__ == "__main__":
    # Quick test of FIREWORKS MCP agent
    print("🔥 FIREWORKS MCP Agent Test")
    print("=" * 40)

    if FireworksConfig.is_configured():
        print("✅ FIREWORKS_API_KEY found")
        print(f"🎯 Default model: {FireworksConfig.DEFAULT_CODE_MODEL}")
        print("✅ FIREWORKS MCP Agent classes ready for use")
    else:
        print("❌ FIREWORKS_API_KEY not found in environment")
        print("   Please add FIREWORKS_API_KEY to your .env file")
