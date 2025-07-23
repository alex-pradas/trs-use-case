"""
Tests for MCP server envelope functionality.

This module tests the envelope tool in the LoadSet MCP server.
"""

import pytest
import tempfile
import json
from pathlib import Path

from tools.mcps.loads_mcp_server import LoadSetMCPProvider  # noqa: E402
from tools.loads import LoadSet, Units, LoadCase, PointLoad, ForceMoment  # noqa: E402


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
