"""
Integration test for AI agent with MCP server using clean architecture.

This test validates that the clean pydantic-ai agents can successfully interact 
with the MCP server to process load data using any configured AI model.
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

# Add tools directory for clean architecture
tools_path = project_root / "tools"
if str(tools_path) not in sys.path:
    sys.path.insert(0, str(tools_path))

from tools.agents import loadset_agent, python_agent, script_agent
from tools.model_config import get_model_name, validate_model_config
from tools.mcps.loads_mcp_server import reset_global_state
from tools.loads import LoadSet

# Load environment variables from .env file
load_dotenv()


# No more boilerplate agent classes needed with clean architecture!


@pytest.mark.expensive
class TestCleanAgentIntegration:
    """Test suite for clean AI agent integration with MCP server."""

    def setup_method(self):
        """Set up test environment."""
        # Reset global state before each test
        reset_global_state()

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
    async def test_clean_agent_full_workflow(self):
        """Test complete workflow with clean agent architecture."""
        # Validate configuration
        is_valid, error = validate_model_config()
        if not is_valid:
            pytest.skip(f"Model configuration error: {error}")

        # Test data
        json_path = "solution/loads/new_loads.json"
        target_units = "klbf"
        scale_factor = 1.5
        output_folder = str(self.output_folder)

        # Run the complete workflow using clean architecture
        result = await loadset_agent.run(f"""
        Please help me process the loads in {json_path}. 
        Factor by {scale_factor} and convert to {target_units}. 
        Generate files for ansys in a subfolder called {output_folder}.
        
        Please perform these steps:
        1. Load LoadSet data from: {json_path}
        2. Scale loads by factor: {scale_factor}
        3. Convert units to: {target_units}
        4. Export to ANSYS format in folder: {output_folder} with name_stem: "processed_loads"
        5. Get a summary of the final LoadSet
        
        Return the results of each operation.
        """)

        # Validate agent response
        assert result.output, "Agent should return a response"
        assert "LoadSet" in result.output, "Response should mention LoadSet"

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

    @pytest.mark.asyncio
    async def test_clean_agent_error_handling(self):
        """Test error handling with clean agent architecture."""
        # Validate configuration
        is_valid, error = validate_model_config()
        if not is_valid:
            pytest.skip(f"Model configuration error: {error}")

        # Test with invalid file path
        result = await loadset_agent.run(
            "Please load LoadSet data from nonexistent_file.json"
        )

        # Should handle the error gracefully
        assert result.output, "Agent should return a response even for errors"

    def test_direct_tool_access(self):
        """Test that clean agents have properly registered tools."""
        # Check that agents have tools registered
        assert hasattr(loadset_agent, '_tools'), "LoadSet agent should have tools"
        assert hasattr(python_agent, '_tools'), "Python agent should have tools"
        assert hasattr(script_agent, '_tools'), "Script agent should have tools"

        # Check specific tools exist
        loadset_tool_names = [tool.function.__name__ for tool in loadset_agent._tools.values()]
        assert "load_from_json" in loadset_tool_names, "LoadSet agent should have load_from_json tool"
        assert "convert_units" in loadset_tool_names, "LoadSet agent should have convert_units tool"

        python_tool_names = [tool.function.__name__ for tool in python_agent._tools.values()]
        assert "execute_code" in python_tool_names, "Python agent should have execute_code tool"

        script_tool_names = [tool.function.__name__ for tool in script_agent._tools.values()]
        assert "execute_python_script" in script_tool_names, "Script agent should have execute_python_script tool"

    @pytest.mark.asyncio
    async def test_clean_agent_model_switching(self):
        """Test that clean agent works with different model configurations."""
        # Validate configuration
        is_valid, error = validate_model_config()
        if not is_valid:
            pytest.skip(f"Model configuration error: {error}")

        current_model = get_model_name()
        
        # Test basic functionality with current model
        result = await loadset_agent.run(
            "Load 'solution/loads/new_loads.json' and tell me how many load cases it contains."
        )

        assert result.output, "Agent should work with current model"
        assert "25" in result.output or "load cases" in result.output.lower(), "Should report load case count"


# Helper functions
def run_agent_test(coro):
    """Run an async agent test synchronously."""
    return asyncio.run(coro)


if __name__ == "__main__":
    # Run a quick integration test with clean architecture
    import sys

    async def main():
        """Quick test of clean agent architecture."""
        print("🧪 Clean Agent Integration Test")
        print("=" * 40)
        
        # Validate configuration
        is_valid, error = validate_model_config()
        if not is_valid:
            print(f"❌ Configuration error: {error}")
            sys.exit(1)

        print(f"✅ Using model: {get_model_name()}")
        
        try:
            # Test basic LoadSet agent functionality
            result = await loadset_agent.run(
                "Load 'solution/loads/new_loads.json' and give me a quick summary."
            )
            print(f"✅ LoadSet agent test passed: {len(result.output)} character response")
            
            # Test Python agent functionality
            result = await python_agent.run(
                "Execute: print('Hello from clean architecture!')"
            )
            print(f"✅ Python agent test passed: {len(result.output)} character response")
            
            print("🎉 Clean architecture integration test passed!")
            
        except Exception as e:
            print(f"❌ Integration test failed: {e}")
            sys.exit(1)

    asyncio.run(main())
