"""
Integration tests for AI agent with MCP server using both stdio and HTTP transports.

This test validates that an AI agent can successfully interact with the MCP server
to process load data and that the final mathematical results are correct,
regardless of the tool execution order.
"""

import os
import tempfile
import shutil
import re
import asyncio
import pytest
import subprocess
from pathlib import Path

# No typing imports needed
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio, MCPServerStreamableHTTP

from tools.loads import LoadSet

# Load environment variables from .env file
load_dotenv()


class MCPTestAgentStdio:
    """
    A Pydantic-AI agent client using Anthropic models for testing MCP server functionality via stdio.

    This agent connects directly to the MCP server via MCPServerStdio and uses Anthropic's Claude model
    to test the actual MCP protocol communication with focus on final value validation.
    """

    def __init__(self):
        """Initialize the agent with MCP server connection."""
        self.mcp_server: MCPServerStdio
        self.agent: Agent

        self.mcp_server = MCPServerStdio(
            "/opt/homebrew/bin/uv",
            args=[
                "--directory",
                str(Path.cwd()),  # Use current working directory
                "run",
                "python",
                "tools/mcps/loads_mcp_server.py",
                "stdio",  # Specify stdio transport for integration tests
            ],
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


class MCPTestAgentHTTP:
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


def extract_force_value(ansys_content: str, component: str) -> float | None:
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
    original_values: dict[str, float], factor: float
) -> dict[str, float]:
    """
    Calculate expected values after factoring by 1.5 and converting N→klbf, Nm→lbf-ft.

    Args:
        original_values: Dict with original force/moment values in N/Nm
        factor: Scaling factor (1.5)

    Returns:
        Dict with expected values in klbf/lbf-ft
    """
    # Conversion factors from loads.py
    force_conversion = 1.0 / 4448.222  # N to klbf
    moment_conversion = 1.0 / 1.355818  # Nm to lbf-ft

    expected = {}

    for component, original_value in original_values.items():
        scaled_value = original_value * factor

        if component in ["fx", "fy", "fz"]:
            # Force components
            expected[component] = scaled_value * force_conversion
        else:
            # Moment components (mx, my, mz)
            expected[component] = scaled_value * moment_conversion

    return expected


@pytest.mark.expensive
class TestMCPStdioIntegration:
    """Test suite for AI agent integration via stdio with focus on final value validation."""

    def setup_method(self):
        """Set up test environment."""
        # Create test agent (it will create its own MCP server connection)
        self.agent = MCPTestAgentStdio()

        # Create temporary output directory
        self.temp_dir = tempfile.mkdtemp()
        self.output_folder = Path(self.temp_dir) / "output"
        self.output_folder.mkdir(exist_ok=True)

    def teardown_method(self):
        """Clean up test environment."""
        # Clean up temporary directory
        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    async def test_agent_final_value_validation(self):
        """
        Test that the agent produces mathematically correct final values.

        This test lets the agent choose the tool execution order but validates
        that the final mathematical results are correct.
        """

        # Run agent with the same prompt as loads_agent.py
        async with self.agent.mcp_server:
            result = await self.agent.agent.run(
                f"""Please help me process the loads in use_case_definition/data/loads/03_A_new_loads.json. 
                Factor them by 1.5 and convert to klbf. Generate files for ansys in a subfolder called {self.output_folder}.
                
                Use export_to_ansys with folder_path="{self.output_folder}" and name_stem="processed_loads"
                """
            )

        # Validate agent response
        assert result.output, "Agent workflow failed or returned empty output"

        # Validate that output files were created
        assert self.output_folder.exists(), "Output folder was not created"

        # Find the ANSYS file for Take_off_004 load case
        ansys_files = list(self.output_folder.glob("processed_loads_Take_off_004.inp"))
        assert len(ansys_files) == 1, (
            f"Expected 1 Take_off_004 file, found {len(ansys_files)}"
        )

        ansys_file = ansys_files[0]
        content = ansys_file.read_text()

        # Read original values from 03_A_new_loads.json for Take_off_004, Point A
        original_loadset = LoadSet.read_json(
            Path("use_case_definition/data/loads/03_A_new_loads.json")
        )

        # Find Take_off_004 load case
        take_off_004 = None
        for load_case in original_loadset.load_cases:
            if load_case.name == "Take_off_004":
                take_off_004 = load_case
                break

        assert take_off_004 is not None, "Take_off_004 load case not found in JSON file"

        # Find Point A in Take_off_004
        point_a = None
        for point_load in take_off_004.point_loads:
            if point_load.name == "Point A":
                point_a = point_load
                break

        assert point_a is not None, "Point A not found in Take_off_004 load case"

        # Extract original values from the JSON data
        fm = point_a.force_moment
        original_values = {
            "fx": fm.fx,
            "fy": fm.fy,
            "fz": fm.fz,
            "mx": fm.mx,
            "my": fm.my,
            "mz": fm.mz,
        }

        # Calculate expected values after factor by 1.5 and convert to klbf/lbf-ft
        expected_values = calculate_expected_values(original_values, 1.5)

        # Validate specific force and moment values
        tolerance_force = 0.00001  # klbf tolerance
        tolerance_moment = 0.001  # lbf-ft tolerance

        for component, expected_value in expected_values.items():
            actual_value = extract_force_value(content, component)

            if expected_value != 0.0:  # Only check non-zero values
                assert actual_value is not None, (
                    f"Could not find {component} value in ANSYS file"
                )

                if component in ["fx", "fy", "fz"]:
                    tolerance = tolerance_force
                else:
                    tolerance = tolerance_moment

                assert abs(actual_value - expected_value) < tolerance, (
                    f"{component}: expected {expected_value:.6f}, got {actual_value:.6f}, "
                    f"difference {abs(actual_value - expected_value):.6f} > tolerance {tolerance}"
                )

    async def test_agent_handles_load_case_selection(self):
        """Test that agent can process multiple load cases correctly."""

        # Run agent workflow
        async with self.agent.mcp_server:
            result = await self.agent.agent.run(
                f"""Please help me process the loads in use_case_definition/data/loads/03_A_new_loads.json. 
                Factor by 2.0 and convert to kN. Generate files for ansys in {self.output_folder}.
                
                Use export_to_ansys with folder_path="{self.output_folder}" and name_stem="test_loads"
                """
            )

        assert result.output, "Agent workflow failed or returned empty output"

        # Load original data to verify number of files
        original_loadset = LoadSet.read_json(
            Path("use_case_definition/data/loads/03_A_new_loads.json")
        )
        expected_files = len(original_loadset.load_cases)

        # Check that all load cases were processed
        ansys_files = list(self.output_folder.glob("test_loads_*.inp"))
        assert len(ansys_files) == expected_files, (
            f"Expected {expected_files} files, got {len(ansys_files)}"
        )

        # Verify that files contain valid ANSYS commands
        for ansys_file in ansys_files[:3]:  # Check first 3 files
            content = ansys_file.read_text()
            assert "f,all," in content, f"File {ansys_file.name} missing f,all commands"
            assert "/TITLE," in content, f"File {ansys_file.name} missing title command"

    def test_mathematical_calculations(self):
        """Test the mathematical calculation functions used for validation."""
        # Read test values from Take_off_004, Point A
        original_loadset = LoadSet.read_json(
            Path("use_case_definition/data/loads/03_A_new_loads.json")
        )

        # Find Take_off_004 load case and Point A
        take_off_004 = next(
            lc for lc in original_loadset.load_cases if lc.name == "Take_off_004"
        )
        point_a = next(pl for pl in take_off_004.point_loads if pl.name == "Point A")

        fm = point_a.force_moment
        original_values = {
            "fx": fm.fx,
            "fy": fm.fy,
            "fz": fm.fz,
            "mx": fm.mx,
            "my": fm.my,
            "mz": fm.mz,
        }

        expected_values = calculate_expected_values(original_values, 1.5)

        # Manually verify a few calculations using actual values from JSON
        # fx: original_fx * 1.5 / 4448.222 (N to klbf conversion)
        expected_fx = original_values["fx"] * 1.5 / 4448.222
        assert abs(expected_values["fx"] - expected_fx) < 0.000001

        # mx: original_mx * 1.5 / 1.355818 (Nm to lbf-ft conversion)
        expected_mx = original_values["mx"] * 1.5 / 1.355818
        assert abs(expected_values["mx"] - expected_mx) < 0.001

    def test_ansys_file_parsing(self):
        """Test ANSYS file parsing helper function."""
        # Sample ANSYS content
        sample_content = """
        /TITLE,Take_off_004
        nsel,u,,,all
        
        cmsel,s,pilot_Point_A
        f,all,fx,2.567e-04
        nsel,u,,,all
        
        cmsel,s,pilot_Point_A
        f,all,fy,2.948e-04
        nsel,u,,,all
        
        cmsel,s,pilot_Point_A
        f,all,mx,9.856e-01
        nsel,u,,,all
        """

        # Test extraction
        fx_value = extract_force_value(sample_content, "fx")
        fy_value = extract_force_value(sample_content, "fy")
        mx_value = extract_force_value(sample_content, "mx")
        fz_value = extract_force_value(sample_content, "fz")  # Should be None

        assert fx_value is not None and abs(fx_value - 2.567e-04) < 1e-7
        assert fy_value is not None and abs(fy_value - 2.948e-04) < 1e-7
        assert mx_value is not None and abs(mx_value - 9.856e-01) < 1e-4
        assert fz_value is None  # Not present in sample


@pytest.mark.expensive
class TestMCPHTTPIntegration:
    """Test class for MCP HTTP integration."""

    def setup_method(self):
        """Setup for each test method."""
        # Skip if no API key
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")

        self.agent = MCPTestAgentHTTP()

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
                    Load the JSON file from use_case_definition/data/loads/03_A_new_loads.json and provide a summary.
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
        original_loadset = LoadSet.read_json(
            Path("use_case_definition/data/loads/03_A_new_loads.json")
        )
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
                        1. Load the JSON file from use_case_definition/data/loads/03_A_new_loads.json
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
                    Load the JSON file from use_case_definition/data/loads/03_A_new_loads.json and list all available load cases.
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
                    Load the JSON file from use_case_definition/data/loads/03_A_new_loads.json.
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
