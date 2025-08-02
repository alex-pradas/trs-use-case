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
            "convert_units",
            "scale_loads",
            "export_to_ansys",
            "get_load_summary",
            "list_load_cases",
            "load_second_loadset",
            "load_second_loadset_from_data",
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
            tool_func = server._tool_manager._tools["load_from_json"].fn  # type: ignore  # type: ignore

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
        tool_func = server._tool_manager._tools["load_from_json"].fn  # type: ignore

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
            tool_func = server._tool_manager._tools["load_from_json"].fn  # type: ignore  # type: ignore

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
            tool_func = server._tool_manager._tools["load_from_json"].fn  # type: ignore  # type: ignore

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
        self.load_tool = self.server._tool_manager._tools["load_from_json"].fn  # type: ignore
        self.convert_tool = self.server._tool_manager._tools["convert_units"].fn  # type: ignore

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
        self.load_tool = self.server._tool_manager._tools["load_from_json"].fn  # type: ignore
        self.scale_tool = self.server._tool_manager._tools["scale_loads"].fn  # type: ignore

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

    def test_export_to_ansys_includes_extremes(self):
        """Test that export_to_ansys includes loadset_extremes in the response."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.test_data, f)
            temp_file = f.name

        try:
            # Load the LoadSet
            load_result = self.load_tool(temp_file)
            assert load_result["success"] is True

            # Scale loads by factor of 1.5 (to match evaluation scenario)
            scale_result = self.scale_tool(1.5)
            assert scale_result["success"] is True

            # Export to ANSYS and verify extremes are included
            export_tool = self.server._tool_manager._tools["export_to_ansys"].fn  # type: ignore

            with tempfile.TemporaryDirectory() as temp_dir:
                export_result = export_tool(temp_dir, "test")

                # Verify export succeeded
                assert export_result["success"] is True
                assert "ANSYS files exported" in export_result["message"]

                # Verify loadset_extremes is included in response
                assert "loadset_extremes" in export_result
                extremes = export_result["loadset_extremes"]

                # Verify structure of extremes data
                assert isinstance(extremes, dict)
                assert "Point 1" in extremes  # Point name from test data

                point_data = extremes["Point 1"]
                assert isinstance(point_data, dict)

                # Verify components are present
                for component in ["fx", "fy", "fz", "mx", "my", "mz"]:
                    assert component in point_data

                    component_data = point_data[component]
                    assert isinstance(component_data, dict)

                    # Verify min/max structure
                    for extreme_type in ["min", "max"]:
                        if extreme_type in component_data:
                            extreme_data = component_data[extreme_type]
                            assert "value" in extreme_data
                            assert "loadcase" in extreme_data
                            assert isinstance(extreme_data["value"], (int, float))
                            assert isinstance(extreme_data["loadcase"], str)

        finally:
            import os

            os.unlink(temp_file)


class TestDataBasedMethods:
    """Test data-based LoadSet methods (load_from_data, load_second_loadset_from_data)."""

    def setup_method(self):
        """Set up test data for each test method."""
        reset_global_state()
        self.server = create_mcp_server()
        self.load_from_data_tool = self.server._tool_manager._tools["load_from_data"].fn  # type: ignore
        self.load_second_from_data_tool = self.server._tool_manager._tools[
            "load_second_loadset_from_data"
        ].fn  # type: ignore
        self.compare_tool = self.server._tool_manager._tools["compare_loadsets"].fn  # type: ignore
        self.chart_tool = self.server._tool_manager._tools[
            "generate_comparison_charts"
        ].fn  # type: ignore

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
            ].fn  # type: ignore
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
        new_loads_path = Path("use_case_definition/data/loads/03_A_new_loads.json")
        old_loads_path = Path("use_case_definition/data/loads/03_old_loads.json")

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
            file_tool = self.server._tool_manager._tools["load_from_json"].fn  # type: ignore
            file_result = file_tool(temp_file)
            assert file_result["success"] is False
            assert "error" in file_result

            # Both should fail (though error messages might be slightly different)
            # The key is that both fail appropriately

        finally:
            import os

            os.unlink(temp_file)


