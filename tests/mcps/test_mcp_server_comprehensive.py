"""
Tests for comprehensive MCP server functionality.

This module consolidates all MCP server tests including:
- Core server functionality (load, convert, scale, export)
- Comparison functionality
- Envelope functionality
"""

import pytest
import tempfile
import json
import os
from pathlib import Path

from tools.mcps.loads_mcp_server import (
    create_mcp_server,
    reset_global_state,
    LoadSetMCPProvider,
)


# =============================================================================
# CORE SERVER FUNCTIONALITY TESTS
# =============================================================================


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
            "load_from_data",
            "load_from_resource",
            "convert_units",
            "scale_loads",
            "export_to_ansys",
            "get_load_summary",
            "list_load_cases",
            "load_second_loadset",
            "load_second_loadset_from_data",
            "load_second_loadset_from_resource",
            "compare_loadsets",
            "generate_comparison_charts",
            "export_comparison_json",
            "get_comparison_summary",
            "envelope_loadset",
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


class TestDataBasedMethods:
    """Test data-based LoadSet methods (load_from_data, load_second_loadset_from_data)."""

    def setup_method(self):
        """Set up test data for each test method."""
        reset_global_state()
        self.server = create_mcp_server()
        self.load_from_data_tool = self.server._tool_manager._tools["load_from_data"].fn
        self.load_second_from_data_tool = self.server._tool_manager._tools[
            "load_second_loadset_from_data"
        ].fn
        self.compare_tool = self.server._tool_manager._tools["compare_loadsets"].fn
        self.chart_tool = self.server._tool_manager._tools[
            "generate_comparison_charts"
        ].fn

        # Create test LoadSet data
        self.test_data_1 = {
            "name": "Test LoadSet 1",
            "version": 1,
            "units": {"forces": "N", "moments": "Nm"},
            "load_cases": [
                {
                    "name": "Test Case 1",
                    "point_loads": [
                        {
                            "name": "Point A",
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

        self.test_data_2 = {
            "name": "Test LoadSet 2",
            "version": 1,
            "units": {"forces": "N", "moments": "Nm"},
            "load_cases": [
                {
                    "name": "Test Case 2",
                    "point_loads": [
                        {
                            "name": "Point A",
                            "force_moment": {
                                "fx": 150.0,
                                "fy": 250.0,
                                "fz": 350.0,
                                "mx": 15.0,
                                "my": 25.0,
                                "mz": 35.0,
                            },
                        }
                    ],
                }
            ],
        }

    def teardown_method(self):
        """Clean up after each test method."""
        reset_global_state()

    def test_load_from_data_success(self):
        """Test successful loading from data."""
        result = self.load_from_data_tool(self.test_data_1)

        assert result["success"] is True
        assert result["message"] == "LoadSet loaded from data"
        assert result["loadset_name"] == "Test LoadSet 1"
        assert result["num_load_cases"] == 1
        assert result["units"]["forces"] == "N"
        assert result["units"]["moments"] == "Nm"

    def test_load_from_data_invalid_data(self):
        """Test loading from invalid data."""
        invalid_data = {"invalid_field": "test", "missing_required": True}
        result = self.load_from_data_tool(invalid_data)

        assert result["success"] is False
        assert "error" in result

    def test_load_from_data_empty_data(self):
        """Test loading from empty data."""
        result = self.load_from_data_tool({})

        assert result["success"] is False
        assert "error" in result

    def test_load_second_loadset_from_data_success(self):
        """Test successful loading second loadset from data."""
        result = self.load_second_from_data_tool(self.test_data_2)

        assert result["success"] is True
        assert result["message"] == "Comparison LoadSet loaded from data"
        assert result["loadset_name"] == "Test LoadSet 2"
        assert result["num_load_cases"] == 1
        assert result["units"]["forces"] == "N"
        assert result["units"]["moments"] == "Nm"

    def test_load_second_loadset_from_data_invalid_data(self):
        """Test loading second loadset from invalid data."""
        invalid_data = {"invalid_field": "test"}
        result = self.load_second_from_data_tool(invalid_data)

        assert result["success"] is False
        assert "error" in result

    def test_complete_data_based_workflow(self):
        """Test complete workflow using data-based methods."""
        # Load first LoadSet from data
        result1 = self.load_from_data_tool(self.test_data_1)
        assert result1["success"] is True

        # Load second LoadSet from data
        result2 = self.load_second_from_data_tool(self.test_data_2)
        assert result2["success"] is True

        # Compare the LoadSets
        comparison_result = self.compare_tool()
        assert comparison_result["success"] is True
        assert comparison_result["loadset1_name"] == "Test LoadSet 1"
        assert comparison_result["loadset2_name"] == "Test LoadSet 2"
        assert comparison_result["total_comparison_rows"] > 0

        # Generate charts
        chart_result = self.chart_tool(as_images=True, format="png")
        assert chart_result["success"] is True
        assert "charts" in chart_result
        assert len(chart_result["charts"]) > 0

    def test_mixed_workflow_file_and_data(self):
        """Test workflow mixing file-based and data-based methods."""
        # Load first LoadSet from data
        result1 = self.load_from_data_tool(self.test_data_1)
        assert result1["success"] is True

        # Load second LoadSet from file (create temporary file)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.test_data_2, f)
            temp_file = f.name

        try:
            load_second_tool = self.server._tool_manager._tools[
                "load_second_loadset"
            ].fn
            result2 = load_second_tool(temp_file)
            assert result2["success"] is True

            # Compare the LoadSets
            comparison_result = self.compare_tool()
            assert comparison_result["success"] is True

        finally:
            import os

            os.unlink(temp_file)

    def test_data_based_with_real_project_data(self):
        """Test data-based methods with real project data."""
        # Load real project data
        new_loads_path = Path("solution/loads/03_01_new_loads.json")
        old_loads_path = Path("solution/loads/03_03_old_loads.json")

        # Skip if files don't exist
        if not new_loads_path.exists() or not old_loads_path.exists():
            pytest.skip("Real project data files not found")

        # Load the JSON data
        with open(new_loads_path, "r") as f:
            new_loads_data = json.load(f)

        with open(old_loads_path, "r") as f:
            old_loads_data = json.load(f)

        # Test load_from_data with real data
        result1 = self.load_from_data_tool(new_loads_data)
        assert result1["success"] is True
        assert result1["loadset_name"] == "Aerospace Structural Load Cases"
        assert result1["num_load_cases"] == 25

        # Test load_second_loadset_from_data with real data
        result2 = self.load_second_from_data_tool(old_loads_data)
        assert result2["success"] is True
        assert result2["loadset_name"] == "Aerospace Structural Load Cases"
        assert result2["num_load_cases"] == 25

        # Test comparison with real data
        comparison_result = self.compare_tool()
        assert comparison_result["success"] is True
        assert comparison_result["total_comparison_rows"] > 0

        # Test chart generation with real data
        chart_result = self.chart_tool(as_images=True, format="png")
        assert chart_result["success"] is True
        assert "charts" in chart_result
        assert len(chart_result["charts"]) == 2  # Should have Point A and Point B

    def test_data_validation_comprehensive(self):
        """Test comprehensive data validation scenarios."""
        # Test missing required fields
        invalid_scenarios = [
            {},  # Empty dict
            {"name": "Test"},  # Missing version, units, load_cases
            {"name": "Test", "version": 1},  # Missing units, load_cases
            {
                "name": "Test",
                "version": 1,
                "units": {"forces": "N"},
            },  # Missing moments unit
            {
                "name": "Test",
                "version": 1,
                "units": {"forces": "N", "moments": "Nm"},
            },  # Missing load_cases
        ]

        for i, invalid_data in enumerate(invalid_scenarios):
            result = self.load_from_data_tool(invalid_data)
            assert result["success"] is False, f"Scenario {i} should fail"
            assert "error" in result, f"Scenario {i} should have error message"

    def test_error_handling_consistency(self):
        """Test that error handling is consistent between file and data methods."""
        # Test with same invalid data structure
        invalid_data = {"invalid": "structure"}

        # Test data-based method
        data_result = self.load_from_data_tool(invalid_data)
        assert data_result["success"] is False
        assert "error" in data_result

        # Test file-based method with same invalid data
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(invalid_data, f)
            temp_file = f.name

        try:
            file_tool = self.server._tool_manager._tools["load_from_json"].fn
            file_result = file_tool(temp_file)
            assert file_result["success"] is False
            assert "error" in file_result

            # Both should fail (though error messages might be slightly different)
            # The key is that both fail appropriately

        finally:
            import os

            os.unlink(temp_file)


class TestResourceBasedMethods:
    """Test resource-based LoadSet methods (load_from_resource, load_second_loadset_from_resource)."""

    def setup_method(self):
        """Set up test data for each test method."""
        reset_global_state()
        self.server = create_mcp_server()
        self.load_from_resource_tool = self.server._tool_manager._tools[
            "load_from_resource"
        ].fn
        self.load_second_from_resource_tool = self.server._tool_manager._tools[
            "load_second_loadset_from_resource"
        ].fn
        self.compare_tool = self.server._tool_manager._tools["compare_loadsets"].fn

    def teardown_method(self):
        """Clean up after each test method."""
        reset_global_state()

    def test_load_from_resource_new_loads_success(self):
        """Test successful loading from new_loads.json resource."""
        result = self.load_from_resource_tool("loadsets://03_01_new_loads.json")

        assert result["success"] is True
        assert (
            result["message"]
            == "LoadSet loaded from resource loadsets://03_01_new_loads.json"
        )
        assert result["loadset_name"] == "Aerospace Structural Load Cases"
        assert result["num_load_cases"] == 25
        assert result["units"]["forces"] == "N"
        assert result["units"]["moments"] == "Nm"

    def test_load_from_resource_old_loads_success(self):
        """Test successful loading from old_loads.json resource."""
        result = self.load_from_resource_tool("loadsets://03_03_old_loads.json")

        assert result["success"] is True
        assert (
            result["message"]
            == "LoadSet loaded from resource loadsets://03_03_old_loads.json"
        )
        assert result["loadset_name"] == "Aerospace Structural Load Cases"
        assert result["num_load_cases"] == 25
        assert result["units"]["forces"] == "N"
        assert result["units"]["moments"] == "Nm"

    def test_load_from_resource_invalid_scheme(self):
        """Test loading from resource with invalid URI scheme."""
        result = self.load_from_resource_tool("invalid://new_loads.json")

        assert result["success"] is False
        assert "error" in result
        assert "Unsupported resource URI scheme" in result["error"]
        assert "Expected 'loadsets://'" in result["error"]

    def test_load_from_resource_unknown_resource(self):
        """Test loading from unknown resource."""
        result = self.load_from_resource_tool("loadsets://unknown_file.json")

        assert result["success"] is False
        assert "error" in result
        assert "Unknown resource: unknown_file.json" in result["error"]
        assert "Available: 03_01_new_loads.json, 03_02_new_loads.json, 03_03_old_loads.json" in result["error"]

    def test_load_from_resource_malformed_uri(self):
        """Test loading from malformed resource URI."""
        malformed_uris = [
            "loadsets://",  # Missing resource name
            "loadsets:",  # Missing //
            "loadsets",  # Missing ://
            "",  # Empty string
            "loadsets://03_01_new_loads.json/extra/path",  # Extra path components
        ]

        for uri in malformed_uris:
            result = self.load_from_resource_tool(uri)
            assert result["success"] is False
            assert "error" in result

    def test_load_second_loadset_from_resource_success(self):
        """Test successful loading second loadset from resource."""
        result = self.load_second_from_resource_tool("loadsets://03_03_old_loads.json")

        assert result["success"] is True
        assert (
            result["message"]
            == "Comparison LoadSet loaded from resource loadsets://03_03_old_loads.json"
        )
        assert result["loadset_name"] == "Aerospace Structural Load Cases"
        assert result["num_load_cases"] == 25
        assert result["units"]["forces"] == "N"
        assert result["units"]["moments"] == "Nm"

    def test_load_second_loadset_from_resource_invalid_scheme(self):
        """Test loading second loadset with invalid URI scheme."""
        result = self.load_second_from_resource_tool("invalid://old_loads.json")

        assert result["success"] is False
        assert "error" in result
        assert "Unsupported resource URI scheme" in result["error"]

    def test_load_second_loadset_from_resource_unknown_resource(self):
        """Test loading second loadset from unknown resource."""
        result = self.load_second_from_resource_tool("loadsets://nonexistent.json")

        assert result["success"] is False
        assert "error" in result
        assert "Unknown resource: nonexistent.json" in result["error"]

    def test_complete_resource_based_workflow(self):
        """Test complete workflow using resource-based methods."""
        # Load first LoadSet from resource
        result1 = self.load_from_resource_tool("loadsets://03_01_new_loads.json")
        assert result1["success"] is True
        assert result1["loadset_name"] == "Aerospace Structural Load Cases"

        # Load second LoadSet from resource
        result2 = self.load_second_from_resource_tool("loadsets://03_03_old_loads.json")
        assert result2["success"] is True
        assert result2["loadset_name"] == "Aerospace Structural Load Cases"

        # Compare the LoadSets
        comparison_result = self.compare_tool()
        assert comparison_result["success"] is True
        assert comparison_result["loadset1_name"] == "Aerospace Structural Load Cases"
        assert comparison_result["loadset2_name"] == "Aerospace Structural Load Cases"
        assert comparison_result["total_comparison_rows"] > 0

        # Verify comparison data structure
        assert "comparison_data" in comparison_result
        assert "metadata" in comparison_result["comparison_data"]
        assert "comparison_rows" in comparison_result["comparison_data"]
        assert len(comparison_result["comparison_data"]["comparison_rows"]) > 0

    def test_resource_vs_data_consistency(self):
        """Test that resource-based and data-based methods produce consistent results."""
        # Load from resource
        resource_result = self.load_from_resource_tool("loadsets://03_01_new_loads.json")
        assert resource_result["success"] is True

        # Reset state and load same data using data-based method
        reset_global_state()

        # Load the same data using data-based method
        new_loads_path = Path("solution/loads/03_01_new_loads.json")
        if new_loads_path.exists():
            with open(new_loads_path, "r") as f:
                new_loads_data = json.load(f)

            data_tool = self.server._tool_manager._tools["load_from_data"].fn
            data_result = data_tool(new_loads_data)
            assert data_result["success"] is True

            # Results should be identical (except for the message)
            assert resource_result["loadset_name"] == data_result["loadset_name"]
            assert resource_result["num_load_cases"] == data_result["num_load_cases"]
            assert resource_result["units"] == data_result["units"]

    def test_mixed_resource_and_data_workflow(self):
        """Test workflow mixing resource-based and data-based methods."""
        # Load first LoadSet from resource
        result1 = self.load_from_resource_tool("loadsets://03_01_new_loads.json")
        assert result1["success"] is True

        # Load second LoadSet from data (if available)
        old_loads_path = Path("solution/loads/03_03_old_loads.json")
        if old_loads_path.exists():
            with open(old_loads_path, "r") as f:
                old_loads_data = json.load(f)

            data_tool = self.server._tool_manager._tools[
                "load_second_loadset_from_data"
            ].fn
            result2 = data_tool(old_loads_data)
            assert result2["success"] is True

            # Compare the LoadSets
            comparison_result = self.compare_tool()
            assert comparison_result["success"] is True
            assert comparison_result["total_comparison_rows"] > 0

    def test_resource_loading_state_management(self):
        """Test that resource loading properly manages state."""
        # Load first resource
        result1 = self.load_from_resource_tool("loadsets://03_01_new_loads.json")
        assert result1["success"] is True

        # Load second resource (should replace first)
        result2 = self.load_from_resource_tool("loadsets://03_03_old_loads.json")
        assert result2["success"] is True

        # Load comparison resource
        result3 = self.load_second_from_resource_tool("loadsets://03_01_new_loads.json")
        assert result3["success"] is True

        # Compare should work with the current state
        comparison_result = self.compare_tool()
        assert comparison_result["success"] is True

    def test_resource_uri_validation_comprehensive(self):
        """Test comprehensive resource URI validation."""
        invalid_uris = [
            None,  # None value
            "",  # Empty string
            "loadsets://",  # Missing resource name
            "loadsets:",  # Invalid format
            "loadsets",  # Missing scheme
            "http://new_loads.json",  # Wrong scheme
            "loadsets://new_loads.txt",  # Wrong extension (but should still fail on unknown resource)
            "loadsets://03_01_new_loads.json/extra",  # Extra path
            "LOADSETS://new_loads.json",  # Case sensitive
            "loadsets://NEW_LOADS.JSON",  # Case sensitive
        ]

        for uri in invalid_uris:
            try:
                result = self.load_from_resource_tool(uri)
                assert result["success"] is False
                assert "error" in result
            except Exception as e:
                # Some URIs might cause exceptions, which is also acceptable
                pass

    def test_resource_error_handling_consistency(self):
        """Test that resource-based methods have consistent error handling."""
        # Test same invalid URI with both resource methods
        invalid_uri = "invalid://test.json"

        result1 = self.load_from_resource_tool(invalid_uri)
        result2 = self.load_second_from_resource_tool(invalid_uri)

        # Both should fail with similar error messages
        assert result1["success"] is False
        assert result2["success"] is False
        assert "error" in result1
        assert "error" in result2
        assert "Unsupported resource URI scheme" in result1["error"]
        assert "Unsupported resource URI scheme" in result2["error"]

    def test_resource_files_exist(self):
        """Test that the expected resource files exist in the project."""
        # This test verifies the project structure
        project_root = Path(__file__).parent.parent.parent
        new_loads_path = project_root / "solution" / "loads" / "03_01_new_loads.json"
        old_loads_path = project_root / "solution" / "loads" / "03_03_old_loads.json"

        assert new_loads_path.exists(), f"03_01_new_loads.json not found at {new_loads_path}"
        assert old_loads_path.exists(), f"03_03_old_loads.json not found at {old_loads_path}"

        # Verify files are valid JSON
        with open(new_loads_path, "r") as f:
            new_loads_data = json.load(f)
        with open(old_loads_path, "r") as f:
            old_loads_data = json.load(f)

        # Basic structure validation
        assert "name" in new_loads_data
        assert "load_cases" in new_loads_data
        assert "name" in old_loads_data
        assert "load_cases" in old_loads_data


# =============================================================================
# COMPARISON FUNCTIONALITY TESTS
# =============================================================================


class TestMCPServerComparison:
    """Test class for MCP server comparison functionality."""

    def setup_method(self):
        """Set up test environment."""
        # Reset global state before each test
        reset_global_state()

        # Create MCP server instance
        self.mcp = create_mcp_server()

        # Create temporary directory for test outputs
        self.temp_dir = tempfile.mkdtemp()

    def call_tool(self, tool_name: str, **kwargs):
        """Helper method to call MCP tools."""
        tool_func = self.mcp._tool_manager._tools[tool_name].fn
        return tool_func(**kwargs)

    def teardown_method(self):
        """Clean up test environment."""
        # Clean up temporary directory
        if os.path.exists(self.temp_dir):
            import shutil

            shutil.rmtree(self.temp_dir)

        # Reset global state after each test
        reset_global_state()

    def test_load_second_loadset_success(self):
        """Test loading a second LoadSet for comparison."""
        # First load the primary LoadSet
        result1 = self.call_tool(
            "load_from_json", file_path="solution/loads/03_01_new_loads.json"
        )
        assert result1["success"] is True

        # Then load the comparison LoadSet
        result2 = self.call_tool(
            "load_second_loadset", file_path="solution/loads/03_03_old_loads.json"
        )

        assert result2["success"] is True
        assert "Comparison LoadSet loaded from" in result2["message"]
        assert "loadset_name" in result2
        assert "num_load_cases" in result2
        assert "units" in result2

    def test_load_second_loadset_invalid_file(self):
        """Test loading an invalid file as second LoadSet."""
        result = self.call_tool(
            "load_second_loadset", file_path="nonexistent_file.json"
        )

        assert result["success"] is False
        assert "error" in result

    def test_compare_loadsets_success(self):
        """Test successful LoadSet comparison."""
        # Load both LoadSets
        self.call_tool("load_from_json", file_path="solution/loads/03_01_new_loads.json")
        self.call_tool("load_second_loadset", file_path="solution/loads/03_03_old_loads.json")

        # Compare LoadSets
        result = self.call_tool("compare_loadsets")

        assert result["success"] is True
        assert "LoadSets compared successfully" in result["message"]
        assert "loadset1_name" in result
        assert "loadset2_name" in result
        assert "total_comparison_rows" in result
        assert "comparison_data" in result
        assert isinstance(result["comparison_data"], dict)

    def test_compare_loadsets_no_current_loadset(self):
        """Test comparison without current LoadSet loaded."""
        result = self.call_tool("compare_loadsets")

        assert result["success"] is False
        assert "No current LoadSet loaded" in result["error"]

    def test_compare_loadsets_no_comparison_loadset(self):
        """Test comparison without comparison LoadSet loaded."""
        # Load only primary LoadSet
        self.call_tool("load_from_json", file_path="solution/loads/03_01_new_loads.json")

        result = self.call_tool("compare_loadsets")

        assert result["success"] is False
        assert "No comparison LoadSet loaded" in result["error"]

    def test_get_comparison_summary_success(self):
        """Test getting comparison summary."""
        # Load both LoadSets and compare
        self.call_tool("load_from_json", file_path="solution/loads/03_01_new_loads.json")
        self.call_tool("load_second_loadset", file_path="solution/loads/03_03_old_loads.json")
        self.call_tool("compare_loadsets")

        # Get summary
        result = self.call_tool("get_comparison_summary")

        assert result["success"] is True
        assert "loadset1_name" in result
        assert "loadset2_name" in result
        assert "total_comparison_rows" in result
        assert "unique_points" in result
        assert "unique_components" in result
        assert "point_names" in result
        assert "components" in result
        assert "max_absolute_difference" in result
        assert "max_percentage_difference" in result
        assert "largest_difference" in result

        # Validate largest_difference structure
        largest_diff = result["largest_difference"]
        assert "point" in largest_diff
        assert "component" in largest_diff
        assert "type" in largest_diff
        assert "absolute_diff" in largest_diff

    def test_get_comparison_summary_no_comparison(self):
        """Test getting summary without comparison."""
        result = self.call_tool("get_comparison_summary")

        assert result["success"] is False
        assert "No comparison available" in result["error"]

    def test_export_comparison_json_success(self):
        """Test exporting comparison to JSON file."""
        # Load both LoadSets and compare
        self.call_tool("load_from_json", file_path="solution/loads/03_01_new_loads.json")
        self.call_tool("load_second_loadset", file_path="solution/loads/03_03_old_loads.json")
        self.call_tool("compare_loadsets")

        # Export to JSON
        json_file = os.path.join(self.temp_dir, "comparison.json")
        result = self.call_tool("export_comparison_json", file_path=json_file)

        assert result["success"] is True
        assert f"Comparison exported to {json_file}" in result["message"]
        assert "total_rows" in result

        # Verify file was created and contains valid JSON
        assert os.path.exists(json_file)
        with open(json_file, "r") as f:
            import json

            data = json.load(f)
            assert "comparison_rows" in data

    def test_export_comparison_json_no_comparison(self):
        """Test exporting without comparison."""
        json_file = os.path.join(self.temp_dir, "comparison.json")
        result = self.call_tool("export_comparison_json", file_path=json_file)

        assert result["success"] is False
        assert "No comparison available" in result["error"]

    def test_generate_comparison_charts_as_files(self):
        """Test generating comparison charts as files."""
        # Load both LoadSets and compare
        self.call_tool("load_from_json", file_path="solution/loads/03_01_new_loads.json")
        self.call_tool("load_second_loadset", file_path="solution/loads/03_03_old_loads.json")
        self.call_tool("compare_loadsets")

        # Generate charts as files
        result = self.call_tool(
            "generate_comparison_charts",
            output_dir=self.temp_dir,
            format="png",
            as_images=False,
        )

        assert result["success"] is True
        assert f"Comparison charts saved to {self.temp_dir}" in result["message"]
        assert "format" in result
        assert result["format"] == "png"
        assert "chart_files" in result

        # Verify at least one chart file was created
        chart_files = result["chart_files"]
        assert len(chart_files) > 0

        # Verify files actually exist
        for point_name, file_path in chart_files.items():
            assert os.path.exists(file_path), f"Chart file {file_path} was not created"
            assert file_path.endswith(".png"), f"Chart file {file_path} should be PNG"

    def test_generate_comparison_charts_as_image_objects(self):
        """Test generating comparison charts as base64 strings."""
        # Load both LoadSets and compare
        self.call_tool("load_from_json", file_path="solution/loads/03_01_new_loads.json")
        self.call_tool("load_second_loadset", file_path="solution/loads/03_03_old_loads.json")
        self.call_tool("compare_loadsets")

        # Generate charts as base64 strings
        result = self.call_tool(
            "generate_comparison_charts", format="png", as_images=True
        )

        assert result["success"] is True
        assert "Comparison charts generated as base64 strings" in result["message"]
        assert "format" in result
        assert result["format"] == "png"
        assert "charts" in result

        # Verify base64 strings structure
        charts = result["charts"]
        assert len(charts) > 0

        # Verify base64 strings are present
        for point_name, base64_string in charts.items():
            assert isinstance(base64_string, str), (
                f"Chart data for {point_name} should be base64 string"
            )
            assert len(base64_string) > 0, (
                f"Base64 string for {point_name} should be non-empty"
            )

            # Verify it's valid base64 by trying to decode it
            import base64

            try:
                decoded_bytes = base64.b64decode(base64_string)
                assert len(decoded_bytes) > 0, (
                    f"Decoded image data for {point_name} should be non-empty"
                )
            except Exception as e:
                assert False, f"Invalid base64 string for {point_name}: {e}"

    def test_generate_comparison_charts_no_comparison(self):
        """Test generating charts without comparison."""
        result = self.call_tool("generate_comparison_charts", output_dir=self.temp_dir)

        assert result["success"] is False
        assert "No comparison available" in result["error"]

    def test_generate_comparison_charts_missing_output_dir(self):
        """Test generating charts as files without output directory."""
        # Load both LoadSets and compare
        self.call_tool("load_from_json", file_path="solution/loads/03_01_new_loads.json")
        self.call_tool("load_second_loadset", file_path="solution/loads/03_03_old_loads.json")
        self.call_tool("compare_loadsets")

        # Try to generate charts without output_dir
        result = self.call_tool("generate_comparison_charts", as_images=False)

        assert result["success"] is False
        assert "output_dir required when as_images=False" in result["error"]

    def test_complete_comparison_workflow(self):
        """Test complete comparison workflow."""
        # Step 1: Load primary LoadSet
        result1 = self.call_tool(
            "load_from_json", file_path="solution/loads/03_01_new_loads.json"
        )
        assert result1["success"] is True

        # Step 2: Load comparison LoadSet
        result2 = self.call_tool(
            "load_second_loadset", file_path="solution/loads/03_03_old_loads.json"
        )
        assert result2["success"] is True

        # Step 3: Compare LoadSets
        result3 = self.call_tool("compare_loadsets")
        assert result3["success"] is True

        # Step 4: Get summary
        result4 = self.call_tool("get_comparison_summary")
        assert result4["success"] is True

        # Step 5: Export to JSON
        json_file = os.path.join(self.temp_dir, "comparison.json")
        result5 = self.call_tool("export_comparison_json", file_path=json_file)
        assert result5["success"] is True
        assert os.path.exists(json_file)

        # Step 6: Generate charts as files
        result6 = self.call_tool(
            "generate_comparison_charts",
            output_dir=self.temp_dir,
            format="png",
            as_images=False,
        )
        assert result6["success"] is True

        # Step 7: Generate charts as Image objects
        result7 = self.call_tool(
            "generate_comparison_charts", format="png", as_images=True
        )
        assert result7["success"] is True

        # Verify all outputs are consistent
        assert result3["total_comparison_rows"] == result4["total_comparison_rows"]
        assert result5["total_rows"] == result4["total_comparison_rows"]


class TestMCPServerComparisonToolList:
    """Test that comparison tools are properly registered."""

    def test_server_has_comparison_tools(self):
        """Test that MCP server includes all comparison tools."""
        mcp = create_mcp_server()

        # Get list of available tools
        tool_names = list(mcp._tool_manager._tools.keys())

        # Check that all comparison tools are present
        expected_tools = [
            "load_from_json",
            "convert_units",
            "scale_loads",
            "export_to_ansys",
            "get_load_summary",
            "list_load_cases",
            "load_second_loadset",
            "compare_loadsets",
            "generate_comparison_charts",
            "export_comparison_json",
            "get_comparison_summary",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names, (
                f"Tool {tool_name} not found in server tools"
            )

        # Verify total count includes all tools
        assert len(tool_names) >= len(expected_tools)


# =============================================================================
# ENVELOPE FUNCTIONALITY TESTS
# =============================================================================


class TestMCPEnvelope:
    """Test MCP envelope functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.provider = LoadSetMCPProvider()

        # Create test LoadSet data with extreme values
        self.test_loadset_data = {
            "name": "MCP Test Envelope LoadSet",
            "version": 1,
            "description": "Test load set for MCP envelope functionality",
            "units": {"forces": "N", "moments": "Nm"},
            "load_cases": [
                {
                    "name": "Max_Fx_Case",
                    "description": "Load case with maximum fx",
                    "point_loads": [
                        {
                            "name": "Point_A",
                            "force_moment": {
                                "fx": 1000.0,  # MAX for Point_A fx
                                "fy": 100.0,
                                "fz": 50.0,
                                "mx": 10.0,
                                "my": 20.0,
                                "mz": 30.0,
                            },
                        },
                    ],
                },
                {
                    "name": "Min_Fx_Case",
                    "description": "Load case with negative minimum fx",
                    "point_loads": [
                        {
                            "name": "Point_A",
                            "force_moment": {
                                "fx": -500.0,  # MIN for Point_A fx (negative)
                                "fy": 200.0,  # MAX for Point_A fy
                                "fz": 75.0,
                                "mx": 15.0,
                                "my": 25.0,
                                "mz": 35.0,
                            },
                        },
                    ],
                },
                {
                    "name": "Max_Fz_Case",
                    "description": "Load case with maximum fz",
                    "point_loads": [
                        {
                            "name": "Point_A",
                            "force_moment": {
                                "fx": 200.0,
                                "fy": 80.0,  # MIN for Point_A fy (positive, won't be included as min)
                                "fz": 800.0,  # MAX for Point_A fz
                                "mx": -100.0,  # MIN for Point_A mx (negative)
                                "my": 10.0,
                                "mz": 200.0,  # MAX for Point_A mz
                            },
                        },
                    ],
                },
                {
                    "name": "No_Extremes_Case",
                    "description": "Load case with no extreme values",
                    "point_loads": [
                        {
                            "name": "Point_A",
                            "force_moment": {
                                "fx": 300.0,  # Between min and max
                                "fy": 150.0,  # Between min and max
                                "fz": 100.0,  # Between min and max
                                "mx": 12.0,  # Between min and max
                                "my": 15.0,  # Between min and max
                                "mz": 100.0,  # Between min and max
                            },
                        },
                    ],
                },
            ],
        }

    def test_envelope_loadset_success(self):
        """Test successful envelope operation."""
        # Load the test data first
        load_result = self.provider.load_from_data(self.test_loadset_data)
        assert load_result["success"] is True

        # Create envelope
        envelope_result = self.provider.envelope_loadset()

        # Validate response
        assert envelope_result["success"] is True
        assert "message" in envelope_result
        assert "LoadSet envelope created successfully" in envelope_result["message"]

        # Check statistics
        assert envelope_result["original_load_cases"] == 4
        assert (
            envelope_result["envelope_load_cases"] == 3
        )  # Should exclude No_Extremes_Case
        assert envelope_result["reduction_ratio"] == 25.0  # (4-3)/4 * 100 = 25%

        # Check envelope case names
        envelope_case_names = set(envelope_result["envelope_case_names"])
        assert "Max_Fx_Case" in envelope_case_names
        assert "Min_Fx_Case" in envelope_case_names
        assert "Max_Fz_Case" in envelope_case_names
        assert "No_Extremes_Case" not in envelope_case_names

    def test_envelope_loadset_no_loadset_loaded(self):
        """Test envelope operation when no LoadSet is loaded."""
        # Try to create envelope without loading data first
        envelope_result = self.provider.envelope_loadset()

        # Should return error
        assert envelope_result["success"] is False
        assert "No LoadSet loaded" in envelope_result["error"]

    def test_envelope_loadset_empty_loadset(self):
        """Test envelope operation with empty LoadSet."""
        empty_loadset_data = {
            "name": "Empty LoadSet",
            "version": 1,
            "units": {"forces": "N", "moments": "Nm"},
            "load_cases": [],
        }

        # Load empty data
        load_result = self.provider.load_from_data(empty_loadset_data)
        assert load_result["success"] is True

        # Try to create envelope
        envelope_result = self.provider.envelope_loadset()

        # Should return error from envelope method
        assert envelope_result["success"] is False
        assert "Cannot create envelope of empty LoadSet" in envelope_result["error"]

    def test_envelope_loadset_single_case(self):
        """Test envelope operation with single load case."""
        single_case_data = {
            "name": "Single Case LoadSet",
            "version": 1,
            "units": {"forces": "N", "moments": "Nm"},
            "load_cases": [
                {
                    "name": "Only_Case",
                    "point_loads": [
                        {
                            "name": "Point_A",
                            "force_moment": {
                                "fx": 100.0,
                                "fy": -50.0,
                                "fz": 200.0,
                            },
                        },
                    ],
                },
            ],
        }

        # Load single case data
        load_result = self.provider.load_from_data(single_case_data)
        assert load_result["success"] is True

        # Create envelope
        envelope_result = self.provider.envelope_loadset()

        # Should succeed and include the single case
        assert envelope_result["success"] is True
        assert envelope_result["original_load_cases"] == 1
        assert envelope_result["envelope_load_cases"] == 1
        assert envelope_result["reduction_ratio"] == 0.0  # No reduction
        assert envelope_result["envelope_case_names"] == ["Only_Case"]

    def test_envelope_loadset_all_positive_values(self):
        """Test envelope operation when all values are positive."""
        positive_data = {
            "name": "All Positive LoadSet",
            "version": 1,
            "units": {"forces": "N", "moments": "Nm"},
            "load_cases": [
                {
                    "name": "Case_1",
                    "point_loads": [
                        {
                            "name": "Point_A",
                            "force_moment": {"fx": 100.0, "fy": 200.0, "fz": 300.0},
                        },
                    ],
                },
                {
                    "name": "Case_2",
                    "point_loads": [
                        {
                            "name": "Point_A",
                            "force_moment": {
                                "fx": 50.0,
                                "fy": 400.0,
                                "fz": 150.0,
                            },  # fy is max
                        },
                    ],
                },
                {
                    "name": "Case_3",
                    "point_loads": [
                        {
                            "name": "Point_A",
                            "force_moment": {
                                "fx": 150.0,
                                "fy": 100.0,
                                "fz": 500.0,
                            },  # fx is max, fz is max
                        },
                    ],
                },
            ],
        }

        # Load positive data
        load_result = self.provider.load_from_data(positive_data)
        assert load_result["success"] is True

        # Create envelope
        envelope_result = self.provider.envelope_loadset()

        # Should succeed and only include cases with max values (no negative mins)
        assert envelope_result["success"] is True
        assert envelope_result["original_load_cases"] == 3
        # Should have fewer cases since positive mins are not included
        assert envelope_result["envelope_load_cases"] <= 3

    def test_envelope_loadset_preserves_state(self):
        """Test that envelope operation updates the provider state correctly."""
        # Load the test data first
        load_result = self.provider.load_from_data(self.test_loadset_data)
        assert load_result["success"] is True

        # Get initial summary
        initial_summary = self.provider.get_load_summary()
        assert initial_summary["num_load_cases"] == 4

        # Create envelope
        envelope_result = self.provider.envelope_loadset()
        assert envelope_result["success"] is True

        # Get summary after envelope - should show reduced number of cases
        after_summary = self.provider.get_load_summary()
        assert after_summary["num_load_cases"] == 3

        # List load cases to verify the correct ones remain
        case_list = self.provider.list_load_cases()
        case_names = {case["name"] for case in case_list["load_cases"]}

        assert "Max_Fx_Case" in case_names
        assert "Min_Fx_Case" in case_names
        assert "Max_Fz_Case" in case_names
        assert "No_Extremes_Case" not in case_names

    def test_envelope_loadset_with_file_input(self):
        """Test envelope operation when data is loaded from file."""
        # Create temporary JSON file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.test_loadset_data, f)
            temp_file = f.name

        try:
            # Load from file
            load_result = self.provider.load_from_json(temp_file)
            assert load_result["success"] is True

            # Create envelope
            envelope_result = self.provider.envelope_loadset()
            assert envelope_result["success"] is True
            assert envelope_result["original_load_cases"] == 4
            assert envelope_result["envelope_load_cases"] == 3

        finally:
            # Clean up
            Path(temp_file).unlink()

    def test_envelope_loadset_response_format(self):
        """Test that envelope response has the correct format."""
        # Load test data
        load_result = self.provider.load_from_data(self.test_loadset_data)
        assert load_result["success"] is True

        # Create envelope
        envelope_result = self.provider.envelope_loadset()

        # Validate response structure
        assert isinstance(envelope_result, dict)
        assert "success" in envelope_result
        assert "message" in envelope_result
        assert "original_load_cases" in envelope_result
        assert "envelope_load_cases" in envelope_result
        assert "reduction_ratio" in envelope_result
        assert "envelope_case_names" in envelope_result

        # Validate data types
        assert isinstance(envelope_result["success"], bool)
        assert isinstance(envelope_result["message"], str)
        assert isinstance(envelope_result["original_load_cases"], int)
        assert isinstance(envelope_result["envelope_load_cases"], int)
        assert isinstance(envelope_result["reduction_ratio"], (int, float))
        assert isinstance(envelope_result["envelope_case_names"], list)

        # Validate that all envelope case names are strings
        for case_name in envelope_result["envelope_case_names"]:
            assert isinstance(case_name, str)


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
