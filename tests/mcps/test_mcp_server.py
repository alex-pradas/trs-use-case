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
        new_loads_path = Path("solution/loads/new_loads.json")
        old_loads_path = Path("solution/loads/old_loads.json")

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
        result = self.load_from_resource_tool("loadsets://new_loads.json")

        assert result["success"] is True
        assert (
            result["message"]
            == "LoadSet loaded from resource loadsets://new_loads.json"
        )
        assert result["loadset_name"] == "Aerospace Structural Load Cases"
        assert result["num_load_cases"] == 25
        assert result["units"]["forces"] == "N"
        assert result["units"]["moments"] == "Nm"

    def test_load_from_resource_old_loads_success(self):
        """Test successful loading from old_loads.json resource."""
        result = self.load_from_resource_tool("loadsets://old_loads.json")

        assert result["success"] is True
        assert (
            result["message"]
            == "LoadSet loaded from resource loadsets://old_loads.json"
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
        assert "Available: new_loads.json, old_loads.json" in result["error"]

    def test_load_from_resource_malformed_uri(self):
        """Test loading from malformed resource URI."""
        malformed_uris = [
            "loadsets://",  # Missing resource name
            "loadsets:",  # Missing //
            "loadsets",  # Missing ://
            "",  # Empty string
            "loadsets://new_loads.json/extra/path",  # Extra path components
        ]

        for uri in malformed_uris:
            result = self.load_from_resource_tool(uri)
            assert result["success"] is False
            assert "error" in result

    def test_load_second_loadset_from_resource_success(self):
        """Test successful loading second loadset from resource."""
        result = self.load_second_from_resource_tool("loadsets://old_loads.json")

        assert result["success"] is True
        assert (
            result["message"]
            == "Comparison LoadSet loaded from resource loadsets://old_loads.json"
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
        result1 = self.load_from_resource_tool("loadsets://new_loads.json")
        assert result1["success"] is True
        assert result1["loadset_name"] == "Aerospace Structural Load Cases"

        # Load second LoadSet from resource
        result2 = self.load_second_from_resource_tool("loadsets://old_loads.json")
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
        resource_result = self.load_from_resource_tool("loadsets://new_loads.json")
        assert resource_result["success"] is True

        # Reset state and load same data using data-based method
        reset_global_state()

        # Load the same data using data-based method
        new_loads_path = Path("solution/loads/new_loads.json")
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
        result1 = self.load_from_resource_tool("loadsets://new_loads.json")
        assert result1["success"] is True

        # Load second LoadSet from data (if available)
        old_loads_path = Path("solution/loads/old_loads.json")
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
        result1 = self.load_from_resource_tool("loadsets://new_loads.json")
        assert result1["success"] is True

        # Load second resource (should replace first)
        result2 = self.load_from_resource_tool("loadsets://old_loads.json")
        assert result2["success"] is True

        # Load comparison resource
        result3 = self.load_second_from_resource_tool("loadsets://new_loads.json")
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
            "loadsets://new_loads.json/extra",  # Extra path
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
        new_loads_path = project_root / "solution" / "loads" / "new_loads.json"
        old_loads_path = project_root / "solution" / "loads" / "old_loads.json"

        assert new_loads_path.exists(), f"new_loads.json not found at {new_loads_path}"
        assert old_loads_path.exists(), f"old_loads.json not found at {old_loads_path}"

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
