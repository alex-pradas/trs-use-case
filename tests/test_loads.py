"""
Tests for the loads module.

This module tests the load file reading functionality.
"""

import pytest
import json
import tempfile
from pathlib import Path
import sys
import os

# Add tools directory to path to import loads module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
from loads import (
    read_load_file,
    get_load_cases,
    get_load_case_by_id,
    get_load_cases_by_category,
    get_metadata,
    get_units
)


class TestLoadFileReading:
    """Test load file reading functionality."""
    
    def setup_method(self):
        """Set up test data for each test method."""
        self.sample_load_data = {
            "name": "Test Load Cases",
            "version": "1.0.0",
            "units": {
                "forces": "N",
                "moments": "N·m"
            },
            "loading_type": "limit",
            "description": "Test load cases",
            "metadata": {
                "created_date": "2025-07-07",
                "coordinate_system": "global",
                "load_points": {
                    "A": {
                        "description": "Load point A",
                        "components": ["Fx", "Fy", "Fz", "Mx", "My", "Mz"]
                    },
                    "B": {
                        "description": "Load point B",
                        "components": ["Fx", "Fy", "Mx"]
                    }
                }
            },
            "load_cases": [
                {
                    "id": "Take_off_001",
                    "category": "takeoff",
                    "point_A": {
                        "Fx": 0.7608804,
                        "Fy": 0.87435622,
                        "Fz": 0.74486445,
                        "Mx": 0.89091106,
                        "My": 0.68659942,
                        "Mz": 0.9301353
                    },
                    "point_B": {
                        "Fx": 0.25933381,
                        "Fy": 0.73415377,
                        "Mx": 0.0209783
                    }
                },
                {
                    "id": "cruise1_001",
                    "category": "cruise",
                    "point_A": {
                        "Fx": 0.49695467,
                        "Fy": 0.01006604,
                        "Fz": 0.2774027,
                        "Mx": 0.12979303,
                        "My": 0.95631843,
                        "Mz": 0.77767972
                    },
                    "point_B": {
                        "Fx": 0.27851934,
                        "Fy": 0.16678269,
                        "Mx": 0.37987255
                    }
                }
            ]
        }
    
    def test_read_valid_load_file(self):
        """Test reading a valid load file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_load_data, f)
            temp_file = f.name
        
        try:
            data = read_load_file(temp_file)
            assert data['name'] == "Test Load Cases"
            assert data['version'] == "1.0.0"
            assert len(data['load_cases']) == 2
        finally:
            os.unlink(temp_file)
    
    def test_read_nonexistent_file(self):
        """Test reading a file that doesn't exist."""
        with pytest.raises(FileNotFoundError):
            read_load_file("/nonexistent/file.json")
    
    def test_read_invalid_json(self):
        """Test reading a file with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json }")
            temp_file = f.name
        
        try:
            with pytest.raises(json.JSONDecodeError):
                read_load_file(temp_file)
        finally:
            os.unlink(temp_file)
    
    def test_read_missing_required_fields(self):
        """Test reading a file missing required fields."""
        incomplete_data = {
            "name": "Test",
            "version": "1.0"
            # Missing required fields
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(incomplete_data, f)
            temp_file = f.name
        
        try:
            with pytest.raises(ValueError, match="missing required fields"):
                read_load_file(temp_file)
        finally:
            os.unlink(temp_file)
    
    def test_invalid_load_cases_type(self):
        """Test file with load_cases that is not a list."""
        invalid_data = self.sample_load_data.copy()
        invalid_data['load_cases'] = "not a list"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_data, f)
            temp_file = f.name
        
        try:
            with pytest.raises(ValueError, match="'load_cases' must be a list"):
                read_load_file(temp_file)
        finally:
            os.unlink(temp_file)
    
    def test_get_load_cases(self):
        """Test extracting load cases from data."""
        cases = get_load_cases(self.sample_load_data)
        assert len(cases) == 2
        assert cases[0]['id'] == "Take_off_001"
        assert cases[1]['id'] == "cruise1_001"
    
    def test_get_load_case_by_id(self):
        """Test getting a specific load case by ID."""
        case = get_load_case_by_id(self.sample_load_data, "Take_off_001")
        assert case['category'] == "takeoff"
        assert case['point_A']['Fx'] == 0.7608804
        
        with pytest.raises(ValueError, match="Load case with ID 'nonexistent' not found"):
            get_load_case_by_id(self.sample_load_data, "nonexistent")
    
    def test_get_load_cases_by_category(self):
        """Test getting load cases by category."""
        takeoff_cases = get_load_cases_by_category(self.sample_load_data, "takeoff")
        assert len(takeoff_cases) == 1
        assert takeoff_cases[0]['id'] == "Take_off_001"
        
        cruise_cases = get_load_cases_by_category(self.sample_load_data, "cruise")
        assert len(cruise_cases) == 1
        assert cruise_cases[0]['id'] == "cruise1_001"
        
        landing_cases = get_load_cases_by_category(self.sample_load_data, "landing")
        assert len(landing_cases) == 0
    
    def test_get_metadata(self):
        """Test extracting metadata from data."""
        metadata = get_metadata(self.sample_load_data)
        assert metadata['created_date'] == "2025-07-07"
        assert metadata['coordinate_system'] == "global"
        assert 'load_points' in metadata
    
    def test_get_units(self):
        """Test extracting units from data."""
        units = get_units(self.sample_load_data)
        assert units['forces'] == "N"
        assert units['moments'] == "N·m"


class TestRealLoadFiles:
    """Test with real load files from the project."""
    
    def test_read_new_loads_file(self):
        """Test reading the new_loads file."""
        new_loads_path = Path(__file__).parent.parent / "solution" / "loads" / "new_loads.json"
        
        if new_loads_path.exists():
            data = read_load_file(new_loads_path)
            assert data['name'] == "Flight Test Loads"
            assert data['version'] == 1
            assert data['units']['forces'] == "klbs"
            
            load_cases = get_load_cases(data)
            assert len(load_cases) > 0
            
            # Test specific load case
            takeoff_case = get_load_case_by_id(data, "Take_off_004")
            assert takeoff_case['category'] == "takeoff"
            
            # Test category filtering
            takeoff_cases = get_load_cases_by_category(data, "takeoff")
            cruise_cases = get_load_cases_by_category(data, "cruise")
            landing_cases = get_load_cases_by_category(data, "landing")
            
            assert len(takeoff_cases) > 0
            assert len(cruise_cases) > 0
            assert len(landing_cases) > 0
            
            print(f"✅ new_loads: {len(takeoff_cases)} takeoff, {len(cruise_cases)} cruise, {len(landing_cases)} landing cases")
    
    def test_read_old_loads_file(self):
        """Test reading the old_loads file."""
        old_loads_path = Path(__file__).parent.parent / "solution" / "loads" / "old_loads.json"
        
        if old_loads_path.exists():
            data = read_load_file(old_loads_path)
            assert data['name'] == "Aerospace Structural Load Cases"
            assert data['version'] == "1.0.0"
            assert data['units']['forces'] == "N"
            
            load_cases = get_load_cases(data)
            assert len(load_cases) > 0
            
            # Test specific load case
            takeoff_case = get_load_case_by_id(data, "Take_off_004")
            assert takeoff_case['category'] == "takeoff"
            
            # Test category filtering
            takeoff_cases = get_load_cases_by_category(data, "takeoff")
            cruise_cases = get_load_cases_by_category(data, "cruise")
            landing_cases = get_load_cases_by_category(data, "landing")
            
            assert len(takeoff_cases) > 0
            assert len(cruise_cases) > 0
            assert len(landing_cases) > 0
            
            print(f"✅ old_loads: {len(takeoff_cases)} takeoff, {len(cruise_cases)} cruise, {len(landing_cases)} landing cases")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])