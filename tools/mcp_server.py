"""
FastMCP server for LoadSet operations.

This module provides MCP tools for load data processing operations.
"""

from fastmcp import FastMCP
from typing import Optional
from os import PathLike
import sys
from pathlib import Path

# Add the tools directory to Python path so we can import loads
tools_dir = Path(__file__).parent
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

# Import LoadSet and related classes
from loads import LoadSet, ForceUnit, LoadSetCompare


# Global state for LoadSets
_current_loadset: Optional[LoadSet] = None
_comparison_loadset: Optional[LoadSet] = None
_current_comparison: Optional[LoadSetCompare] = None


def reset_global_state():
    """Reset the global LoadSet state."""
    global _current_loadset, _comparison_loadset, _current_comparison
    _current_loadset = None
    _comparison_loadset = None
    _current_comparison = None


def create_mcp_server() -> FastMCP:
    """
    Create and configure the FastMCP server for LoadSet operations.

    Returns:
        FastMCP: Configured MCP server instance
    """

    mcp = FastMCP("LoadSet MCP Server")

    @mcp.tool
    def load_from_json(file_path: PathLike) -> dict:
        """
        Load a LoadSet from a JSON file.

        Args:
            file_path: Path to the JSON file containing LoadSet data

        Returns:
            dict: Success message and LoadSet summary

        Raises:
            ValueError: If file cannot be loaded or parsed
        """
        global _current_loadset

        try:
            _current_loadset = LoadSet.read_json(file_path)
            return {
                "success": True,
                "message": f"LoadSet loaded from {file_path}",
                "loadset_name": _current_loadset.name,
                "num_load_cases": len(_current_loadset.load_cases),
                "units": {
                    "forces": _current_loadset.units.forces,
                    "moments": _current_loadset.units.moments,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @mcp.tool
    def convert_units(target_units: ForceUnit) -> dict:
        """
        Convert the current LoadSet to different units.

        Args:
            target_units: Target force units ("N", "kN", "lbf", "klbf")

        Returns:
            dict: Success message and conversion info
        """
        global _current_loadset

        if _current_loadset is None:
            return {
                "success": False,
                "error": "No LoadSet loaded. Use load_from_json first.",
            }

        try:
            original_units = _current_loadset.units.forces
            _current_loadset = _current_loadset.convert_to(target_units)

            return {
                "success": True,
                "message": f"Units converted from {original_units} to {target_units}",
                "new_units": {
                    "forces": _current_loadset.units.forces,
                    "moments": _current_loadset.units.moments,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @mcp.tool
    def scale_loads(factor: float) -> dict:
        """
        Scale all loads in the current LoadSet by a factor.

        Args:
            factor: Scaling factor to apply to all loads

        Returns:
            dict: Success message and scaling info
        """
        global _current_loadset

        if _current_loadset is None:
            return {
                "success": False,
                "error": "No LoadSet loaded. Use load_from_json first.",
            }

        try:
            _current_loadset = _current_loadset.factor(factor)

            return {
                "success": True,
                "message": f"Loads scaled by factor {factor}",
                "scaling_factor": factor,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @mcp.tool
    def export_to_ansys(folder_path: PathLike, name_stem: str) -> dict:
        """
        Export the current LoadSet to ANSYS format files.

        Args:
            folder_path: Directory path to save ANSYS files
            name_stem: Base name for the output files

        Returns:
            dict: Success message and export info
        """
        global _current_loadset

        if _current_loadset is None:
            return {
                "success": False,
                "error": "No LoadSet loaded. Use load_from_json first.",
            }

        try:
            _current_loadset.to_ansys(folder_path, name_stem)

            return {
                "success": True,
                "message": f"ANSYS files exported to {folder_path} with stem {name_stem}",
                "num_files": len(_current_loadset.load_cases),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @mcp.tool
    def get_load_summary() -> dict:
        """
        Get summary information about the current LoadSet.

        Returns:
            dict: LoadSet summary information
        """
        global _current_loadset

        if _current_loadset is None:
            return {
                "success": False,
                "error": "No LoadSet loaded. Use load_from_json first.",
            }

        try:
            total_point_loads = sum(
                len(lc.point_loads) for lc in _current_loadset.load_cases
            )

            return {
                "success": True,
                "name": _current_loadset.name,
                "description": _current_loadset.description,
                "version": _current_loadset.version,
                "units": {
                    "forces": _current_loadset.units.forces,
                    "moments": _current_loadset.units.moments,
                },
                "num_load_cases": len(_current_loadset.load_cases),
                "total_point_loads": total_point_loads,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @mcp.tool
    def list_load_cases() -> dict:
        """
        List all load cases in the current LoadSet.

        Returns:
            dict: List of load cases with their information
        """
        global _current_loadset

        if _current_loadset is None:
            return {
                "success": False,
                "error": "No LoadSet loaded. Use load_from_json first.",
            }

        try:
            load_cases = []
            for lc in _current_loadset.load_cases:
                load_cases.append(
                    {
                        "name": lc.name,
                        "description": lc.description,
                        "num_point_loads": len(lc.point_loads),
                        "point_load_names": [pl.name for pl in lc.point_loads],
                    }
                )

            return {
                "success": True,
                "load_cases": load_cases,
                "total_load_cases": len(load_cases),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @mcp.tool
    def load_second_loadset(file_path: PathLike) -> dict:
        """
        Load a second LoadSet from a JSON file for comparison.

        Args:
            file_path: Path to the JSON file containing the second LoadSet data

        Returns:
            dict: Success message and LoadSet summary

        Raises:
            ValueError: If file cannot be loaded or parsed
        """
        global _comparison_loadset, _current_comparison

        try:
            _comparison_loadset = LoadSet.read_json(file_path)
            # Reset any existing comparison when loading new comparison loadset
            _current_comparison = None
            
            return {
                "success": True,
                "message": f"Comparison LoadSet loaded from {file_path}",
                "loadset_name": _comparison_loadset.name,
                "num_load_cases": len(_comparison_loadset.load_cases),
                "units": {
                    "forces": _comparison_loadset.units.forces,
                    "moments": _comparison_loadset.units.moments,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @mcp.tool
    def compare_loadsets() -> dict:
        """
        Compare the current LoadSet with the comparison LoadSet.

        Returns:
            dict: Comparison results in JSON format

        Raises:
            ValueError: If LoadSets are not loaded or comparison fails
        """
        global _current_loadset, _comparison_loadset, _current_comparison

        if _current_loadset is None:
            return {
                "success": False,
                "error": "No current LoadSet loaded. Use load_from_json first.",
            }

        if _comparison_loadset is None:
            return {
                "success": False,
                "error": "No comparison LoadSet loaded. Use load_second_loadset first.",
            }

        try:
            _current_comparison = _current_loadset.compare_to(_comparison_loadset)
            comparison_dict = _current_comparison.to_dict()
            
            return {
                "success": True,
                "message": "LoadSets compared successfully",
                "loadset1_name": _current_loadset.name,
                "loadset2_name": _comparison_loadset.name,
                "total_comparison_rows": len(_current_comparison.comparison_rows),
                "comparison_data": comparison_dict,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @mcp.tool
    def generate_comparison_charts(output_dir: PathLike = None, format: str = "png", as_base64: bool = False) -> dict:
        """
        Generate range bar charts comparing the LoadSets.

        Args:
            output_dir: Directory to save charts (optional if as_base64=True)
            format: Image format (png, jpg, etc.)
            as_base64: If True, return base64-encoded images instead of saving files

        Returns:
            dict: Success message and chart information or base64 data
        """
        global _current_comparison

        if _current_comparison is None:
            return {
                "success": False,
                "error": "No comparison available. Use compare_loadsets first.",
            }

        try:
            if as_base64:
                # Generate charts as base64 strings
                from pathlib import Path
                charts = _current_comparison.generate_range_charts(
                    output_dir=Path.cwd(), format=format, as_base64=True
                )
                return {
                    "success": True,
                    "message": "Comparison charts generated as base64 data",
                    "format": format,
                    "charts": charts,  # Dict with point names as keys, base64 strings as values
                }
            else:
                # Save charts to files
                if output_dir is None:
                    return {
                        "success": False,
                        "error": "output_dir required when as_base64=False",
                    }
                
                charts = _current_comparison.generate_range_charts(
                    output_dir=output_dir, format=format, as_base64=False
                )
                # Convert Path objects to strings for JSON serialization
                chart_paths = {point: str(path) for point, path in charts.items()}
                
                return {
                    "success": True,
                    "message": f"Comparison charts saved to {output_dir}",
                    "format": format,
                    "chart_files": chart_paths,
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @mcp.tool
    def export_comparison_json(file_path: PathLike) -> dict:
        """
        Export the current comparison to a JSON file.

        Args:
            file_path: Path where to save the JSON file

        Returns:
            dict: Success message and export info
        """
        global _current_comparison

        if _current_comparison is None:
            return {
                "success": False,
                "error": "No comparison available. Use compare_loadsets first.",
            }

        try:
            # Export to JSON file
            from pathlib import Path
            
            json_content = _current_comparison.to_json()
            Path(file_path).write_text(json_content)
            
            return {
                "success": True,
                "message": f"Comparison exported to {file_path}",
                "total_rows": len(_current_comparison.comparison_rows),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @mcp.tool
    def get_comparison_summary() -> dict:
        """
        Get a high-level summary of the current comparison.

        Returns:
            dict: Comparison summary statistics
        """
        global _current_comparison, _current_loadset, _comparison_loadset

        if _current_comparison is None:
            return {
                "success": False,
                "error": "No comparison available. Use compare_loadsets first.",
            }

        try:
            comparison_rows = _current_comparison.comparison_rows
            
            # Calculate summary statistics
            total_rows = len(comparison_rows)
            points = set(row.point_name for row in comparison_rows)
            components = set(row.component for row in comparison_rows)
            
            # Find largest differences
            max_abs_diff = max((abs(row.abs_diff) for row in comparison_rows), default=0)
            max_pct_diff = max((abs(row.pct_diff) for row in comparison_rows if row.pct_diff is not None), default=0)
            
            # Find row with maximum absolute difference
            max_diff_row = max(comparison_rows, key=lambda r: abs(r.abs_diff))
            
            return {
                "success": True,
                "loadset1_name": _current_loadset.name if _current_loadset else "Unknown",
                "loadset2_name": _comparison_loadset.name if _comparison_loadset else "Unknown",
                "total_comparison_rows": total_rows,
                "unique_points": len(points),
                "unique_components": len(components),
                "point_names": sorted(list(points)),
                "components": sorted(list(components)),
                "max_absolute_difference": max_abs_diff,
                "max_percentage_difference": max_pct_diff,
                "largest_difference": {
                    "point": max_diff_row.point_name,
                    "component": max_diff_row.component,
                    "type": max_diff_row.type,
                    "absolute_diff": max_diff_row.abs_diff,
                    "percentage_diff": max_diff_row.pct_diff,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    return mcp


if __name__ == "__main__":
    import sys
    
    # Allow transport to be specified via command line argument
    transport = "sse"  # Default to SSE
    
    # Check for command line argument
    if len(sys.argv) > 1 and sys.argv[1] in ["stdio", "sse"]:
        transport = sys.argv[1]
    
    server = create_mcp_server()
    server.run(transport=transport)
