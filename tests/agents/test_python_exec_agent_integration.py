"""
Integration test for AI agent with Python execution MCP server using clean architecture.

This test validates that the clean python_agent can successfully interact with the Python execution
MCP server to generate and execute Python code autonomously.
"""

import pytest
import asyncio
import os
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

from tools.agents import create_python_agent  # noqa: E402
from tools.dependencies import MCPServerProvider  # noqa: E402
from tools.model_config import get_model_name, validate_model_config  # noqa: E402
from tools.mcps.python_exec_mcp_server import (  # noqa: E402
    create_mcp_server,
    PythonExecutorMCPProvider,
)

# Load environment variables from .env file
load_dotenv()


# No more boilerplate agent classes needed with clean architecture!


@pytest.mark.expensive
class TestPythonExecutionCleanAgentIntegration:
    """Test suite for clean Python execution agent integration."""

    @pytest.mark.asyncio
    async def test_clean_python_agent_basic_functionality(self):
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
            f"✅ Clean Python agent test passed: {len(result.output)} character response"
        )


# Keep one old test class for comparison (can be removed after full migration)
class TestPythonExecutionAgentIntegration:
    """Original test class - to be migrated to clean architecture."""

    def __init__(self, server, disable_security=False):
        """Initialize the agent with a Python execution MCP server."""
        self.server = server
        self.agent = None
        self.disable_security = disable_security

        # Only create pydantic-ai agent if Anthropic API key is available
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                from pydantic_ai import Agent

                self.agent = Agent(
                    "anthropic:claude-3-5-sonnet-latest",
                    system_prompt="""
                    You are a Python programming assistant with access to a persistent Python execution environment.
                    
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
                )

                # Register MCP tools with the agent
                self._register_tools()

                # Disable security if requested for testing
                if self.disable_security:
                    self.call_tool_directly("configure_security", enable_security=False)
            except ImportError:
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

    async def solve_programming_challenge(self, challenge: str) -> dict[str, Any]:
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
                "error": "Anthropic API key not available or pydantic-ai not installed",
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
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def test_iterative_development(self) -> dict[str, Any]:
        """
        Test the agent's ability to do iterative development with persistent variables.

        Returns:
            Dict containing the results of the iterative development test
        """
        if not self.agent:
            return {
                "success": False,
                "error": "Anthropic API key not available or pydantic-ai not installed",
            }

        try:
            result = await self.agent.run("""
            Please demonstrate iterative development by:
            
            1. Create a list of numbers from 1 to 10 and store it in a variable called 'numbers'
            2. Calculate the sum of these numbers and store it in 'total'  
            3. Calculate the average and store it in 'average'
            4. Create a simple plot showing the numbers vs their squares
            5. List all variables to show they persist across executions
            
            Execute each step separately to show that variables persist between executions.
            """)

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
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def call_tool_directly(self, tool_name: str, **kwargs) -> dict[str, Any]:
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


@pytest.mark.expensive
class TestPythonExecutionAgentIntegration:
    """Test suite for AI agent integration with Python execution MCP server."""

    def setup_method(self):
        """Set up test environment."""
        # Create MCP server
        self.server = create_mcp_server()

        # Create test agent
        self.agent = PythonExecutionMCPTestAgent(self.server)

    @pytest.mark.asyncio
    async def test_agent_basic_code_generation(self):
        """Test that agent can generate and execute basic Python code."""
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not available")

        challenge = """
        Please write and execute Python code to:
        1. Calculate the factorial of 5
        2. Create a list of the first 10 Fibonacci numbers
        3. Show the results
        
        Execute the code step by step.
        """

        result = await self.agent.solve_programming_challenge(challenge)

        assert result["success"], (
            f"Agent challenge failed: {result.get('error', 'Unknown error')}"
        )
        assert "agent_response" in result

        # Check that the agent actually executed code by examining execution history
        history = self.agent.call_tool_directly("get_execution_history", limit=10)
        assert history["success"], "Failed to get execution history"
        assert len(history["tool_result"]["history"]) > 0, (
            "No code executions found in history"
        )

        # Look for evidence of factorial and fibonacci in the code history
        code_history = [entry["code"] for entry in history["tool_result"]["history"]]
        code_text = " ".join(code_history).lower()

        # The agent should have generated code related to the challenge
        assert any(word in code_text for word in ["factorial", "fibonacci"]), (
            f"Expected factorial/fibonacci code but found: {code_text}"
        )

    @pytest.mark.asyncio
    async def test_agent_iterative_development(self):
        """Test agent's ability to do iterative development with persistent variables."""
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not available")

        result = await self.agent.test_iterative_development()

        assert result["success"], (
            f"Iterative development test failed: {result.get('error', 'Unknown error')}"
        )

        # Check execution history to verify multiple code executions
        history = self.agent.call_tool_directly("get_execution_history", limit=10)
        assert history["success"], "Failed to get execution history"
        assert len(history["tool_result"]["history"]) > 1, (
            "Agent should have made multiple executions for iterative development"
        )

        # Verify that variables were created and persist
        variables = self.agent.call_tool_directly("list_variables")
        assert variables["success"], "Failed to list variables"

        var_names = variables["tool_result"]["variables"].keys()
        expected_vars = ["numbers", "total", "average"]

        # At least some of the expected variables should exist
        found_vars = [var for var in expected_vars if var in var_names]
        assert len(found_vars) > 0, (
            f"Expected variables {expected_vars} not found in {list(var_names)}"
        )

    @pytest.mark.asyncio
    async def test_agent_data_analysis_challenge(self):
        """Test agent's ability to solve a data analysis challenge."""
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not available")

        challenge = """
        Please solve this data analysis challenge step by step:
        
        1. Create a dataset with 100 random data points (use numpy)
        2. Calculate basic statistics (mean, std, min, max)
        3. Create a histogram of the data
        4. Identify any outliers (values > 2 standard deviations from mean)
        5. Show the count of outliers
        
        Use numpy and matplotlib for this analysis. Execute each step and show the results.
        """

        result = await self.agent.solve_programming_challenge(challenge)

        assert result["success"], (
            f"Data analysis challenge failed: {result.get('error', 'Unknown error')}"
        )

        # Check that numpy was used and results were calculated
        history = self.agent.call_tool_directly("get_execution_history", limit=10)
        assert history["success"], "Failed to get execution history"
        assert len(history["tool_result"]["history"]) > 1, (
            "Agent should have executed multiple code blocks"
        )

        # Look for evidence of numpy usage and statistics calculation
        code_history = [entry["code"] for entry in history["tool_result"]["history"]]
        code_text = " ".join(code_history).lower()

        assert "numpy" in code_text or "np." in code_text, (
            "Agent should have used numpy"
        )
        assert any(stat in code_text for stat in ["mean", "std", "statistics"]), (
            "Agent should have calculated statistics"
        )

    @pytest.mark.asyncio
    async def test_agent_loadset_integration(self):
        """Test agent's ability to work with LoadSet classes."""
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not available")

        challenge = """
        The LoadSet class should be available for aerospace load analysis.
        
        Please:
        1. Check if LoadSet is available by printing its type
        2. Try to import or access any LoadSet-related classes
        3. Show what LoadSet-related functionality is available
        
        This tests integration with the project's main functionality.
        """

        result = await self.agent.solve_programming_challenge(challenge)

        assert result["success"], (
            f"LoadSet integration test failed: {result.get('error', 'Unknown error')}"
        )

        # Check that the agent executed code
        history = self.agent.call_tool_directly("get_execution_history", limit=5)
        assert history["success"], "Failed to get execution history"
        assert len(history["tool_result"]["history"]) > 0, (
            "Agent should have executed code to check LoadSet"
        )

        # Verify that LoadSet classes are accessible
        variables = self.agent.call_tool_directly("list_variables")
        assert variables["success"], "Failed to list variables"

        # LoadSet should be in the namespace
        var_names = variables["tool_result"]["variables"].keys()
        loadset_classes = ["LoadSet", "LoadCase", "PointLoad", "ForceMoment"]
        found_classes = [cls for cls in loadset_classes if cls in var_names]

        assert len(found_classes) > 0, (
            f"LoadSet classes {loadset_classes} not found in namespace {list(var_names)}"
        )

    @pytest.mark.asyncio
    async def test_agent_aerospace_load_processing_workflow(self):
        """Test agent's ability to process real aerospace load data with unit conversion, scaling, and comparison."""
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not available")

        # Create a special agent with security disabled for file operations
        aerospace_agent = PythonExecutionMCPTestAgent(
            self.server, disable_security=True
        )

        challenge = """
        I need you to process real aerospace structural load data. Please complete this workflow:
        
        STEP 1: Load the aerospace load data
        - Use: new_loads = LoadSet.read_json('solution/loads/new_loads.json')
        - Show the summary (name, units, number of load cases)
        
        STEP 2: Process the loads
        - Convert units: processed_loads = new_loads.convert_to('kN')
        - Scale loads: processed_loads = processed_loads.factor(1.5)
        - Show a sample of the processed data
        
        STEP 3: Export processed data  
        - Import json and Path: from pathlib import Path; import json
        - Use: output_data = processed_loads.to_dict()
        - Write: Path('processed_aerospace_loads.json').write_text(json.dumps(output_data, indent=2))
        - Verify the file was created
        
        STEP 4: Load comparison data and compare
        - Load: old_loads = LoadSet.read_json('solution/loads/old_loads.json')
        - Compare: comparison = new_loads.compare_to(old_loads)
        - Show comparison statistics and key differences
        
        STEP 5: Analysis summary
        - Count load cases in each file
        - Identify load case name differences  
        - Show the largest value differences found
        
        Execute each step with Python code and show the results. Use the exact LoadSet API methods shown.
        """

        result = await aerospace_agent.solve_programming_challenge(challenge)

        assert result["success"], (
            f"Aerospace load processing test failed: {result.get('error', 'Unknown error')}"
        )

        # Check execution history to verify comprehensive workflow
        history = aerospace_agent.call_tool_directly("get_execution_history", limit=15)
        assert history["success"], "Failed to get execution history"
        assert len(history["tool_result"]["history"]) > 3, (
            "Agent should have executed multiple steps"
        )

        # Look for evidence of the workflow in the code history
        code_history = [entry["code"] for entry in history["tool_result"]["history"]]
        code_text = " ".join(code_history).lower()

        # Verify key workflow elements were executed
        workflow_evidence = [
            "loadset.read_json",  # Loading data
            "convert_to",  # Unit conversion
            "factor",  # Scaling
            "json",  # JSON file operations
            "compare",  # LoadSet comparison
        ]

        missing_elements = [elem for elem in workflow_evidence if elem not in code_text]
        assert len(missing_elements) == 0, (
            f"Missing workflow elements: {missing_elements}. Code: {code_text[:500]}..."
        )

        # Verify variables were created for the workflow
        variables = aerospace_agent.call_tool_directly("list_variables")
        assert variables["success"], "Failed to list variables"

        var_names = list(variables["tool_result"]["variables"].keys())

        # Should have created LoadSet-related variables
        loadset_vars = [
            var
            for var in var_names
            if "load" in var.lower() or "processed" in var.lower()
        ]
        assert len(loadset_vars) > 0, (
            f"Expected LoadSet variables but found: {var_names}"
        )

    @pytest.mark.asyncio
    async def test_agent_error_handling_and_debugging(self):
        """Test agent's ability to handle errors and debug code."""
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not available")

        challenge = """
        Please demonstrate error handling and debugging:
        
        1. Try to execute some code that will cause an error (like dividing by zero)
        2. Show how you handle the error
        3. Fix the code and re-execute it correctly
        4. Explain what went wrong and how you fixed it
        
        This tests your ability to debug and recover from errors.
        """

        result = await self.agent.solve_programming_challenge(challenge)

        assert result["success"], (
            f"Error handling test failed: {result.get('error', 'Unknown error')}"
        )

        # Check execution history for evidence of error and recovery
        history = self.agent.call_tool_directly("get_execution_history", limit=10)
        assert history["success"], "Failed to get execution history"
        assert len(history["tool_result"]["history"]) > 1, (
            "Agent should have executed multiple attempts"
        )

        # Look for evidence of errors and corrections
        executions = history["tool_result"]["history"]

        # Should have at least one failed execution and one successful one
        failed_executions = [exec for exec in executions if not exec["success"]]
        successful_executions = [exec for exec in executions if exec["success"]]

        assert len(failed_executions) > 0, (
            "Agent should have encountered at least one error"
        )
        assert len(successful_executions) > 0, (
            "Agent should have successfully executed corrected code"
        )

    def test_direct_tool_functionality(self):
        """Test that all tools work correctly without agent."""
        # Test execute_code
        result = self.agent.call_tool_directly("execute_code", code="x = 5 + 3")
        assert result["success"], f"execute_code failed: {result.get('error')}"
        assert result["tool_result"]["success"], "Code execution failed"

        # Test list_variables
        result = self.agent.call_tool_directly("list_variables")
        assert result["success"], f"list_variables failed: {result.get('error')}"
        assert "x" in result["tool_result"]["variables"], "Variable 'x' not found"

        # Test get_variable
        result = self.agent.call_tool_directly("get_variable", name="x")
        assert result["success"], f"get_variable failed: {result.get('error')}"
        assert result["tool_result"]["variable_info"]["type"] == "int", (
            "Variable type incorrect"
        )

        # Test execution history
        result = self.agent.call_tool_directly("get_execution_history", limit=5)
        assert result["success"], f"get_execution_history failed: {result.get('error')}"
        assert len(result["tool_result"]["history"]) > 0, "No execution history found"

        # Test reset session
        result = self.agent.call_tool_directly("reset_session")
        assert result["success"], f"reset_session failed: {result.get('error')}"

        # Verify variables are cleared
        result = self.agent.call_tool_directly("list_variables")
        assert result["success"], (
            f"list_variables after reset failed: {result.get('error')}"
        )
        assert "x" not in result["tool_result"]["variables"], (
            "Variable 'x' should be cleared after reset"
        )


if __name__ == "__main__":
    pytest.main([__file__])
