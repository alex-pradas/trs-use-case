"""
Integration test for Anthropic AI agent with MCP server using HTTP transport.

This test validates that an AI agent can successfully interact with the MCP server
using HTTP transport to process load data and that the final mathematical results are correct.
"""

import os
import tempfile
import re
import asyncio
import pytest
import sys
import subprocess
from pathlib import Path
from typing import Optional, Dict
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP

# Add the project root to Python path so we can import from tools
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tools.loads import LoadSet

# Load environment variables from .env file
load_dotenv()


class AnthropicMCPHTTPTestAgent:
    """
    A Pydantic-AI agent client using Anthropic models for testing MCP server functionality via HTTP.

    This agent connects to the MCP server via HTTP transport and uses Anthropic's Claude model
    to test the actual MCP protocol communication with focus on final value validation.
    """

    def __init__(self):
        """Initialize the agent with MCP server HTTP connection."""
        self.mcp_server: MCPServerStreamableHTTP
        self.agent: Agent
        self.server_process = None

        # Use HTTP transport with the server running on default port
        self.mcp_server = MCPServerStreamableHTTP(
            url="http://127.0.0.1:8000/mcp/",
            timeout=30.0,  # Increased timeout for HTTP connections
        )

        self.agent = Agent(
            "anthropic:claude-3-5-sonnet-latest",
            mcp_servers=[self.mcp_server],
            system_prompt="""
            You are a test agent for processing structural load data.
            
            Always use the available tools to perform the requested operations.
            Be precise and follow the user's instructions exactly.
            You can choose the optimal order of operations to achieve the desired result.
            """,
        )

    async def start_server(self):
        """Start the MCP server in HTTP mode."""
        # Start the server process
        self.server_process = subprocess.Popen(
            [
                "/opt/homebrew/bin/uv",
                "--directory",
                str(Path.cwd()),
                "run",
                "python",
                "tools/mcps/loads_mcp_server.py",
                "http",
            ]
        )

        # Give the server time to start
        await asyncio.sleep(3)

    async def stop_server(self):
        """Stop the MCP server."""
        if self.server_process:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
                self.server_process.wait()


def extract_force_value(ansys_content: str, component: str) -> Optional[float]:
    """
    Extract a specific force/moment component value from ANSYS file content.

    Args:
        ansys_content: Content of the ANSYS .inp file
        component: Component to extract (fx, fy, fz, mx, my, mz)

    Returns:
        float: The extracted value, or None if not found
    """
    # Pattern to match f,all,component,value
    pattern = rf"f,all,{component},([+-]?\d*\.?\d+[eE]?[+-]?\d*)"

    matches = re.findall(pattern, ansys_content, re.IGNORECASE)

    if matches:
        # Return the first match converted to float
        return float(matches[0])

    return None


def calculate_expected_values(
    original_values: Dict[str, float], factor: float
) -> Dict[str, float]:
    """
    Calculate expected values after factoring by 1.5 and converting N→klbf, Nm→lbf-ft.

    Args:
        original_values: Dict with original force/moment values in N/Nm
        factor: Scaling factor (1.5)

    Returns:
        Dict with expected values in klbf/lbf-ft
    """
    # Conversion factors from loads.py (must match exactly)
    force_conversion = 1.0 / 4448.222  # N to klbf
    moment_conversion = 1.0 / 1.355818  # Nm to lbf-ft

    expected = {}

    for key, value in original_values.items():
        if key in ["fx", "fy", "fz"]:
            # Force components: N → klbf
            expected[key] = value * factor * force_conversion
        else:
            # Moment components: Nm → lbf-ft
            expected[key] = value * factor * moment_conversion

    return expected


@pytest.mark.expensive
class TestAnthropicMCPHTTPIntegration:
    """Test class for Anthropic MCP HTTP integration."""

    def setup_method(self):
        """Setup for each test method."""
        # Skip if no API key
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")

        self.agent = AnthropicMCPHTTPTestAgent()

    def teardown_method(self):
        """Teardown for each test method."""
        # Cleanup will be handled by async context managers in tests
        pass

    @pytest.mark.asyncio
    async def test_agent_http_connection_and_basic_operations(self):
        """Test that the agent can connect via HTTP and perform basic operations."""
        try:
            # Start server
            await self.agent.start_server()

            async with self.agent.mcp_server:
                result = await self.agent.agent.run(
                    """
                    Load the JSON file from solution/loads/new_loads.json and provide a summary.
                    """
                )

                # Verify the result contains information about loading
                result_text = str(result.output)
                assert "load" in result_text.lower()
                assert any(
                    keyword in result_text.lower()
                    for keyword in ["case", "point", "summary"]
                )

        except Exception as e:
            pytest.fail(f"HTTP connection test failed: {e}")
        finally:
            # Stop server
            await self.agent.stop_server()

    @pytest.mark.asyncio
    async def test_agent_http_final_value_validation(self):
        """Test HTTP transport with final value validation using known data."""
        # Get original values from the JSON for validation
        original_loadset = LoadSet.read_json(Path("solution/loads/new_loads.json"))
        first_load_case = original_loadset.load_cases[0]
        first_point_load = first_load_case.point_loads[0]

        # Store original values for comparison
        original_values = {
            "fx": first_point_load.force_moment.fx,
            "fy": first_point_load.force_moment.fy,
            "fz": first_point_load.force_moment.fz,
            "mx": first_point_load.force_moment.mx,
            "my": first_point_load.force_moment.my,
            "mz": first_point_load.force_moment.mz,
        }

        # Calculate expected values after scaling by 1.5 and converting to klbf/lbf-ft
        expected_values = calculate_expected_values(original_values, 1.5)

        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Start server
                await self.agent.start_server()

                async with self.agent.mcp_server:
                    result = await self.agent.agent.run(
                        f"""
                        Please perform these operations in sequence:
                        1. Load the JSON file from solution/loads/new_loads.json
                        2. Scale all loads by a factor of 1.5
                        3. Convert the units to klbf (for forces)
                        4. Export to ANSYS format in {temp_dir} with name stem 'scaled_loads'
                        
                        Provide a summary of what was accomplished.
                        """
                    )

                    # Verify files were created
                    output_files = list(Path(temp_dir).glob("*.inp"))
                    assert len(output_files) > 0, "No ANSYS files were created"

                    # Find the file for the first load case (Take_off_004) to match our test data
                    first_load_case_name = "Take_off_004"
                    target_files = [
                        f for f in output_files if first_load_case_name in f.name
                    ]
                    assert len(target_files) > 0, (
                        f"Could not find ANSYS file for {first_load_case_name}"
                    )
                    first_file = target_files[0]
                    with open(first_file, "r") as f:
                        ansys_content = f.read()

                    # Extract values and compare with expected (use percentage-based tolerances)
                    tolerance_percent_force = (
                        0.01  # 1% tolerance for forces (high precision expected)
                    )
                    tolerance_percent_moment = (
                        0.01  # 1% tolerance for moments (high precision expected)
                    )

                    for component in ["fx", "fy", "fz", "mx", "my", "mz"]:
                        actual_value = extract_force_value(ansys_content, component)
                        expected_value = expected_values[component]

                        assert actual_value is not None, (
                            f"Could not find {component} in ANSYS file"
                        )

                        # Use percentage-based tolerance
                        if component in ["fx", "fy", "fz"]:
                            tolerance_percent = tolerance_percent_force
                        else:
                            tolerance_percent = tolerance_percent_moment

                        # Calculate absolute tolerance based on expected value
                        absolute_tolerance = abs(expected_value) * tolerance_percent
                        difference = abs(actual_value - expected_value)
                        percent_difference = (
                            (difference / abs(expected_value)) * 100
                            if expected_value != 0
                            else 0
                        )

                        assert difference < absolute_tolerance, (
                            f"{component}: expected {expected_value:.6f}, got {actual_value:.6f}, "
                            f"difference {difference:.6f} ({percent_difference:.2f}%) > {tolerance_percent * 100:.1f}% tolerance"
                        )

                    # Verify the agent's response mentions the operations
                    result_text = str(result.output).lower()
                    assert any(
                        keyword in result_text
                        for keyword in ["load", "scale", "convert", "export"]
                    )

            except Exception as e:
                pytest.fail(f"HTTP final value validation test failed: {e}")
            finally:
                # Stop server
                await self.agent.stop_server()

    @pytest.mark.asyncio
    async def test_agent_http_handles_load_case_selection(self):
        """Test HTTP transport with load case selection functionality."""
        try:
            # Start server
            await self.agent.start_server()

            async with self.agent.mcp_server:
                result = await self.agent.agent.run(
                    """
                    Load the JSON file from solution/loads/new_loads.json and list all available load cases.
                    Provide the names and descriptions of each load case.
                    """
                )

                # Verify the result contains load case information
                result_text = str(result.output)
                assert (
                    "load case" in result_text.lower()
                    or "loadcase" in result_text.lower()
                )

        except Exception as e:
            pytest.fail(f"HTTP load case selection test failed: {e}")
        finally:
            # Stop server
            await self.agent.stop_server()

    @pytest.mark.asyncio
    async def test_agent_http_mathematical_calculations(self):
        """Test HTTP transport with mathematical validation of unit conversions."""
        try:
            # Start server
            await self.agent.start_server()

            async with self.agent.mcp_server:
                result = await self.agent.agent.run(
                    """
                    Load the JSON file from solution/loads/new_loads.json.
                    Get the current units and then convert to kN units.
                    Provide information about the original and new units.
                    """
                )

                # Verify the result mentions unit conversion
                result_text = str(result.output).lower()
                assert any(
                    keyword in result_text
                    for keyword in ["unit", "convert", "kn", "newton"]
                )

        except Exception as e:
            pytest.fail(f"HTTP mathematical calculations test failed: {e}")
        finally:
            # Stop server
            await self.agent.stop_server()
