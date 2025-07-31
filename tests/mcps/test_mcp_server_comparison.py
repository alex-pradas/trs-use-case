"""
Tests for MCP server comparison functionality.

This module tests the new LoadSet comparison tools added to the MCP server.
"""

import tempfile
import os
from pathlib import Path

from tools.mcps.loads_mcp_server import create_mcp_server, reset_global_state


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

        # Set up repo root for absolute paths
        self.repo_root = Path(__file__).parent.parent.parent

    def call_tool(self, tool_name: str, **kwargs):
        """Helper method to call MCP tools."""
        # Convert relative file paths to absolute paths
        if "file_path" in kwargs and not Path(kwargs["file_path"]).is_absolute():
            kwargs["file_path"] = str(self.repo_root / kwargs["file_path"])
        tool_func = self.mcp._tool_manager._tools[tool_name].fn  # type: ignore
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
            "load_from_json",
            file_path="use_case_definition/data/loads/03_A_new_loads.json",
        )
        assert result1["success"] is True

        # Then load the comparison LoadSet
        result2 = self.call_tool(
            "load_second_loadset",
            file_path="use_case_definition/data/loads/03_old_loads.json",
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
        self.call_tool(
            "load_from_json",
            file_path="use_case_definition/data/loads/03_A_new_loads.json",
        )
        self.call_tool(
            "load_second_loadset",
            file_path="use_case_definition/data/loads/03_old_loads.json",
        )

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
        self.call_tool(
            "load_from_json",
            file_path="use_case_definition/data/loads/03_A_new_loads.json",
        )

        result = self.call_tool("compare_loadsets")

        assert result["success"] is False
        assert "No comparison LoadSet loaded" in result["error"]

    def test_get_comparison_summary_success(self):
        """Test getting comparison summary."""
        # Load both LoadSets and compare
        self.call_tool(
            "load_from_json",
            file_path="use_case_definition/data/loads/03_A_new_loads.json",
        )
        self.call_tool(
            "load_second_loadset",
            file_path="use_case_definition/data/loads/03_old_loads.json",
        )
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
        self.call_tool(
            "load_from_json",
            file_path="use_case_definition/data/loads/03_A_new_loads.json",
        )
        self.call_tool(
            "load_second_loadset",
            file_path="use_case_definition/data/loads/03_old_loads.json",
        )
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
            assert "comparisons" in data

    def test_export_comparison_json_no_comparison(self):
        """Test exporting without comparison."""
        json_file = os.path.join(self.temp_dir, "comparison.json")
        result = self.call_tool("export_comparison_json", file_path=json_file)

        assert result["success"] is False
        assert "No comparison available" in result["error"]

    def test_generate_comparison_charts_as_files(self):
        """Test generating comparison charts as files."""
        # Load both LoadSets and compare
        self.call_tool(
            "load_from_json",
            file_path="use_case_definition/data/loads/03_A_new_loads.json",
        )
        self.call_tool(
            "load_second_loadset",
            file_path="use_case_definition/data/loads/03_old_loads.json",
        )
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
        self.call_tool(
            "load_from_json",
            file_path="use_case_definition/data/loads/03_A_new_loads.json",
        )
        self.call_tool(
            "load_second_loadset",
            file_path="use_case_definition/data/loads/03_old_loads.json",
        )
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
        self.call_tool(
            "load_from_json",
            file_path="use_case_definition/data/loads/03_A_new_loads.json",
        )
        self.call_tool(
            "load_second_loadset",
            file_path="use_case_definition/data/loads/03_old_loads.json",
        )
        self.call_tool("compare_loadsets")

        # Try to generate charts without output_dir
        result = self.call_tool("generate_comparison_charts", as_images=False)

        assert result["success"] is False
        assert "output_dir required when as_images=False" in result["error"]

    def test_complete_comparison_workflow(self):
        """Test complete comparison workflow."""
        # Step 1: Load primary LoadSet
        result1 = self.call_tool(
            "load_from_json",
            file_path="use_case_definition/data/loads/03_A_new_loads.json",
        )
        assert result1["success"] is True

        # Step 2: Load comparison LoadSet
        result2 = self.call_tool(
            "load_second_loadset",
            file_path="use_case_definition/data/loads/03_old_loads.json",
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
