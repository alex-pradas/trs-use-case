"""
Consolidated integration tests for AI agents with MCP server integration.

This module consolidates all general agent integration tests including:
- LoadSet agent with clean architecture
- Python execution agent integration
"""

import pytest
import asyncio
import os
import tempfile
import shutil
import json
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

from tools.agents import create_loadset_agent, create_python_agent, create_script_agent
from tools.dependencies import MCPServerProvider
from tools.model_config import get_model_name, validate_model_config
from tools.mcps.loads_mcp_server import reset_global_state
from tools.mcps.python_exec_mcp_server import (
    create_mcp_server as create_python_mcp_server,
    PythonExecutorMCPProvider,
)
from tools.mcps.script_exec_mcp_server import create_mcp_server as create_script_mcp_server
from tools.loads import LoadSet

# Load environment variables from .env file
load_dotenv()


# =============================================================================
# LOADSET AGENT INTEGRATION TESTS
# =============================================================================

@pytest.mark.expensive
class TestLoadSetAgentIntegration:
    """Test suite for LoadSet agent integration with MCP server."""

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
    async def test_loadset_agent_full_workflow(self):
        """Test complete LoadSet workflow with clean agent architecture."""
        # Validate configuration
        is_valid, error = validate_model_config()
        if not is_valid:
            pytest.skip(f"Model configuration error: {error}")

        # Test data
        json_path = "solution/loads/new_loads.json"
        target_units = "klbf"
        scale_factor = 1.5
        output_folder = str(self.output_folder)

        # Create agent and dependencies
        agent = create_loadset_agent()
        deps = MCPServerProvider()

        # Run the complete workflow using clean architecture
        result = await agent.run(
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
        
        Return the results of each operation.
        """,
            deps=deps,
        )

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
    async def test_loadset_agent_error_handling(self):
        """Test error handling with LoadSet agent."""
        # Validate configuration
        is_valid, error = validate_model_config()
        if not is_valid:
            pytest.skip(f"Model configuration error: {error}")

        # Create agent and dependencies
        agent = create_loadset_agent()
        deps = MCPServerProvider()

        # Test with invalid file path
        result = await agent.run(
            "Please load LoadSet data from nonexistent_file.json", deps=deps
        )

        # Should handle the error gracefully
        assert result.output, "Agent should return a response even for errors"

    def test_loadset_agent_tool_availability(self):
        """Test that LoadSet agent has properly registered tools."""
        # Create agent
        agent = create_loadset_agent()

        # Check that agent has tools registered
        assert hasattr(agent, "_tools"), "LoadSet agent should have tools"

        # Check specific tools exist
        tool_names = [tool.function.__name__ for tool in agent._tools.values()]
        assert "load_from_json" in tool_names, (
            "LoadSet agent should have load_from_json tool"
        )
        assert "convert_units" in tool_names, (
            "LoadSet agent should have convert_units tool"
        )

    @pytest.mark.asyncio
    async def test_loadset_agent_model_switching(self):
        """Test that LoadSet agent works with different model configurations."""
        # Validate configuration
        is_valid, error = validate_model_config()
        if not is_valid:
            pytest.skip(f"Model configuration error: {error}")

        current_model = get_model_name()

        # Create agent and dependencies
        agent = create_loadset_agent()
        deps = MCPServerProvider()

        # Test basic functionality with current model
        result = await agent.run(
            "Load 'solution/loads/new_loads.json' and tell me how many load cases it contains.",
            deps=deps,
        )

        assert result.output, "Agent should work with current model"
        assert "25" in result.output or "load cases" in result.output.lower(), (
            "Should report load case count"
        )


# =============================================================================
# PYTHON EXECUTION AGENT INTEGRATION TESTS
# =============================================================================

@pytest.mark.expensive
class TestPythonExecutionAgentIntegration:
    """Test suite for Python execution agent integration."""

    def setup_method(self):
        """Set up test environment."""
        # Create Python execution MCP server
        self.server = create_python_mcp_server()
        self.provider = PythonExecutorMCPProvider()

    def teardown_method(self):
        """Clean up test environment."""
        # Reset any persistent state
        if hasattr(self, "provider"):
            try:
                self.provider.reset_environment()
            except:
                pass

    @pytest.mark.asyncio
    async def test_python_agent_basic_functionality(self):
        """Test basic Python agent functionality with clean architecture."""
        # Validate configuration
        is_valid, error = validate_model_config()
        if not is_valid:
            pytest.skip(f"Model configuration error: {error}")

        # Create agent and dependencies
        agent = create_python_agent()
        deps = MCPServerProvider()

        # Test basic code execution
        result = await agent.run(
            """
        Generate Python code to:
        1. Calculate the factorial of 5
        2. Create a list of the first 10 fibonacci numbers  
        3. Print both results
        
        Execute the code step by step.
        """,
            deps=deps,
        )

        # Validate response
        assert result.output, "Agent should return a response"
        assert "factorial" in result.output.lower() or "120" in result.output, (
            "Should mention factorial calculation"
        )

        print(
            f"✅ Python agent test passed: {len(result.output)} character response"
        )

    @pytest.mark.asyncio
    async def test_python_agent_iterative_development(self):
        """Test iterative development with persistent variables."""
        # Validate configuration
        is_valid, error = validate_model_config()
        if not is_valid:
            pytest.skip(f"Model configuration error: {error}")

        # Create agent and dependencies
        agent = create_python_agent()
        deps = MCPServerProvider()

        # First execution - create variables
        result1 = await agent.run(
            """
        Create a variable called 'my_data' containing a list of numbers [1, 2, 3, 4, 5].
        Then calculate the sum and store it in 'total'.
        Print both variables.
        """,
            deps=deps,
        )

        assert result1.output, "First execution should return a response"

        # Second execution - use previously created variables
        result2 = await agent.run(
            """
        Use the previously created 'my_data' variable.
        Calculate the average of the numbers and store it in 'average'.
        Print the average.
        """,
            deps=deps,
        )

        assert result2.output, "Second execution should return a response"
        assert "average" in result2.output.lower(), "Should mention average calculation"

    @pytest.mark.asyncio
    async def test_python_agent_data_analysis_challenge(self):
        """Test data analysis capabilities with numpy/matplotlib."""
        # Validate configuration
        is_valid, error = validate_model_config()
        if not is_valid:
            pytest.skip(f"Model configuration error: {error}")

        # Create agent and dependencies
        agent = create_python_agent()
        deps = MCPServerProvider()

        # Test data analysis workflow
        result = await agent.run(
            """
        Perform a data analysis task:
        1. Create sample data points (x, y) for a sine wave
        2. Use numpy to generate x values from 0 to 2π
        3. Calculate y = sin(x)
        4. Print the first 5 data points
        
        Handle any missing imports gracefully.
        """,
            deps=deps,
        )

        assert result.output, "Data analysis should return a response"
        assert "sin" in result.output.lower() or "numpy" in result.output.lower(), (
            "Should mention sine function or numpy"
        )

    @pytest.mark.asyncio
    async def test_python_agent_loadset_integration(self):
        """Test LoadSet integration with Python agent."""
        # Validate configuration
        is_valid, error = validate_model_config()
        if not is_valid:
            pytest.skip(f"Model configuration error: {error}")

        # Create agent and dependencies
        agent = create_python_agent()
        deps = MCPServerProvider()

        # Test LoadSet class availability
        result = await agent.run(
            """
        Check if LoadSet class is available and test basic functionality:
        1. Try to import LoadSet from tools.loads
        2. If successful, create a simple LoadSet instance
        3. Print the result
        
        Handle any import errors gracefully.
        """,
            deps=deps,
        )

        assert result.output, "LoadSet integration should return a response"

    @pytest.mark.asyncio
    async def test_python_agent_error_handling(self):
        """Test error handling and debugging capabilities."""
        # Validate configuration
        is_valid, error = validate_model_config()
        if not is_valid:
            pytest.skip(f"Model configuration error: {error}")

        # Create agent and dependencies
        agent = create_python_agent()
        deps = MCPServerProvider()

        # Test error handling
        result = await agent.run(
            """
        Create code that will cause an error, then fix it:
        1. Try to divide by zero
        2. Catch the error
        3. Fix the code to handle the error properly
        4. Print the result
        """,
            deps=deps,
        )

        assert result.output, "Error handling should return a response"
        assert "error" in result.output.lower() or "exception" in result.output.lower(), (
            "Should mention error handling"
        )

    def test_python_agent_tool_availability(self):
        """Test that Python agent has properly registered tools."""
        # Create agent
        agent = create_python_agent()

        # Check that agent has tools registered
        assert hasattr(agent, "_tools"), "Python agent should have tools"

        # Check specific tools exist
        tool_names = [tool.function.__name__ for tool in agent._tools.values()]
        assert "execute_code" in tool_names, (
            "Python agent should have execute_code tool"
        )

    def test_python_direct_tool_functionality(self):
        """Test that Python MCP tools work correctly without agent."""
        # Test execute_code tool
        result = self.provider.execute_code("print('Direct tool test')")
        assert result["success"], f"execute_code failed: {result.get('error')}"
        assert "Direct tool test" in result["output"], "Output should contain expected text"

        # Test get_variables tool
        result = self.provider.get_variables()
        assert result["success"], f"get_variables failed: {result.get('error')}"
        assert "variables" in result, "Should return variables"

        # Test reset_environment tool
        result = self.provider.reset_environment()
        assert result["success"], f"reset_environment failed: {result.get('error')}"