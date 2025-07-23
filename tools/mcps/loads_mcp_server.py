"""
FastMCP server for LoadSet operations.

This module provides MCP tools for load data processing operations.
"""

from fastmcp import FastMCP
from os import PathLike
import sys
from pathlib import Path
import json

# Add the tools directory to Python path so we can import loads
tools_dir = Path(__file__).parent.parent  # Go up one level from mcps to tools
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

# Import LoadSet and related classes
from loads import LoadSet, ForceUnit, LoadSetCompare


class LoadSetMCPProvider:
    """Provider class for LoadSet MCP operations with encapsulated state."""

    def __init__(self):
        self._current_loadset: LoadSet | None = None
        self._comparison_loadset: LoadSet | None = None
        self._current_comparison: LoadSetCompare | None = None

    def reset_state(self):
        """Reset the LoadSet state."""
        self._current_loadset = None
        self._comparison_loadset = None
        self._current_comparison = None

    def load_from_json(self, file_path: PathLike) -> dict:
        """
        Load a LoadSet from a JSON file.

        Args:
            file_path: Path to the JSON file containing LoadSet data

        Returns:
            dict: Success message and LoadSet summary

        Raises:
            ValueError: If file cannot be loaded or parsed
        """
        try:
            self._current_loadset = LoadSet.read_json(file_path)
            return {
                "success": True,
                "message": f"LoadSet loaded from {file_path}",
                "loadset_name": self._current_loadset.name,
                "num_load_cases": len(self._current_loadset.load_cases),
                "units": {
                    "forces": self._current_loadset.units.forces,
                    "moments": self._current_loadset.units.moments,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def load_from_data(self, loadset_data: dict) -> dict:
        """
        Load a LoadSet from JSON data directly.

        Args:
            loadset_data: Dictionary containing LoadSet data (JSON object)

        Returns:
            dict: Success message and LoadSet summary

        Raises:
            ValueError: If data cannot be parsed as LoadSet
        """
        try:
            self._current_loadset = LoadSet.model_validate(loadset_data)
            return {
                "success": True,
                "message": "LoadSet loaded from data",
                "loadset_name": self._current_loadset.name,
                "num_load_cases": len(self._current_loadset.load_cases),
                "units": {
                    "forces": self._current_loadset.units.forces,
                    "moments": self._current_loadset.units.moments,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def load_from_resource(self, resource_uri: str) -> dict:
        """
        Load a LoadSet from a resource URI.

        Args:
            resource_uri: Resource URI (e.g., "loadsets://new_loads.json")

        Returns:
            dict: Success message and LoadSet summary

        Raises:
            ValueError: If resource cannot be loaded or parsed
        """
        try:
            # Parse the resource URI to get the resource path
            if resource_uri.startswith("loadsets://"):
                resource_name = resource_uri.replace("loadsets://", "")

                # Get the project root directory (two levels up from tools/mcps)
                project_root = Path(__file__).parent.parent.parent

                if resource_name == "new_loads.json":
                    file_path = project_root / "solution" / "loads" / "new_loads.json"
                elif resource_name == "old_loads.json":
                    file_path = project_root / "solution" / "loads" / "old_loads.json"
                else:
                    return {
                        "success": False,
                        "error": f"Unknown resource: {resource_name}. Available: new_loads.json, old_loads.json",
                    }

                # Load the LoadSet from the file
                self._current_loadset = LoadSet.read_json(file_path)

                return {
                    "success": True,
                    "message": f"LoadSet loaded from resource {resource_uri}",
                    "loadset_name": self._current_loadset.name,
                    "num_load_cases": len(self._current_loadset.load_cases),
                    "units": {
                        "forces": self._current_loadset.units.forces,
                        "moments": self._current_loadset.units.moments,
                    },
                }
            else:
                return {
                    "success": False,
                    "error": f"Unsupported resource URI scheme. Expected 'loadsets://', got: {resource_uri}",
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def convert_units(self, target_units: ForceUnit) -> dict:
        """
        Convert the current LoadSet to different units.

        Args:
            target_units: Target force units ("N", "kN", "lbf", "klbf")

        Returns:
            dict: Success message and conversion info
        """
        if self._current_loadset is None:
            return {
                "success": False,
                "error": "No LoadSet loaded. Use load_from_json first.",
            }

        try:
            original_units = self._current_loadset.units.forces
            self._current_loadset = self._current_loadset.convert_to(target_units)

            return {
                "success": True,
                "message": f"Units converted from {original_units} to {target_units}",
                "new_units": {
                    "forces": self._current_loadset.units.forces,
                    "moments": self._current_loadset.units.moments,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def scale_loads(self, factor: float) -> dict:
        """
        Scale all loads in the current LoadSet by a factor.

        Args:
            factor: Scaling factor to apply to all loads

        Returns:
            dict: Success message and scaling info
        """
        if self._current_loadset is None:
            return {
                "success": False,
                "error": "No LoadSet loaded. Use load_from_json first.",
            }

        try:
            self._current_loadset = self._current_loadset.factor(factor)

            return {
                "success": True,
                "message": f"Loads scaled by factor {factor}",
                "scaling_factor": factor,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def export_to_ansys(self, folder_path: PathLike, name_stem: str) -> dict:
        """
        Export the current LoadSet to ANSYS format files.

        Args:
            folder_path: Directory path to save ANSYS files
            name_stem: Base name for the output files

        Returns:
            dict: Success message and export info
        """
        if self._current_loadset is None:
            return {
                "success": False,
                "error": "No LoadSet loaded. Use load_from_json first.",
            }

        try:
            self._current_loadset.to_ansys(folder_path, name_stem)

            return {
                "success": True,
                "message": f"ANSYS files exported to {folder_path} with stem {name_stem}",
                "num_files": len(self._current_loadset.load_cases),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_load_summary(self) -> dict:
        """
        Get summary information about the current LoadSet.

        Returns:
            dict: LoadSet summary information
        """
        if self._current_loadset is None:
            return {
                "success": False,
                "error": "No LoadSet loaded. Use load_from_json first.",
            }

        try:
            total_point_loads = sum(
                len(lc.point_loads) for lc in self._current_loadset.load_cases
            )

            return {
                "success": True,
                "name": self._current_loadset.name,
                "description": self._current_loadset.description,
                "version": self._current_loadset.version,
                "units": {
                    "forces": self._current_loadset.units.forces,
                    "moments": self._current_loadset.units.moments,
                },
                "num_load_cases": len(self._current_loadset.load_cases),
                "total_point_loads": total_point_loads,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_load_cases(self) -> dict:
        """
        List all load cases in the current LoadSet.

        Returns:
            dict: List of load cases with their information
        """
        if self._current_loadset is None:
            return {
                "success": False,
                "error": "No LoadSet loaded. Use load_from_json first.",
            }

        try:
            load_cases = []
            for lc in self._current_loadset.load_cases:
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

    def load_second_loadset(self, file_path: PathLike) -> dict:
        """
        Load a second LoadSet from a JSON file for comparison.

        Args:
            file_path: Path to the JSON file containing the second LoadSet data

        Returns:
            dict: Success message and LoadSet summary

        Raises:
            ValueError: If file cannot be loaded or parsed
        """
        try:
            self._comparison_loadset = LoadSet.read_json(file_path)
            # Reset any existing comparison when loading new comparison loadset
            self._current_comparison = None

            return {
                "success": True,
                "message": f"Comparison LoadSet loaded from {file_path}",
                "loadset_name": self._comparison_loadset.name,
                "num_load_cases": len(self._comparison_loadset.load_cases),
                "units": {
                    "forces": self._comparison_loadset.units.forces,
                    "moments": self._comparison_loadset.units.moments,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def load_second_loadset_from_data(self, loadset_data: dict) -> dict:
        """
        Load a second LoadSet from JSON data directly for comparison.

        Args:
            loadset_data: Dictionary containing LoadSet data (JSON object)

        Returns:
            dict: Success message and LoadSet summary

        Raises:
            ValueError: If data cannot be parsed as LoadSet
        """
        try:
            self._comparison_loadset = LoadSet.model_validate(loadset_data)
            # Reset any existing comparison when loading new comparison loadset
            self._current_comparison = None

            return {
                "success": True,
                "message": "Comparison LoadSet loaded from data",
                "loadset_name": self._comparison_loadset.name,
                "num_load_cases": len(self._comparison_loadset.load_cases),
                "units": {
                    "forces": self._comparison_loadset.units.forces,
                    "moments": self._comparison_loadset.units.moments,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def load_second_loadset_from_resource(self, resource_uri: str) -> dict:
        """
        Load a second LoadSet from a resource URI for comparison.

        Args:
            resource_uri: Resource URI (e.g., "loadsets://old_loads.json")

        Returns:
            dict: Success message and LoadSet summary

        Raises:
            ValueError: If resource cannot be loaded or parsed
        """
        try:
            # Parse the resource URI to get the resource path
            if resource_uri.startswith("loadsets://"):
                resource_name = resource_uri.replace("loadsets://", "")

                # Get the project root directory (two levels up from tools/mcps)
                project_root = Path(__file__).parent.parent.parent

                if resource_name == "new_loads.json":
                    file_path = project_root / "solution" / "loads" / "new_loads.json"
                elif resource_name == "old_loads.json":
                    file_path = project_root / "solution" / "loads" / "old_loads.json"
                else:
                    return {
                        "success": False,
                        "error": f"Unknown resource: {resource_name}. Available: new_loads.json, old_loads.json",
                    }

                # Load the comparison LoadSet from the file
                self._comparison_loadset = LoadSet.read_json(file_path)
                # Reset any existing comparison when loading new comparison loadset
                self._current_comparison = None

                return {
                    "success": True,
                    "message": f"Comparison LoadSet loaded from resource {resource_uri}",
                    "loadset_name": self._comparison_loadset.name,
                    "num_load_cases": len(self._comparison_loadset.load_cases),
                    "units": {
                        "forces": self._comparison_loadset.units.forces,
                        "moments": self._comparison_loadset.units.moments,
                    },
                }
            else:
                return {
                    "success": False,
                    "error": f"Unsupported resource URI scheme. Expected 'loadsets://', got: {resource_uri}",
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def compare_loadsets(self) -> dict:
        """
        Compare the current LoadSet with the comparison LoadSet.

        Returns:
            dict: Comparison results in JSON format

        Raises:
            ValueError: If LoadSets are not loaded or comparison fails
        """
        if self._current_loadset is None:
            return {
                "success": False,
                "error": "No current LoadSet loaded. Use load_from_json first.",
            }

        if self._comparison_loadset is None:
            return {
                "success": False,
                "error": "No comparison LoadSet loaded. Use load_second_loadset first.",
            }

        try:
            self._current_comparison = self._current_loadset.compare_to(
                self._comparison_loadset
            )
            comparison_dict = self._current_comparison.to_dict()

            return {
                "success": True,
                "message": "LoadSets compared successfully",
                "loadset1_name": self._current_loadset.name,
                "loadset2_name": self._comparison_loadset.name,
                "total_comparison_rows": len(self._current_comparison.comparison_rows),
                "comparison_data": comparison_dict,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def generate_comparison_charts(
        self,
        output_dir: PathLike | None = None,
        format: str = "png",
        as_images: bool = False,
    ) -> dict:
        """
        Generate range bar charts comparing the LoadSets.

        Args:
            output_dir: Directory to save charts (optional if as_images=True)
            format: Image format (png, jpg, etc.)
            as_images: If True, return base64-encoded image strings instead of saving files

        Returns:
            dict: Success message and chart information (base64 strings or file paths)
        """
        if self._current_comparison is None:
            return {
                "success": False,
                "error": "No comparison available. Use compare_loadsets first.",
            }

        try:
            if as_images:
                # Generate charts as base64 strings
                from pathlib import Path

                charts = self._current_comparison.generate_range_charts(
                    output_dir=Path.cwd(), image_format=format, as_base64=True
                )

                # Return base64 strings directly instead of Image objects
                return {
                    "success": True,
                    "message": "Comparison charts generated as base64 strings",
                    "format": format,
                    "charts": charts,  # Dict with point names as keys, base64 strings as values
                }
            else:
                # Save charts to files
                if output_dir is None:
                    return {
                        "success": False,
                        "error": "output_dir required when as_images=False",
                    }

                charts = self._current_comparison.generate_range_charts(
                    output_dir=output_dir, image_format=format, as_base64=False
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

    def export_comparison_json(self, file_path: PathLike) -> dict:
        """
        Export the current comparison to a JSON file.

        Args:
            file_path: Path where to save the JSON file

        Returns:
            dict: Success message and export info
        """
        if self._current_comparison is None:
            return {
                "success": False,
                "error": "No comparison available. Use compare_loadsets first.",
            }

        try:
            # Export to JSON file
            from pathlib import Path

            json_content = self._current_comparison.to_json()
            Path(file_path).write_text(json_content)

            return {
                "success": True,
                "message": f"Comparison exported to {file_path}",
                "total_rows": len(self._current_comparison.comparison_rows),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_comparison_summary(self) -> dict:
        """
        Get a high-level summary of the current comparison.

        Returns:
            dict: Comparison summary statistics
        """
        if self._current_comparison is None:
            return {
                "success": False,
                "error": "No comparison available. Use compare_loadsets first.",
            }

        try:
            comparison_rows = self._current_comparison.comparison_rows

            # Calculate summary statistics
            total_rows = len(comparison_rows)
            points = set(row.point_name for row in comparison_rows)
            components = set(row.component for row in comparison_rows)

            # Find largest differences
            max_abs_diff = max(
                (abs(row.abs_diff) for row in comparison_rows), default=0
            )
            max_pct_diff = max(
                (
                    abs(row.pct_diff)
                    for row in comparison_rows
                    if row.pct_diff is not None
                ),
                default=0,
            )

            # Find row with maximum absolute difference
            max_diff_row = max(comparison_rows, key=lambda r: abs(r.abs_diff))

            return {
                "success": True,
                "loadset1_name": self._current_loadset.name
                if self._current_loadset
                else "Unknown",
                "loadset2_name": self._comparison_loadset.name
                if self._comparison_loadset
                else "Unknown",
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

    def envelope_loadset(self) -> dict:
        """
        Create an envelope LoadSet containing only load cases with extreme values.

        For each point and component (fx, fy, fz, mx, my, mz), selects load cases with:
        - Maximum value (always included)
        - Minimum value (only if negative)

        Load cases appearing multiple times are deduplicated in the result.

        Returns:
            dict: Success message and envelope statistics
        """
        if self._current_loadset is None:
            return {
                "success": False,
                "error": "No LoadSet loaded. Use load_from_json first.",
            }

        try:
            original_case_count = len(self._current_loadset.load_cases)
            self._current_loadset = self._current_loadset.envelope()
            envelope_case_count = len(self._current_loadset.load_cases)

            return {
                "success": True,
                "message": "LoadSet envelope created successfully",
                "original_load_cases": original_case_count,
                "envelope_load_cases": envelope_case_count,
                "reduction_ratio": round(
                    (original_case_count - envelope_case_count)
                    / original_case_count
                    * 100,
                    2,
                )
                if original_case_count > 0
                else 0,
                "envelope_case_names": [
                    lc.name for lc in self._current_loadset.load_cases
                ],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


def create_mcp_server() -> FastMCP:
    """
    Create and configure the FastMCP server for LoadSet operations.

    Returns:
        FastMCP: Configured MCP server instance
    """
    mcp = FastMCP("LoadSet MCP Server")
    provider = LoadSetMCPProvider()

    # Register all methods as tools
    mcp.tool(provider.load_from_json)
    mcp.tool(provider.load_from_data)
    mcp.tool(provider.load_from_resource)
    mcp.tool(provider.convert_units)
    mcp.tool(provider.scale_loads)
    mcp.tool(provider.export_to_ansys)
    mcp.tool(provider.get_load_summary)
    mcp.tool(provider.list_load_cases)
    mcp.tool(provider.load_second_loadset)
    mcp.tool(provider.load_second_loadset_from_data)
    mcp.tool(provider.load_second_loadset_from_resource)
    mcp.tool(provider.compare_loadsets)
    mcp.tool(provider.generate_comparison_charts)
    mcp.tool(provider.export_comparison_json)
    mcp.tool(provider.get_comparison_summary)
    mcp.tool(provider.envelope_loadset)

    # Register resource definitions for JSON load files
    @mcp.resource("loadsets://new_loads.json")
    def get_new_loads():
        """
        Get the new loads JSON file content.

        Returns:
            dict: Contents of solution/loads/new_loads.json
        """
        try:
            # Get the project root directory (two levels up from tools/mcps)
            project_root = Path(__file__).parent.parent.parent
            new_loads_path = project_root / "solution" / "loads" / "new_loads.json"

            with open(new_loads_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            return {"error": f"Failed to load new_loads.json: {str(e)}"}

    @mcp.resource("loadsets://old_loads.json")
    def get_old_loads():
        """
        Get the old loads JSON file content.

        Returns:
            dict: Contents of solution/loads/old_loads.json
        """
        try:
            # Get the project root directory (two levels up from tools/mcps)
            project_root = Path(__file__).parent.parent.parent
            old_loads_path = project_root / "solution" / "loads" / "old_loads.json"

            with open(old_loads_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            return {"error": f"Failed to load old_loads.json: {str(e)}"}

    return mcp


def reset_global_state():
    """Reset the global LoadSet state (for backward compatibility)."""
    pass  # No longer needed with class-based approach


if __name__ == "__main__":
    import sys
    from typing import Literal

    # Allow transport to be specified via command line argument
    transport: Literal["stdio", "http"] = "http"  # Default to HTTP

    # Check for command line argument
    if len(sys.argv) > 1 and sys.argv[1] in ["stdio", "http"]:
        transport = sys.argv[1]  # type: ignore

    server = create_mcp_server()
    server.run(transport=transport)
