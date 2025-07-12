"""
Tests for LoadSet comparison range chart generation.

This module tests the range bar chart visualization functionality
that creates comparison images for LoadSet force and moment ranges.
"""

import pytest
import tempfile
import os
from pathlib import Path

from loads import LoadSet, LoadCase, PointLoad, ForceMoment, Units, ComparisonRow, LoadSetCompare


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
                                fx=100.0, fy=200.0, fz=300.0,
                                mx=10.0, my=20.0, mz=30.0
                            ),
                        ),
                        PointLoad(
                            name="Point_B",
                            force_moment=ForceMoment(
                                fx=150.0, fy=50.0, fz=0.0,
                                mx=5.0, my=0.0, mz=0.0
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
                                fx=80.0, fy=250.0, fz=200.0,
                                mx=15.0, my=10.0, mz=25.0
                            ),
                        ),
                        PointLoad(
                            name="Point_B",
                            force_moment=ForceMoment(
                                fx=200.0, fy=75.0, fz=100.0,
                                mx=8.0, my=5.0, mz=12.0
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
                                fx=120.0, fy=180.0, fz=320.0,
                                mx=12.0, my=25.0, mz=35.0
                            ),
                        ),
                        PointLoad(
                            name="Point_B",
                            force_moment=ForceMoment(
                                fx=160.0, fy=60.0, fz=10.0,
                                mx=6.0, my=2.0, mz=1.0
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
                                fx=90.0, fy=260.0, fz=190.0,
                                mx=18.0, my=15.0, mz=28.0
                            ),
                        ),
                        PointLoad(
                            name="Point_B",
                            force_moment=ForceMoment(
                                fx=210.0, fy=85.0, fz=110.0,
                                mx=9.0, my=7.0, mz=15.0
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
            generated_files = comparison.generate_range_charts(temp_dir, format="svg")
            
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
        point_a_rows = [row for row in comparison.comparison_rows if row.point_name == "Point_A"]
        
        # Extract force component ranges
        force_data = comparison._extract_component_ranges(point_a_rows, ['fx', 'fy', 'fz'])
        
        # Should have data for all three force components
        assert 'fx' in force_data
        assert 'fy' in force_data
        assert 'fz' in force_data
        
        # Check fx data structure
        fx_data = force_data['fx']
        assert 'loadset1_min' in fx_data
        assert 'loadset1_max' in fx_data
        assert 'loadset2_min' in fx_data
        assert 'loadset2_max' in fx_data
        
        # Verify that min <= max for both loadsets
        assert fx_data['loadset1_min'] <= fx_data['loadset1_max']
        assert fx_data['loadset2_min'] <= fx_data['loadset2_max']

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
                                fx=100.0, fy=200.0, fz=300.0,
                                mx=0.0, my=0.0, mz=0.0  # All moments zero
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


class TestRangeChartsWithRealData:
    """Test range chart generation with real data files."""

    def setup_method(self):
        """Set up real data LoadSets."""
        self.old_loads_path = Path(__file__).parent.parent / "solution" / "loads" / "old_loads.json"
        self.new_loads_path = Path(__file__).parent.parent / "solution" / "loads" / "new_loads.json"

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
                    assert file_path.stat().st_size > 10000  # Should be at least 10KB for a real chart
                    
                    print(f"Generated chart for {point_name}: {file_path}")
        else:
            pytest.skip("Real data files not found, skipping test")

    @pytest.mark.visuals
    def test_generate_visual_range_charts(self):
        """Generate visual range charts from real data (marked as 'visuals' - run with: pytest -m visuals)."""
        if self.old_loads_path.exists() and self.new_loads_path.exists():
            old_loadset = LoadSet.read_json(self.old_loads_path)
            new_loadset = LoadSet.read_json(self.new_loads_path)
            
            comparison = old_loadset.compare_to(new_loadset)
            
            # Create visual output directory in tests folder
            visual_output_dir = Path(__file__).parent / "visual_range_charts"
            
            generated_files = comparison.generate_range_charts(visual_output_dir)
            
            # Verify all files exist and have reasonable sizes
            assert len(generated_files) > 0
            
            print(f"\nGenerated visual range charts in: {visual_output_dir}")
            print("Files created:")
            
            for point_name, file_path in generated_files.items():
                assert file_path.exists()
                assert file_path.suffix == ".png"
                file_size_kb = file_path.stat().st_size / 1024
                print(f"  {point_name}: {file_path.name} ({file_size_kb:.1f} KB)")
            
            # Also generate summary statistics
            summary_file = visual_output_dir / "comparison_summary.txt"
            with open(summary_file, 'w') as f:
                f.write("LoadSet Comparison Summary\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Old LoadSet: {old_loadset.name}\n")
                f.write(f"New LoadSet: {new_loadset.name}\n")
                f.write(f"Units: Forces={old_loadset.units.forces}, Moments={old_loadset.units.moments}\n\n")
                
                # Calculate range statistics
                points_data = {}
                for row in comparison.comparison_rows:
                    if row.point_name not in points_data:
                        points_data[row.point_name] = {'forces': {}, 'moments': {}}
                    
                    category = 'forces' if row.component in ['fx', 'fy', 'fz'] else 'moments'
                    if row.component not in points_data[row.point_name][category]:
                        points_data[row.point_name][category][row.component] = {}
                    
                    points_data[row.point_name][category][row.component][row.type] = {
                        'old': row.loadset1_value,
                        'new': row.loadset2_value,
                        'old_case': row.loadset1_loadcase,
                        'new_case': row.loadset2_loadcase,
                        'pct_diff': row.pct_diff
                    }
                
                for point_name, data in points_data.items():
                    f.write(f"\n{point_name}:\n")
                    f.write("-" * (len(point_name) + 1) + "\n")
                    
                    # Forces
                    f.write("  Forces:\n")
                    for component in ['fx', 'fy', 'fz']:
                        if component in data['forces']:
                            comp_data = data['forces'][component]
                            if 'max' in comp_data and 'min' in comp_data:
                                old_range = comp_data['max']['old'] - comp_data['min']['old']
                                new_range = comp_data['max']['new'] - comp_data['min']['new']
                                range_change = ((new_range - old_range) / old_range * 100) if old_range != 0 else 0
                                f.write(f"    {component}: Old range={old_range:.4f}{old_loadset.units.forces}, "
                                       f"New range={new_range:.4f}{old_loadset.units.forces}, "
                                       f"Change={range_change:+.1f}%\n")
                                f.write(f"         Max: {comp_data['max']['old']:.4f} → {comp_data['max']['new']:.4f} "
                                       f"({comp_data['max']['pct_diff']:+.1f}%)\n")
                                f.write(f"         Min: {comp_data['min']['old']:.4f} → {comp_data['min']['new']:.4f} "
                                       f"({comp_data['min']['pct_diff']:+.1f}%)\n")
                    
                    # Moments
                    f.write("  Moments:\n")
                    for component in ['mx', 'my', 'mz']:
                        if component in data['moments']:
                            comp_data = data['moments'][component]
                            if 'max' in comp_data and 'min' in comp_data:
                                old_range = comp_data['max']['old'] - comp_data['min']['old']
                                new_range = comp_data['max']['new'] - comp_data['min']['new']
                                range_change = ((new_range - old_range) / old_range * 100) if old_range != 0 else 0
                                f.write(f"    {component}: Old range={old_range:.4f}{old_loadset.units.moments}, "
                                       f"New range={new_range:.4f}{old_loadset.units.moments}, "
                                       f"Change={range_change:+.1f}%\n")
                                f.write(f"         Max: {comp_data['max']['old']:.4f} → {comp_data['max']['new']:.4f} "
                                       f"({comp_data['max']['pct_diff']:+.1f}%)\n")
                                f.write(f"         Min: {comp_data['min']['old']:.4f} → {comp_data['min']['new']:.4f} "
                                       f"({comp_data['min']['pct_diff']:+.1f}%)\n")
            
            print(f"  Summary: {summary_file.name}")
            print(f"\nVisual charts saved. To regenerate, run: uv run pytest -m visuals -s")
            
        else:
            pytest.skip("Real data files not found, skipping visual generation")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])