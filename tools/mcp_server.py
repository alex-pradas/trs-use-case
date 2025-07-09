"""
FastMCP server for LoadSet operations.

This module provides MCP tools for load data processing operations.
"""

from fastmcp import FastMCP
from pathlib import Path
from typing import Optional
from os import PathLike
import json

# Import LoadSet and related classes
from .loads import LoadSet, ForceUnit


# Global state for current LoadSet
_current_loadset: Optional[LoadSet] = None


def reset_global_state():
    """Reset the global LoadSet state."""
    global _current_loadset
    _current_loadset = None


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
                    "moments": _current_loadset.units.moments
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
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
                "error": "No LoadSet loaded. Use load_from_json first."
            }
        
        try:
            original_units = _current_loadset.units.forces
            _current_loadset = _current_loadset.convert_to(target_units)
            
            return {
                "success": True,
                "message": f"Units converted from {original_units} to {target_units}",
                "new_units": {
                    "forces": _current_loadset.units.forces,
                    "moments": _current_loadset.units.moments
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
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
                "error": "No LoadSet loaded. Use load_from_json first."
            }
        
        try:
            _current_loadset = _current_loadset.factor(factor)
            
            return {
                "success": True,
                "message": f"Loads scaled by factor {factor}",
                "scaling_factor": factor
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
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
                "error": "No LoadSet loaded. Use load_from_json first."
            }
        
        try:
            _current_loadset.to_ansys(folder_path, name_stem)
            
            return {
                "success": True,
                "message": f"ANSYS files exported to {folder_path} with stem {name_stem}",
                "num_files": len(_current_loadset.load_cases)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
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
                "error": "No LoadSet loaded. Use load_from_json first."
            }
        
        try:
            total_point_loads = sum(len(lc.point_loads) for lc in _current_loadset.load_cases)
            
            return {
                "success": True,
                "name": _current_loadset.name,
                "description": _current_loadset.description,
                "version": _current_loadset.version,
                "units": {
                    "forces": _current_loadset.units.forces,
                    "moments": _current_loadset.units.moments
                },
                "num_load_cases": len(_current_loadset.load_cases),
                "total_point_loads": total_point_loads
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
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
                "error": "No LoadSet loaded. Use load_from_json first."
            }
        
        try:
            load_cases = []
            for lc in _current_loadset.load_cases:
                load_cases.append({
                    "name": lc.name,
                    "description": lc.description,
                    "num_point_loads": len(lc.point_loads),
                    "point_load_names": [pl.name for pl in lc.point_loads]
                })
            
            return {
                "success": True,
                "load_cases": load_cases,
                "total_load_cases": len(load_cases)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    return mcp


if __name__ == "__main__":
    server = create_mcp_server()
    server.run()