"""
Tests for LoadSet comparison range chart generation.

This module tests the range bar chart visualization functionality
that creates comparison images for LoadSet force and moment ranges.
"""

import pytest
import tempfile
import os
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


class TestRangeChartGeneration:
    """Test range chart generation functionality."""

    def setup_method(self):
        """Set up test data for each test method."""
        # Create two LoadSets with known data for testing
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
                            force_moment=ForceMoment(
                                fx=120.0, fy=180.0, fz=320.0, mx=12.0, my=25.0, mz=35.0
                            ),
                        ),
                        PointLoad(
                            name="Point_B",
                            force_moment=ForceMoment(
                                fx=160.0, fy=60.0, fz=10.0, mx=6.0, my=2.0, mz=1.0
                            ),
                        ),
                    ],
                ),
                LoadCase(
                    name="Case2",
                    point_loads=[
                        PointLoad(
                            name="Point_A",
                            force_moment=ForceMoment(
                                fx=90.0, fy=260.0, fz=190.0, mx=18.0, my=15.0, mz=28.0
                            ),
                        ),
                        PointLoad(
                            name="Point_B",
                            force_moment=ForceMoment(
                                fx=210.0, fy=85.0, fz=110.0, mx=9.0, my=7.0, mz=15.0
                            ),
                        ),
                    ],
                ),
            ],
        )

    def test_generate_range_charts_basic(self):
        """Test basic range chart generation functionality."""
        comparison = self.loadset1.compare_to(self.loadset2)

        with tempfile.TemporaryDirectory() as temp_dir:
            generated_files = comparison.generate_range_charts(temp_dir)

            # Should generate files for both points
            assert len(generated_files) == 2
            assert "Point_A" in generated_files
            assert "Point_B" in generated_files

            # Check that files actually exist
            for point_name, file_path in generated_files.items():
                assert file_path.exists()
                assert file_path.suffix == ".png"
                assert file_path.stat().st_size > 0  # File should not be empty

    def test_generate_range_charts_custom_format(self):
        """Test range chart generation with different formats."""
        comparison = self.loadset1.compare_to(self.loadset2)

        with tempfile.TemporaryDirectory() as temp_dir:
            # Test SVG format
            generated_files = comparison.generate_range_charts(
                temp_dir, image_format="svg"
            )

            for point_name, file_path in generated_files.items():
                assert file_path.suffix == ".svg"
                assert file_path.exists()

    def test_generate_range_charts_creates_directory(self):
        """Test that generate_range_charts creates output directory if it doesn't exist."""
        comparison = self.loadset1.compare_to(self.loadset2)

        with tempfile.TemporaryDirectory() as temp_dir:
            # Use a non-existent subdirectory
            output_dir = Path(temp_dir) / "new_folder" / "charts"
            assert not output_dir.exists()

            generated_files = comparison.generate_range_charts(output_dir)

            # Directory should be created and files should exist
            assert output_dir.exists()
            assert output_dir.is_dir()
            assert len(generated_files) > 0

    def test_extract_component_ranges(self):
        """Test the _extract_component_ranges helper method."""
        comparison = self.loadset1.compare_to(self.loadset2)

        # Get rows for Point_A
        point_a_rows = [
            row for row in comparison.comparison_rows if row.point_name == "Point_A"
        ]

        # Extract force component ranges
        force_data = comparison._extract_component_ranges(
            point_a_rows, ["fx", "fy", "fz"]
        )

        # Should have data for all three force components
        assert "fx" in force_data
        assert "fy" in force_data
        assert "fz" in force_data

        # Check fx data structure
        fx_data = force_data["fx"]
        assert "loadset1_min" in fx_data
        assert "loadset1_max" in fx_data
        assert "loadset2_min" in fx_data
        assert "loadset2_max" in fx_data

        # Verify that min <= max for both loadsets
        assert fx_data["loadset1_min"] <= fx_data["loadset1_max"]
        assert fx_data["loadset2_min"] <= fx_data["loadset2_max"]

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        comparison = self.loadset1.compare_to(self.loadset2)

        # Test various problematic names
        test_cases = [
            ("Point A", "Point_A"),
            ("Point-B", "Point-B"),
            ("Point/C\\D", "Point_C_D"),
            ("Point::E", "Point_E"),
            ("Point   F", "Point_F"),
            ("__Point__G__", "Point_G"),
        ]

        for input_name, expected in test_cases:
            result = comparison._sanitize_filename(input_name)
            assert result == expected

    def test_generate_range_charts_with_missing_components(self):
        """Test range chart generation when some components are missing."""
        # Create a LoadSet with only force components (no moments)
        force_only_loadset = LoadSet(
            name="Force Only",
            version=1,
            units=Units(forces="N", moments="Nm"),
            load_cases=[
                LoadCase(
                    name="Case1",
                    point_loads=[
                        PointLoad(
                            name="Point_A",
                            force_moment=ForceMoment(
                                fx=100.0,
                                fy=200.0,
                                fz=300.0,
                                mx=0.0,
                                my=0.0,
                                mz=0.0,  # All moments zero
                            ),
                        ),
                    ],
                ),
            ],
        )

        comparison = force_only_loadset.compare_to(self.loadset1)

        with tempfile.TemporaryDirectory() as temp_dir:
            generated_files = comparison.generate_range_charts(temp_dir)

            # Should still generate files, but moment subplot may show "No moment data"
            assert len(generated_files) > 0
            for file_path in generated_files.values():
                assert file_path.exists()

    def test_generate_range_charts_error_handling(self):
        """Test error handling in range chart generation."""
        comparison = self.loadset1.compare_to(self.loadset2)

        # Test with invalid output directory (file instead of directory)
        with tempfile.NamedTemporaryFile() as temp_file:
            with pytest.raises(FileNotFoundError, match="not a directory"):
                comparison.generate_range_charts(temp_file.name)

    def test_generate_range_charts_base64_mode(self):
        """Test base64 generation mode."""
        import base64

        comparison = self.loadset1.compare_to(self.loadset2)

        # Generate as base64
        base64_charts = comparison.generate_range_charts(
            as_base64=True, image_format="png"
        )

        # Verify we get base64 strings
        assert isinstance(base64_charts, dict)
        assert len(base64_charts) > 0

        for point_name, base64_data in base64_charts.items():
            # Should be a string
            assert isinstance(base64_data, str)
            # Should be valid base64
            try:
                decoded = base64.b64decode(base64_data)
                # Should be a reasonable size for a PNG
                assert len(decoded) > 1000  # At least 1KB
                # PNG files start with specific magic bytes
                assert decoded[:8] == b"\x89PNG\r\n\x1a\n"
            except Exception as e:
                pytest.fail(f"Invalid base64 data for {point_name}: {e}")

    def test_generate_range_charts_base64_validation(self):
        """Test parameter validation for base64 mode."""
        comparison = self.loadset1.compare_to(self.loadset2)

        # Should work without output_dir when as_base64=True
        base64_charts = comparison.generate_range_charts(as_base64=True)
        assert len(base64_charts) > 0

        # Should raise error when output_dir is None and as_base64=False
        with pytest.raises(ValueError, match="output_dir is required"):
            comparison.generate_range_charts(as_base64=False)

    def test_generate_range_charts_format_validation(self):
        """Test image format validation."""
        comparison = self.loadset1.compare_to(self.loadset2)

        # Valid formats should work
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test PNG
            comparison.generate_range_charts(temp_dir, image_format="png")
            
            # Test SVG
            comparison.generate_range_charts(temp_dir, image_format="svg")

        # Invalid format should raise error
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ValueError, match="Unsupported image format 'pdf'"):
                comparison.generate_range_charts(temp_dir, image_format="pdf")
            
            with pytest.raises(ValueError, match="Unsupported image format 'jpeg'"):
                comparison.generate_range_charts(temp_dir, image_format="jpeg")


class TestRangeChartsWithRealData:
    """Test range chart generation with real data files."""

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

    def test_real_data_range_charts(self):
        """Test range chart generation with real old_loads vs new_loads data."""
        if self.old_loads_path.exists() and self.new_loads_path.exists():
            old_loadset = LoadSet.read_json(self.old_loads_path)
            new_loadset = LoadSet.read_json(self.new_loads_path)

            comparison = old_loadset.compare_to(new_loadset)

            with tempfile.TemporaryDirectory() as temp_dir:
                generated_files = comparison.generate_range_charts(temp_dir)

                # Should generate files for all points in the real data
                assert len(generated_files) > 0

                # Verify all files exist and have reasonable sizes
                for point_name, file_path in generated_files.items():
                    assert file_path.exists()
                    assert file_path.suffix == ".png"
                    assert (
                        file_path.stat().st_size > 10000
                    )  # Should be at least 10KB for a real chart

                    print(f"Generated chart for {point_name}: {file_path}")
        else:
            pytest.skip("Real data files not found, skipping test")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
