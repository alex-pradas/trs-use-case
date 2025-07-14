"""
Visual chart generation tests for LoadSet comparison.

This module contains expensive visual tests that generate actual chart files
for manual inspection and verification. These tests are marked with @pytest.mark.visuals
and should be run explicitly when chart generation needs to be tested or updated.
"""

import pytest
from pathlib import Path

from tools.loads import LoadSet


@pytest.mark.visuals
class TestRangeChartsVisualGeneration:
    """Visual chart generation tests (marked as 'visuals' - run with: pytest -m visuals)."""

    def setup_method(self):
        """Set up real data LoadSets."""
        self.old_loads_path = Path(__file__).parent.parent.parent / "solution" / "loads" / "old_loads.json"
        self.new_loads_path = Path(__file__).parent.parent.parent / "solution" / "loads" / "new_loads.json"

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