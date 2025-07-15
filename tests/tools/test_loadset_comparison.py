"""
Tests for LoadSet comparison functionality.

This module tests the LoadSet comparison feature that compares two LoadSets
and provides detailed analysis of differences between them.
"""

import pytest
from pathlib import Path

from tools.loads import (
    LoadSet,
    LoadCase,
    PointLoad,
    ForceMoment,
    Units,
    ComparisonRow,
    LoadSetCompare,
)


class TestComparisonRow:
    """Test ComparisonRow class."""

    def test_comparison_row_creation(self):
        """Test creating a ComparisonRow with all fields."""
        row = ComparisonRow(
            point_name="Point_A",
            component="fx",
            type="max",
            loadset1_value=100.0,
            loadset2_value=120.0,
            loadset1_loadcase="Case1",
            loadset2_loadcase="Case2",
            abs_diff=20.0,
            pct_diff=20.0,
        )

        assert row.point_name == "Point_A"
        assert row.component == "fx"
        assert row.type == "max"
        assert row.loadset1_value == 100.0
        assert row.loadset2_value == 120.0
        assert row.loadset1_loadcase == "Case1"
        assert row.loadset2_loadcase == "Case2"
        assert row.abs_diff == 20.0
        assert row.pct_diff == 20.0

    def test_comparison_row_validation(self):
        """Test ComparisonRow validation with invalid values."""
        # Test invalid component
        with pytest.raises(ValueError):
            ComparisonRow(
                point_name="Point_A",
                component="invalid",  # Invalid component
                type="max",
                loadset1_value=100.0,
                loadset2_value=120.0,
                loadset1_loadcase="Case1",
                loadset2_loadcase="Case2",
                abs_diff=20.0,
                pct_diff=20.0,
            )

        # Test invalid type
        with pytest.raises(ValueError):
            ComparisonRow(
                point_name="Point_A",
                component="fx",
                type="invalid",  # Invalid type
                loadset1_value=100.0,
                loadset2_value=120.0,
                loadset1_loadcase="Case1",
                loadset2_loadcase="Case2",
                abs_diff=20.0,
                pct_diff=20.0,
            )


class TestLoadSetCompare:
    """Test LoadSetCompare class."""

    def test_loadset_compare_creation(self):
        """Test creating a LoadSetCompare instance."""
        # Create sample comparison rows
        row1 = ComparisonRow(
            point_name="Point_A",
            component="fx",
            type="max",
            loadset1_value=100.0,
            loadset2_value=120.0,
            loadset1_loadcase="Case1",
            loadset2_loadcase="Case2",
            abs_diff=20.0,
            pct_diff=20.0,
        )

        row2 = ComparisonRow(
            point_name="Point_A",
            component="fx",
            type="min",
            loadset1_value=80.0,
            loadset2_value=90.0,
            loadset1_loadcase="Case3",
            loadset2_loadcase="Case4",
            abs_diff=10.0,
            pct_diff=12.5,
        )

        # Create LoadSetCompare instance
        compare = LoadSetCompare(
            loadset1_metadata={"name": "LoadSet 1", "units": {"forces": "N"}},
            loadset2_metadata={"name": "LoadSet 2", "units": {"forces": "N"}},
            comparison_rows=[row1, row2],
        )

        assert len(compare.comparison_rows) == 2
        assert compare.loadset1_metadata["name"] == "LoadSet 1"
        assert compare.loadset2_metadata["name"] == "LoadSet 2"

    def test_loadset_compare_to_dict(self):
        """Test LoadSetCompare to_dict method."""
        row = ComparisonRow(
            point_name="Point_A",
            component="fx",
            type="max",
            loadset1_value=100.0,
            loadset2_value=120.0,
            loadset1_loadcase="Case1",
            loadset2_loadcase="Case2",
            abs_diff=20.0,
            pct_diff=20.0,
        )

        compare = LoadSetCompare(
            loadset1_metadata={"name": "LoadSet 1"},
            loadset2_metadata={"name": "LoadSet 2"},
            comparison_rows=[row],
        )

        result_dict = compare.to_dict()

        assert "metadata" in result_dict
        assert "comparison_rows" in result_dict
        assert result_dict["metadata"]["loadset1"]["name"] == "LoadSet 1"
        assert result_dict["metadata"]["loadset2"]["name"] == "LoadSet 2"
        assert len(result_dict["comparison_rows"]) == 1
        assert result_dict["comparison_rows"][0]["point_name"] == "Point_A"

    def test_loadset_compare_to_json(self):
        """Test LoadSetCompare to_json method."""
        row = ComparisonRow(
            point_name="Point_A",
            component="fx",
            type="max",
            loadset1_value=100.0,
            loadset2_value=120.0,
            loadset1_loadcase="Case1",
            loadset2_loadcase="Case2",
            abs_diff=20.0,
            pct_diff=20.0,
        )

        compare = LoadSetCompare(
            loadset1_metadata={"name": "LoadSet 1"},
            loadset2_metadata={"name": "LoadSet 2"},
            comparison_rows=[row],
        )

        json_str = compare.to_json()

        # Verify it's valid JSON
        import json

        parsed = json.loads(json_str)
        assert parsed["metadata"]["loadset1"]["name"] == "LoadSet 1"
        assert len(parsed["comparison_rows"]) == 1


class TestLoadSetPointExtremes:
    """Test LoadSet.get_point_extremes() method."""

    def setup_method(self):
        """Set up test data for each test method."""
        self.test_loadset = LoadSet(
            name="Test LoadSet",
            version=1,
            description="Test data for point extremes",
            units=Units(forces="N", moments="Nm"),
            load_cases=[
                LoadCase(
                    name="Case1",
                    description="First test case",
                    point_loads=[
                        PointLoad(
                            name="Point_A",
                            force_moment=ForceMoment(
                                fx=100.0, fy=200.0, fz=300.0, mx=10.0, my=20.0, mz=30.0
                            ),
                        ),
                        PointLoad(
                            name="Point_B",
                            force_moment=ForceMoment(
                                fx=150.0, fy=50.0, fz=0.0, mx=5.0, my=0.0, mz=0.0
                            ),
                        ),
                    ],
                ),
                LoadCase(
                    name="Case2",
                    description="Second test case",
                    point_loads=[
                        PointLoad(
                            name="Point_A",
                            force_moment=ForceMoment(
                                fx=80.0, fy=250.0, fz=200.0, mx=15.0, my=10.0, mz=25.0
                            ),
                        ),
                        PointLoad(
                            name="Point_B",
                            force_moment=ForceMoment(
                                fx=200.0, fy=75.0, fz=100.0, mx=8.0, my=5.0, mz=12.0
                            ),
                        ),
                    ],
                ),
            ],
        )

    def test_get_point_extremes_basic(self):
        """Test get_point_extremes method with basic data."""
        extremes = self.test_loadset.get_point_extremes()

        # Should have both points
        assert "Point_A" in extremes
        assert "Point_B" in extremes

        # Point_A should have all components (since they're non-zero)
        point_a = extremes["Point_A"]
        assert "fx" in point_a
        assert "fy" in point_a
        assert "fz" in point_a
        assert "mx" in point_a
        assert "my" in point_a
        assert "mz" in point_a

        # Check fx for Point_A: max=100.0 (Case1), min=80.0 (Case2)
        fx_data = point_a["fx"]
        assert fx_data["max"]["value"] == 100.0
        assert fx_data["max"]["loadcase"] == "Case1"
        assert fx_data["min"]["value"] == 80.0
        assert fx_data["min"]["loadcase"] == "Case2"

        # Check fy for Point_A: max=250.0 (Case2), min=200.0 (Case1)
        fy_data = point_a["fy"]
        assert fy_data["max"]["value"] == 250.0
        assert fy_data["max"]["loadcase"] == "Case2"
        assert fy_data["min"]["value"] == 200.0
        assert fy_data["min"]["loadcase"] == "Case1"

    def test_get_point_extremes_filters_zero_components(self):
        """Test that get_point_extremes filters out components that are zero in all cases."""
        # Create a LoadSet with some zero components
        test_loadset = LoadSet(
            name="Test with zeros",
            version=1,
            units=Units(forces="N", moments="Nm"),
            load_cases=[
                LoadCase(
                    name="Case1",
                    point_loads=[
                        PointLoad(
                            name="Point_Zero",
                            force_moment=ForceMoment(
                                fx=0.0,
                                fy=0.0,
                                fz=0.0,  # All forces zero
                                mx=10.0,
                                my=0.0,
                                mz=0.0,  # Only mx non-zero
                            ),
                        ),
                    ],
                ),
            ],
        )

        extremes = test_loadset.get_point_extremes()

        # Should have Point_Zero
        assert "Point_Zero" in extremes
        point_data = extremes["Point_Zero"]

        # Should only have mx (non-zero component)
        assert "mx" in point_data
        assert "fx" not in point_data  # Filtered out (zero)
        assert "fy" not in point_data  # Filtered out (zero)
        assert "fz" not in point_data  # Filtered out (zero)
        assert "my" not in point_data  # Filtered out (zero)
        assert "mz" not in point_data  # Filtered out (zero)

    def test_get_point_extremes_empty_loadset(self):
        """Test get_point_extremes with empty LoadSet."""
        empty_loadset = LoadSet(
            name="Empty",
            version=1,
            units=Units(forces="N", moments="Nm"),
            load_cases=[],
        )

        extremes = empty_loadset.get_point_extremes()
        assert extremes == {}


class TestLoadSetComparison:
    """Test LoadSet.compare_to() method."""

    def setup_method(self):
        """Set up test LoadSets for comparison."""
        self.loadset1 = LoadSet(
            name="LoadSet 1",
            version=1,
            description="First test loadset",
            units=Units(forces="N", moments="Nm"),
            load_cases=[
                LoadCase(
                    name="Case1",
                    point_loads=[
                        PointLoad(
                            name="Point_A",
                            force_moment=ForceMoment(fx=100.0, fy=200.0, fz=300.0),
                        ),
                    ],
                ),
            ],
        )

        self.loadset2 = LoadSet(
            name="LoadSet 2",
            version=1,
            description="Second test loadset",
            units=Units(forces="N", moments="Nm"),
            load_cases=[
                LoadCase(
                    name="Case1",
                    point_loads=[
                        PointLoad(
                            name="Point_A",
                            force_moment=ForceMoment(fx=120.0, fy=180.0, fz=300.0),
                        ),
                    ],
                ),
            ],
        )

    def test_compare_to_basic(self):
        """Test basic comparison between two LoadSets."""
        comparison = self.loadset1.compare_to(self.loadset2)

        # Check metadata
        assert comparison.loadset1_metadata["name"] == "LoadSet 1"
        assert comparison.loadset2_metadata["name"] == "LoadSet 2"

        # Should have comparison rows
        assert len(comparison.comparison_rows) > 0

        # Find fx comparison rows for Point_A
        fx_rows = [
            row
            for row in comparison.comparison_rows
            if row.point_name == "Point_A" and row.component == "fx"
        ]

        # Should have both max and min rows
        max_row = next((row for row in fx_rows if row.type == "max"), None)
        min_row = next((row for row in fx_rows if row.type == "min"), None)

        assert max_row is not None
        assert min_row is not None

        # Check values: LoadSet1 fx=100.0, LoadSet2 fx=120.0
        assert max_row.loadset1_value == 100.0
        assert max_row.loadset2_value == 120.0
        assert max_row.abs_diff == 20.0
        assert max_row.pct_diff == 20.0  # (20/100)*100

    def test_compare_to_different_units(self):
        """Test comparison with different units (should auto-convert)."""
        # Create LoadSet with kN units
        loadset_kn = LoadSet(
            name="LoadSet kN",
            version=1,
            units=Units(forces="kN", moments="kNm"),
            load_cases=[
                LoadCase(
                    name="Case1",
                    point_loads=[
                        PointLoad(
                            name="Point_A",
                            force_moment=ForceMoment(
                                fx=0.12, fy=0.18, fz=0.30
                            ),  # 120N, 180N, 300N in kN
                        ),
                    ],
                ),
            ],
        )

        comparison = self.loadset1.compare_to(loadset_kn)

        # Should work despite different units
        assert len(comparison.comparison_rows) > 0

        # Check that the comparison used converted values
        fx_max_row = next(
            (
                row
                for row in comparison.comparison_rows
                if row.point_name == "Point_A"
                and row.component == "fx"
                and row.type == "max"
            ),
            None,
        )

        assert fx_max_row is not None
        assert fx_max_row.loadset1_value == 100.0  # Original N value
        assert fx_max_row.loadset2_value == 120.0  # Converted from 0.12 kN to 120 N

    def test_compare_to_invalid_input(self):
        """Test compare_to with invalid input."""
        with pytest.raises(
            ValueError, match="Can only compare to another LoadSet instance"
        ):
            self.loadset1.compare_to("not a loadset")


class TestLoadSetComparisonWithRealData:
    """Test LoadSet comparison with real data files."""

    def setup_method(self):
        """Set up real data LoadSets."""
        self.old_loads_path = (
            Path(__file__).parent.parent.parent
            / "solution"
            / "loads"
            / "old_loads.json"
        )
        self.new_loads_path = (
            Path(__file__).parent.parent.parent
            / "solution"
            / "loads"
            / "new_loads.json"
        )

    def test_load_real_data_files(self):
        """Test loading the real data files."""
        if self.old_loads_path.exists() and self.new_loads_path.exists():
            old_loadset = LoadSet.read_json(self.old_loads_path)
            new_loadset = LoadSet.read_json(self.new_loads_path)

            # Verify basic properties
            assert old_loadset.name is not None
            assert new_loadset.name is not None
            assert len(old_loadset.load_cases) > 0
            assert len(new_loadset.load_cases) > 0

    def test_compare_real_data_files(self):
        """Test comparing real old_loads.json and new_loads.json files."""
        if self.old_loads_path.exists() and self.new_loads_path.exists():
            old_loadset = LoadSet.read_json(self.old_loads_path)
            new_loadset = LoadSet.read_json(self.new_loads_path)

            # Perform comparison
            comparison = old_loadset.compare_to(new_loadset)

            # Verify comparison results
            assert comparison.loadset1_metadata["name"] == old_loadset.name
            assert comparison.loadset2_metadata["name"] == new_loadset.name
            assert len(comparison.comparison_rows) > 0

            # Verify we can export to JSON
            json_output = comparison.to_json()
            assert isinstance(json_output, str)
            assert len(json_output) > 0

            # Verify we can parse the JSON back
            import json

            parsed_data = json.loads(json_output)
            assert "metadata" in parsed_data
            assert "comparison_rows" in parsed_data
            assert len(parsed_data["comparison_rows"]) > 0

            # Print some stats for verification
            print(f"\nComparison results:")
            print(f"Total comparison rows: {len(comparison.comparison_rows)}")

            # Group by point and component for summary
            points = set(row.point_name for row in comparison.comparison_rows)
            components = set(row.component for row in comparison.comparison_rows)
            print(f"Points compared: {len(points)}")
            print(f"Components compared: {len(components)}")

            # Show a sample of the data
            if len(comparison.comparison_rows) >= 2:
                sample_row = comparison.comparison_rows[0]
                print(
                    f"Sample row: {sample_row.point_name}.{sample_row.component}.{sample_row.type} - LoadSet1: {sample_row.loadset1_value}, LoadSet2: {sample_row.loadset2_value}, Diff: {sample_row.pct_diff:.1f}%"
                )
        else:
            pytest.skip("Real data files not found, skipping test")

    def test_compare_to_edge_cases(self):
        """Test comparison edge cases."""
        # Test empty LoadSets
        empty_loadset1 = LoadSet(
            name="Empty 1",
            version=1,
            units=Units(forces="N", moments="Nm"),
            load_cases=[],
        )

        empty_loadset2 = LoadSet(
            name="Empty 2",
            version=1,
            units=Units(forces="N", moments="Nm"),
            load_cases=[],
        )

        comparison = empty_loadset1.compare_to(empty_loadset2)
        assert len(comparison.comparison_rows) == 0

        # Test LoadSet with only zero values
        zero_loadset = LoadSet(
            name="Zero LoadSet",
            version=1,
            units=Units(forces="N", moments="Nm"),
            load_cases=[
                LoadCase(
                    name="ZeroCase",
                    point_loads=[
                        PointLoad(
                            name="Point_Zero",
                            force_moment=ForceMoment(
                                fx=0.0, fy=0.0, fz=0.0, mx=0.0, my=0.0, mz=0.0
                            ),
                        ),
                    ],
                ),
            ],
        )

        # Comparing zero loadset to itself should produce no rows (all filtered out)
        zero_comparison = zero_loadset.compare_to(zero_loadset)
        assert len(zero_comparison.comparison_rows) == 0

    def test_compare_to_percentage_calculations(self):
        """Test edge cases in percentage calculations."""
        # Test with zero values in first LoadSet (should handle division by zero)
        loadset_zero = LoadSet(
            name="LoadSet with Zero",
            version=1,
            units=Units(forces="N", moments="Nm"),
            load_cases=[
                LoadCase(
                    name="Case1",
                    point_loads=[
                        PointLoad(
                            name="Point_A",
                            force_moment=ForceMoment(fx=0.0, fy=100.0),  # fx=0, fy≠0
                        ),
                    ],
                ),
            ],
        )

        loadset_nonzero = LoadSet(
            name="LoadSet with Non-Zero",
            version=1,
            units=Units(forces="N", moments="Nm"),
            load_cases=[
                LoadCase(
                    name="Case1",
                    point_loads=[
                        PointLoad(
                            name="Point_A",
                            force_moment=ForceMoment(
                                fx=100.0, fy=200.0
                            ),  # Both non-zero
                        ),
                    ],
                ),
            ],
        )

        comparison = loadset_zero.compare_to(loadset_nonzero)

        # Find fx row where loadset1=0 and loadset2=100
        fx_row = next(
            (
                row
                for row in comparison.comparison_rows
                if row.point_name == "Point_A" and row.component == "fx"
            ),
            None,
        )

        assert fx_row is not None
        assert fx_row.loadset1_value == 0.0
        assert fx_row.loadset2_value == 100.0
        assert fx_row.pct_diff == float("inf")  # Infinite percentage change


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
