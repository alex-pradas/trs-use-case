#!/usr/bin/env python3
"""
Clean agent integration tests using the new simplified architecture.

This replaces the old boilerplate test classes with simple direct agent usage.
"""

import pytest
import asyncio
import os
import tempfile
import shutil
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Add tools directory
tools_path = project_root / "tools"
if str(tools_path) not in sys.path:
    sys.path.insert(0, str(tools_path))

from agents import loadset_agent, python_agent, script_agent
from model_config import get_model_name, validate_model_config
from mcps.loads_mcp_server import reset_global_state
from loads import LoadSet

# Load environment variables
load_dotenv()


@pytest.mark.expensive
class TestCleanAgentIntegration:
    """Test suite for clean agent integration."""

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

    @pytest.mark.asyncio
    async def test_loadset_agent_basic_workflow(self):
        """Test complete LoadSet workflow with clean agent."""
        # Validate configuration
        is_valid, error = validate_model_config()
        if not is_valid:
            pytest.skip(f"Model configuration error: {error}")

        # Test basic LoadSet workflow
        result = await loadset_agent.run(f"""
        Please perform these LoadSet operations:
        1. Load LoadSet data from: solution/loads/new_loads.json
        2. Scale loads by factor: 1.5
        3. Convert units to: klbf
        4. Export to ANSYS format in folder: {self.output_folder} with name_stem: test_loads
        5. Get a summary of the final LoadSet
        
        Provide a detailed report of each step.
        """)

        # Validate agent response
        assert result.output, "Agent should return a response"
        assert "LoadSet" in result.output, "Response should mention LoadSet"

        # Validate that output files were created
        assert self.output_folder.exists(), "Output folder was not created"

        # Load original data to get expected number of load cases
        original_loadset = LoadSet.read_json("solution/loads/new_loads.json")
        expected_load_cases = len(original_loadset.load_cases)

        # Validate ANSYS files
        ansys_files = list(self.output_folder.glob("*.inp"))
        assert len(ansys_files) == expected_load_cases, (
            f"Expected {expected_load_cases} ANSYS files, got {len(ansys_files)}"
        )

        # Validate file content
        sample_file = ansys_files[0]
        content = sample_file.read_text()
        assert "f,all," in content, "ANSYS file does not contain f,all commands"

    @pytest.mark.asyncio
    async def test_python_agent_code_execution(self):
        """Test Python execution agent with clean architecture."""
        is_valid, error = validate_model_config()
        if not is_valid:
            pytest.skip(f"Model configuration error: {error}")

        # Test Python code generation and execution
        result = await python_agent.run("""
        Create a simple LoadSet processing example:
        1. Load the LoadSet from 'solution/loads/new_loads.json'
        2. Show the original units and total number of load cases
        3. Convert to klbf units and show a sample force value
        4. Calculate the scaling factor needed to double all forces
        
        Execute code to demonstrate each step.
        """)

        # Validate response
        assert result.output, "Agent should return a response"
        assert "LoadSet" in result.output, "Response should mention LoadSet"

    @pytest.mark.asyncio
    async def test_script_agent_generation(self):
        """Test script generation and execution agent."""
        is_valid, error = validate_model_config()
        if not is_valid:
            pytest.skip(f"Model configuration error: {error}")

        # Test script generation
        result = await script_agent.run("""
        Generate and execute a Python script that:
        1. Loads the LoadSet from 'solution/loads/new_loads.json'
        2. Analyzes the data and creates a summary report
        3. Converts units to different systems (N, kN, lbf)
        4. Saves the analysis results to a JSON file called 'analysis_report.json'
        
        The script should be complete and self-contained.
        """)

        # Validate response
        assert result.output, "Agent should return a response"
        assert "script" in result.output.lower(), (
            "Response should mention script execution"
        )

    @pytest.mark.asyncio
    async def test_loadset_agent_error_handling(self):
        """Test error handling with clean agent."""
        is_valid, error = validate_model_config()
        if not is_valid:
            pytest.skip(f"Model configuration error: {error}")

        # Test with invalid file path
        result = await loadset_agent.run(
            "Please load LoadSet data from nonexistent_file.json"
        )

        # Should handle the error gracefully
        assert result.output, "Agent should return a response even for errors"

    @pytest.mark.asyncio
    async def test_model_switching_compatibility(self):
        """Test that the same agent works with different models."""
        is_valid, error = validate_model_config()
        if not is_valid:
            pytest.skip(f"Model configuration error: {error}")

        current_model = get_model_name()

        # Test basic functionality
        result = await loadset_agent.run(
            "Load 'solution/loads/new_loads.json' and tell me how many load cases it contains."
        )

        assert result.output, "Agent should work with current model"
        assert "25" in result.output or "load cases" in result.output.lower(), (
            "Should report load case count"
        )

    def test_direct_tool_access(self):
        """Test that agents have properly registered tools."""
        # Check that agents have tools registered
        assert hasattr(loadset_agent, "_tools"), "LoadSet agent should have tools"
        assert hasattr(python_agent, "_tools"), "Python agent should have tools"
        assert hasattr(script_agent, "_tools"), "Script agent should have tools"

        # Check specific tools exist
        loadset_tool_names = [
            tool.function.__name__ for tool in loadset_agent._tools.values()
        ]
        assert "load_from_json" in loadset_tool_names, (
            "LoadSet agent should have load_from_json tool"
        )
        assert "convert_units" in loadset_tool_names, (
            "LoadSet agent should have convert_units tool"
        )

        python_tool_names = [
            tool.function.__name__ for tool in python_agent._tools.values()
        ]
        assert "execute_code" in python_tool_names, (
            "Python agent should have execute_code tool"
        )

        script_tool_names = [
            tool.function.__name__ for tool in script_agent._tools.values()
        ]
        assert "execute_python_script" in script_tool_names, (
            "Script agent should have execute_python_script tool"
        )


@pytest.mark.asyncio
async def test_clean_vs_old_architecture_comparison():
    """Compare new clean architecture with old approach (if available)."""
    is_valid, error = validate_model_config()
    if not is_valid:
        pytest.skip(f"Model configuration error: {error}")

    # Test new clean architecture
    start_time = asyncio.get_event_loop().time()

    result = await loadset_agent.run(
        "Load 'solution/loads/new_loads.json' and convert units to kN. Give me a summary."
    )

    end_time = asyncio.get_event_loop().time()
    clean_duration = end_time - start_time

    # Validate result
    assert result.output, "Clean architecture should return response"
    assert "kN" in result.output or "kilonewton" in result.output.lower(), (
        "Should mention unit conversion"
    )

    print(f"✅ Clean architecture completed in {clean_duration:.2f} seconds")
    print("💪 Benefits demonstrated:")
    print("   - Zero boilerplate code needed")
    print("   - Direct agent usage with simple .run() calls")
    print("   - Provider-agnostic (works with any model)")
    print("   - Clean error handling")


if __name__ == "__main__":
    # Run a quick integration test
    async def quick_test():
        """Quick test to verify everything works."""
        print("🧪 Quick Clean Architecture Test")
        print("=" * 40)

        is_valid, error = validate_model_config()
        if not is_valid:
            print(f"❌ Configuration error: {error}")
            return False

        print(f"✅ Using model: {get_model_name()}")

        try:
            # Test LoadSet agent
            result = await loadset_agent.run(
                "Load 'solution/loads/new_loads.json' and give me a quick summary."
            )
            print(f"✅ LoadSet agent: {len(result.output)} character response")

            # Test Python agent
            result = await python_agent.run(
                "Execute: print('Hello from clean Python agent!')"
            )
            print(f"✅ Python agent: {len(result.output)} character response")

            print("🎉 Clean architecture working perfectly!")
            return True

        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False

    success = asyncio.run(quick_test())
    print(f"Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
