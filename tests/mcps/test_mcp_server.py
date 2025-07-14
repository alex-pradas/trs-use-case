"""
Tests for MCP server functionality.

This module tests the FastMCP server implementation for LoadSet operations.
"""

import pytest
from pathlib import Path


from tools.mcps.loads_mcp_server import create_mcp_server, reset_global_state
import tempfile
import json


class TestMCPServerCreation:
    """Test MCP server creation and configuration."""

    def test_create_mcp_server(self):
        """Test that MCP server can be created."""
        server = create_mcp_server()
        assert server is not None
        assert server.name == "LoadSet MCP Server"

    def test_server_has_required_tools(self):
        """Test that server has all required tools registered."""
        server = create_mcp_server()

        # Expected tools
        expected_tools = [
            "load_from_json",
            "convert_units",
            "scale_loads",
            "export_to_ansys",
            "get_load_summary",
            "list_load_cases",
        ]

        # Get registered tools from the internal tool manager
        tool_names = list(server._tool_manager._tools.keys())

        for expected_tool in expected_tools:
            assert expected_tool in tool_names, (
                f"Tool {expected_tool} not found in server"
            )

    def test_server_configuration(self):
        """Test server configuration and metadata."""
        server = create_mcp_server()

        # Test server metadata
        assert hasattr(server, "name")
        assert server.name == "LoadSet MCP Server"


class TestMCPServerImport:
    """Test MCP server import functionality."""

    def test_fastmcp_import(self):
        """Test that FastMCP can be imported."""
        from fastmcp import FastMCP

        assert FastMCP is not None

    def test_mcp_server_import(self):
        """Test that loads_mcp_server module can be imported."""
        import mcps.loads_mcp_server as mcp_server

        assert hasattr(mcp_server, "create_mcp_server")


class TestLoadFromJsonTool:
    """Test load_from_json MCP tool functionality."""

    def test_load_valid_json_file(self):
        """Test loading a valid JSON file."""
        server = create_mcp_server()

        # Create a valid LoadSet JSON file
        test_data = {
            "name": "Test LoadSet",
            "version": 1,
            "units": {"forces": "N", "moments": "Nm"},
            "load_cases": [
                {
                    "name": "Test Case",
                    "description": "Test description",
                    "point_loads": [
                        {
                            "name": "Point 1",
                            "force_moment": {
                                "fx": 100.0,
                                "fy": 200.0,
                                "fz": 300.0,
                                "mx": 10.0,
                                "my": 20.0,
                                "mz": 30.0,
                            },
                        }
                    ],
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_file = f.name

        try:
            # Get the tool function
            tool_func = server._tool_manager._tools["load_from_json"].fn

            # Call the tool
            result = tool_func(temp_file)

            # Verify the result
            assert result["success"] is True
            assert "LoadSet loaded from" in result["message"]
            assert result["loadset_name"] == "Test LoadSet"
            assert result["num_load_cases"] == 1
            assert result["units"]["forces"] == "N"
            assert result["units"]["moments"] == "Nm"

        finally:
            # Clean up
            import os

            os.unlink(temp_file)

    def test_load_nonexistent_file(self):
        """Test loading a non-existent file."""
        server = create_mcp_server()

        # Get the tool function
        tool_func = server._tool_manager._tools["load_from_json"].fn

        # Call the tool with non-existent file
        result = tool_func("/path/that/does/not/exist.json")

        # Verify the error result
        assert result["success"] is False
        assert "error" in result
        assert "File not found" in result["error"]

    def test_load_invalid_json(self):
        """Test loading an invalid JSON file."""
        server = create_mcp_server()

        # Create an invalid JSON file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json content")
            temp_file = f.name

        try:
            # Get the tool function
            tool_func = server._tool_manager._tools["load_from_json"].fn

            # Call the tool
            result = tool_func(temp_file)

            # Verify the error result
            assert result["success"] is False
            assert "error" in result

        finally:
            # Clean up
            import os

            os.unlink(temp_file)

    def test_load_invalid_loadset_data(self):
        """Test loading JSON with invalid LoadSet structure."""
        server = create_mcp_server()

        # Create JSON with invalid LoadSet structure
        invalid_data = {"invalid_field": "test", "missing_required_fields": True}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(invalid_data, f)
            temp_file = f.name

        try:
            # Get the tool function
            tool_func = server._tool_manager._tools["load_from_json"].fn

            # Call the tool
            result = tool_func(temp_file)

            # Verify the error result
            assert result["success"] is False
            assert "error" in result
            assert "Invalid LoadSet data" in result["error"]

        finally:
            # Clean up
            import os

            os.unlink(temp_file)


class TestConvertUnitsTool:
    """Test convert_units MCP tool functionality."""

    def setup_method(self):
        """Set up test data for each test method."""
        reset_global_state()  # Reset state before each test
        self.server = create_mcp_server()
        self.load_tool = self.server._tool_manager._tools["load_from_json"].fn
        self.convert_tool = self.server._tool_manager._tools["convert_units"].fn

        # Create test LoadSet data
        self.test_data = {
            "name": "Test LoadSet",
            "version": 1,
            "units": {"forces": "N", "moments": "Nm"},
            "load_cases": [
                {
                    "name": "Test Case",
                    "point_loads": [
                        {
                            "name": "Point 1",
                            "force_moment": {
                                "fx": 1000.0,
                                "fy": 2000.0,
                                "fz": 3000.0,
                                "mx": 100.0,
                                "my": 200.0,
                                "mz": 300.0,
                            },
                        }
                    ],
                }
            ],
        }

    def teardown_method(self):
        """Clean up after each test method."""
        reset_global_state()  # Reset state after each test

    def test_convert_units_success(self):
        """Test successful unit conversion."""
        # First load a LoadSet
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.test_data, f)
            temp_file = f.name

        try:
            # Load the LoadSet
            load_result = self.load_tool(temp_file)
            assert load_result["success"] is True

            # Convert units from N to kN
            convert_result = self.convert_tool("kN")

            # Verify the conversion result
            assert convert_result["success"] is True
            assert "Units converted from N to kN" in convert_result["message"]
            assert convert_result["new_units"]["forces"] == "kN"
            assert convert_result["new_units"]["moments"] == "kNm"

        finally:
            import os

            os.unlink(temp_file)

    def test_convert_units_no_loadset(self):
        """Test convert_units without loading a LoadSet first."""
        # Reset global state explicitly
        reset_global_state()

        # Try to convert units without loading a LoadSet
        result = self.convert_tool("kN")

        # Verify the error result
        assert result["success"] is False
        assert "No LoadSet loaded" in result["error"]

    def test_convert_units_invalid_units(self):
        """Test conversion with invalid units."""
        # First load a LoadSet
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.test_data, f)
            temp_file = f.name

        try:
            # Load the LoadSet
            load_result = self.load_tool(temp_file)
            assert load_result["success"] is True

            # Try to convert to invalid units
            convert_result = self.convert_tool("invalid_unit")

            # Verify the error result
            assert convert_result["success"] is False
            assert "error" in convert_result

        finally:
            import os

            os.unlink(temp_file)

    def test_convert_units_multiple_conversions(self):
        """Test multiple unit conversions in sequence."""
        # First load a LoadSet
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.test_data, f)
            temp_file = f.name

        try:
            # Load the LoadSet
            load_result = self.load_tool(temp_file)
            assert load_result["success"] is True

            # Convert N -> kN
            result1 = self.convert_tool("kN")
            assert result1["success"] is True
            assert result1["new_units"]["forces"] == "kN"

            # Convert kN -> lbf
            result2 = self.convert_tool("lbf")
            assert result2["success"] is True
            assert result2["new_units"]["forces"] == "lbf"
            assert result2["new_units"]["moments"] == "lbf-ft"

        finally:
            import os

            os.unlink(temp_file)


class TestScaleLoadsTool:
    """Test scale_loads MCP tool functionality."""

    def setup_method(self):
        """Set up test data for each test method."""
        reset_global_state()
        self.server = create_mcp_server()
        self.load_tool = self.server._tool_manager._tools["load_from_json"].fn
        self.scale_tool = self.server._tool_manager._tools["scale_loads"].fn

        # Create test LoadSet data
        self.test_data = {
            "name": "Test LoadSet",
            "version": 1,
            "units": {"forces": "N", "moments": "Nm"},
            "load_cases": [
                {
                    "name": "Test Case",
                    "point_loads": [
                        {
                            "name": "Point 1",
                            "force_moment": {
                                "fx": 1000.0,
                                "fy": 2000.0,
                                "fz": 3000.0,
                                "mx": 100.0,
                                "my": 200.0,
                                "mz": 300.0,
                            },
                        }
                    ],
                }
            ],
        }

    def teardown_method(self):
        reset_global_state()

    def test_scale_loads_success(self):
        """Test successful load scaling."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.test_data, f)
            temp_file = f.name

        try:
            # Load the LoadSet
            load_result = self.load_tool(temp_file)
            assert load_result["success"] is True

            # Scale loads by factor of 2.0
            scale_result = self.scale_tool(2.0)

            # Verify the scaling result
            assert scale_result["success"] is True
            assert "Loads scaled by factor 2.0" in scale_result["message"]
            assert scale_result["scaling_factor"] == 2.0

        finally:
            import os

            os.unlink(temp_file)

    def test_scale_loads_no_loadset(self):
        """Test scale_loads without loading a LoadSet first."""
        result = self.scale_tool(1.5)
        assert result["success"] is False
        assert "No LoadSet loaded" in result["error"]
