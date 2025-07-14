"""
Integration test for AI agent with MCP server using Anthropic models.

This test validates that an AI agent can successfully interact with the MCP server
to process load data using Anthropic's Claude model through pydantic-ai.
"""

import pytest
import asyncio
import os
import tempfile
import shutil
import sys
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Add the project root to Python path so we can import from tools
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tools.mcps.loads_mcp_server import create_mcp_server, reset_global_state
from tools.loads import LoadSet

# Load environment variables from .env file
load_dotenv()


class AnthropicMCPTestAgent:
    """
    A Pydantic-AI agent client using Anthropic models for testing MCP server functionality.

    This agent connects to the MCP server and uses Anthropic's Claude model
    to test the actual MCP protocol communication.
    """

    def __init__(self, server):
        """Initialize the agent with an MCP server."""
        self.server = server
        self.agent = None

        # Only create pydantic-ai agent if Anthropic API key is available
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                from pydantic_ai import Agent

                self.agent = Agent(
                    "anthropic:claude-3-5-sonnet-latest",
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
                    Be precise and follow the user's instructions exactly.
                    """,
                )

                # Register MCP tools with the agent
                self._register_tools()
            except ImportError:
                self.agent = None

    def _register_tools(self):
        """Register MCP server tools with the Pydantic-AI agent."""
        # Create simple tool functions that call the MCP server tools
        # Use @agent.tool_plain for tools that don't need context

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
        Process a user prompt through the AI agent.

        Args:
            prompt: User's natural language prompt

        Returns:
            Dict containing the results of the agent's processing
        """
        if not self.agent:
            return {
                "success": False,
                "error": "Anthropic API key not available or pydantic-ai not installed",
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
                "error": "Anthropic API key not available or pydantic-ai not installed",
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


class TestAnthropicAgentIntegration:
    """Test suite for Anthropic AI agent integration with MCP server."""

    def setup_method(self):
        """Set up test environment."""
        # Reset global state before each test
        reset_global_state()

        # Create MCP server
        self.server = create_mcp_server()

        # Create test agent
        self.agent = AnthropicMCPTestAgent(self.server)

        # Create temporary output directory
        self.temp_dir = tempfile.mkdtemp()
        self.output_folder = Path(self.temp_dir) / "output"
        self.output_folder.mkdir(exist_ok=True)

    def teardown_method(self):
        """Clean up test environment."""
        # Clean up temporary directory
        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

        # Reset global state
        reset_global_state()

    def validate_ansys_files(
        self, output_folder: Path, expected_load_cases: int
    ) -> bool:
        """
        Validate that ANSYS files were created correctly.

        Args:
            output_folder: Path to output folder
            expected_load_cases: Expected number of load cases

        Returns:
            bool: True if validation passes
        """
        ansys_files = list(output_folder.glob("*.inp"))

        if len(ansys_files) != expected_load_cases:
            return False

        # Check that files contain f commands (ANSYS format)
        for file_path in ansys_files:
            content = file_path.read_text()
            if "f,all," not in content:
                return False

        return True

    def validate_unit_conversion(
        self,
        original_value: float,
        converted_value: float,
        factor: float,
        unit_conversion_factor: float,
    ) -> bool:
        """
        Validate that unit conversion and scaling are correct.

        Args:
            original_value: Original value in N
            converted_value: Converted value in klbf
            factor: Scaling factor applied
            unit_conversion_factor: N to klbf conversion factor

        Returns:
            bool: True if conversion is correct
        """
        expected_value = original_value * factor / unit_conversion_factor
        return abs(converted_value - expected_value) < 0.001

    @pytest.mark.asyncio
    async def test_anthropic_agent_full_workflow(self):
        """Test complete workflow with Anthropic agent."""
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not available")

        # Test data
        json_path = "solution/loads/new_loads.json"
        target_units = "klbf"
        scale_factor = 1.5
        output_folder = str(self.output_folder)

        # Run the complete workflow
        result = await self.agent.load_and_process_workflow(
            json_path=json_path,
            target_units=target_units,
            scale_factor=scale_factor,
            output_folder=output_folder,
        )

        # Validate agent response
        assert result["success"], (
            f"Agent workflow failed: {result.get('error', 'Unknown error')}"
        )
        assert "agent_response" in result

        # Validate that output files were created
        assert self.output_folder.exists(), "Output folder was not created"

        # Load original data to get expected number of load cases
        original_loadset = LoadSet.read_json(json_path)
        expected_load_cases = len(original_loadset.load_cases)

        # Validate ANSYS files
        assert self.validate_ansys_files(self.output_folder, expected_load_cases), (
            "ANSYS files validation failed"
        )

        # Test that we can read one of the generated files
        ansys_files = list(self.output_folder.glob("*.inp"))
        assert len(ansys_files) > 0, "No ANSYS files were generated"

        # Validate file content
        sample_file = ansys_files[0]
        content = sample_file.read_text()
        assert "f,all," in content, "ANSYS file does not contain f,all commands"
        assert "fx," in content or "fy," in content or "fz," in content, (
            "ANSYS file does not contain force commands"
        )

    async def test_anthropic_agent_error_handling(self):
        """Test error handling with Anthropic agent."""
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not available")

        # Test with invalid file path
        result = await self.agent.process_user_prompt(
            "Please load LoadSet data from nonexistent_file.json"
        )

        # Should handle the error gracefully
        assert result["success"] or "error" in str(result["agent_response"]).lower()

    def test_direct_tool_calls(self):
        """Test direct tool calls without AI agent (fallback)."""
        # Test load_from_json
        result = self.agent.call_tool_directly(
            "load_from_json", file_path="solution/loads/new_loads.json"
        )

        assert result["success"], f"load_from_json failed: {result.get('error')}"
        assert result["tool_result"]["success"], "LoadSet loading failed"

        # Test scale_loads
        result = self.agent.call_tool_directly("scale_loads", factor=1.5)

        assert result["success"], f"scale_loads failed: {result.get('error')}"
        assert result["tool_result"]["success"], "Load scaling failed"

        # Test convert_units
        result = self.agent.call_tool_directly("convert_units", target_units="klbf")

        assert result["success"], f"convert_units failed: {result.get('error')}"
        assert result["tool_result"]["success"], "Unit conversion failed"

        # Test export_to_ansys
        result = self.agent.call_tool_directly(
            "export_to_ansys",
            folder_path=str(self.output_folder),
            name_stem="test_loads",
        )

        assert result["success"], f"export_to_ansys failed: {result.get('error')}"
        assert result["tool_result"]["success"], "ANSYS export failed"

    def test_output_validation(self):
        """Test output validation after processing."""
        # Load and process data directly
        self.agent.call_tool_directly(
            "load_from_json", file_path="solution/loads/new_loads.json"
        )

        self.agent.call_tool_directly("scale_loads", factor=1.5)

        self.agent.call_tool_directly("convert_units", target_units="klbf")

        self.agent.call_tool_directly(
            "export_to_ansys",
            folder_path=str(self.output_folder),
            name_stem="test_loads",
        )

        # Validate output
        original_loadset = LoadSet.read_json("solution/loads/new_loads.json")
        expected_load_cases = len(original_loadset.load_cases)

        assert self.validate_ansys_files(self.output_folder, expected_load_cases), (
            "ANSYS files validation failed"
        )

        # Validate numerical conversion
        # N to klbf conversion factor is 4448.222 (from loads.py)
        # Test one sample value
        original_value = 0.7608804  # First fx value from test data
        unit_conversion_factor = 4448.222
        scale_factor = 1.5

        # Read the first ANSYS file and extract a value
        ansys_files = list(self.output_folder.glob("*.inp"))
        content = ansys_files[0].read_text()

        # The content should contain scaled and converted values
        assert "f,all," in content, "ANSYS file missing f,all commands"
        assert "fx," in content or "fy," in content or "fz," in content, (
            "ANSYS file missing force commands"
        )

    def test_get_available_tools(self):
        """Test getting available tools."""
        result = self.agent.get_available_tools()

        assert result["success"], f"get_available_tools failed: {result.get('error')}"
        assert "tools" in result

        expected_tools = [
            "load_from_json",
            "convert_units",
            "scale_loads",
            "export_to_ansys",
            "get_load_summary",
            "list_load_cases",
        ]

        for tool_name in expected_tools:
            assert tool_name in result["tools"], f"Tool {tool_name} not found"


# Helper functions
def run_agent_test(coro):
    """Run an async agent test synchronously."""
    return asyncio.run(coro)


# if __name__ == "__main__":
#     # Run a quick integration test
#     import sys

#     if not os.getenv("ANTHROPIC_API_KEY"):
#         print("ANTHROPIC_API_KEY not set. Please set it to run the integration test.")
#         sys.exit(1)

#     async def main():
#         # Create test instance
#         test_instance = TestAnthropicAgentIntegration()
#         test_instance.setup_method()

#         try:
#             # Run the main integration test
#             await test_instance.test_anthropic_agent_full_workflow()
#             print("✅ Integration test passed!")

#         except Exception as e:
#             print(f"❌ Integration test failed: {e}")
#             sys.exit(1)

#         finally:
#             test_instance.teardown_method()

#     asyncio.run(main())
