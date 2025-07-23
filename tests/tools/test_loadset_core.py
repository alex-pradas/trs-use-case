"""
Tests for LoadSet core functionality.

This module consolidates all LoadSet-related tests including:
- Core functionality (read, convert, scale, export)
- Comparison functionality
- Envelope functionality
"""

import pytest
import json
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


# Test imports from tools package to cover __init__.py
def test_tools_package_imports():
    """Test that we can import from the tools package."""
    import sys
    from pathlib import Path

    # Add parent dir to path so we can import tools as a package
    parent_dir = Path(__file__).parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))

    # This should work and cover the __init__.py imports
    from tools import LoadSet, LoadCase, PointLoad, ForceMoment, Units

    assert LoadSet is not None
    assert LoadCase is not None
    assert PointLoad is not None
    assert ForceMoment is not None
    assert Units is not None

    # Check that __all__ is properly defined
    import tools

    assert hasattr(tools, "__all__")
    assert "LoadSet" in tools.__all__
    assert "LoadCase" in tools.__all__
    assert "PointLoad" in tools.__all__
    assert "ForceMoment" in tools.__all__
    assert "Units" in tools.__all__


# =============================================================================
# CORE FUNCTIONALITY TESTS
# =============================================================================


class TestLoadSetReadJson:
    """Test LoadSet.read_json() classmethod."""

    def setup_method(self):
        """Set up test data for each test method."""
        self.sample_loadset_data = {
            "name": "Test Load Set",
            "version": 1,
            "description": "Test load set for unit testing",
            "units": {"forces": "N", "moments": "Nm"},
            "load_cases": [
                {
                    "name": "Test Case 1",
                    "description": "First test case",
                    "point_loads": [
                        {
                            "name": "Point A",
                            "force_moment": {
                                "fx": 100.0,
                                "fy": 200.0,
                                "fz": 300.0,
                                "mx": 50.0,
                                "my": 75.0,
                                "mz": 100.0,
                            },
                        },
                        {
                            "name": "Point B",
                            "force_moment": {
                                "fx": 150.0,
                                "fy": 250.0,
                                "fz": 0.0,
                                "mx": 60.0,
                                "my": 0.0,
                                "mz": 0.0,
                            },
                        },
                    ],
                },
                {
                    "name": "Test Case 2",
                    "description": "Second test case",
                    "point_loads": [
                        {
                            "name": "Point A",
                            "force_moment": {
                                "fx": 80.0,
                                "fy": 120.0,
                                "fz": 160.0,
                                "mx": 40.0,
                                "my": 60.0,
                                "mz": 80.0,
                            },
                        }
                    ],
                },
            ],
        }

    def test_read_json_valid_file(self):
        """Test reading a valid JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.sample_loadset_data, f)
            temp_file = f.name

        try:
            load_set = LoadSet.read_json(temp_file)

            # Check basic properties
            assert load_set.name == "Test Load Set"
            assert load_set.version == 1
            assert load_set.description == "Test load set for unit testing"
            assert load_set.units.forces == "N"
            assert load_set.units.moments == "Nm"

            # Check load cases
            assert len(load_set.load_cases) == 2
            assert load_set.load_cases[0].name == "Test Case 1"
            assert load_set.load_cases[1].name == "Test Case 2"

            # Check point loads
            assert len(load_set.load_cases[0].point_loads) == 2
            assert len(load_set.load_cases[1].point_loads) == 1

            # Check force/moment values
            point_a = load_set.load_cases[0].point_loads[0]
            assert point_a.name == "Point A"
            assert point_a.force_moment.fx == 100.0
            assert point_a.force_moment.fy == 200.0
            assert point_a.force_moment.fz == 300.0
            assert point_a.force_moment.mx == 50.0
            assert point_a.force_moment.my == 75.0
            assert point_a.force_moment.mz == 100.0

        finally:
            os.unlink(temp_file)

    def test_read_json_nonexistent_file(self):
        """Test reading a file that doesn't exist."""
        with pytest.raises(FileNotFoundError):
            LoadSet.read_json("/nonexistent/file.json")

    def test_read_json_invalid_json(self):
        """Test reading a file with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            temp_file = f.name

        try:
            with pytest.raises(json.JSONDecodeError):
                LoadSet.read_json(temp_file)
        finally:
            os.unlink(temp_file)

    def test_read_json_invalid_schema(self):
        """Test reading a file with invalid schema."""
        invalid_data = {
            "name": "Test",
            "version": 1,
            "units": {
                "forces": "InvalidUnit",  # Invalid unit
                "moments": "Nm",
            },
            "load_cases": [],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(invalid_data, f)
            temp_file = f.name

        try:
            with pytest.raises(ValueError):
                LoadSet.read_json(temp_file)
        finally:
            os.unlink(temp_file)

    def test_read_json_missing_required_fields(self):
        """Test reading a file missing required fields."""
        incomplete_data = {
            "name": "Test",
            # Missing version, units, load_cases
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(incomplete_data, f)
            temp_file = f.name

        try:
            with pytest.raises(ValueError):
                LoadSet.read_json(temp_file)
        finally:
            os.unlink(temp_file)

    def test_read_json_path_like_object(self):
        """Test reading with Path-like object."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.sample_loadset_data, f)
            temp_file = Path(f.name)

        try:
            load_set = LoadSet.read_json(temp_file)
            assert load_set.name == "Test Load Set"
        finally:
            os.unlink(temp_file)

    def test_read_json_actual_new_loads_file(self):
        """Test reading the actual new_loads file."""
        new_loads_path = (
            Path(__file__).parent.parent / "solution" / "loads" / "new_loads.json"
        )

        if new_loads_path.exists():
            load_set = LoadSet.read_json(new_loads_path)

            # Check basic properties
            assert load_set.name == "Aerospace Structural Load Cases"
            assert load_set.version == 1
            assert load_set.units.forces == "N"
            assert load_set.units.moments == "Nm"

            # Should have multiple load cases
            assert len(load_set.load_cases) > 0

            # Each load case should have point loads
            for load_case in load_set.load_cases:
                assert len(load_case.point_loads) > 0

                # Each point load should have force/moment data
                for point_load in load_case.point_loads:
                    assert point_load.force_moment is not None
                    assert hasattr(point_load.force_moment, "fx")
                    assert hasattr(point_load.force_moment, "fy")
                    assert hasattr(point_load.force_moment, "fz")
                    assert hasattr(point_load.force_moment, "mx")
                    assert hasattr(point_load.force_moment, "my")
                    assert hasattr(point_load.force_moment, "mz")


class TestLoadSetConvertTo:
    """Test LoadSet.convert_to() method."""

    def setup_method(self):
        """Set up test data for each test method."""
        self.sample_loadset = LoadSet(
            name="Test Load Set",
            version=1,
            description="Test load set for unit conversion",
            units=Units(forces="N", moments="Nm"),
            load_cases=[
                LoadCase(
                    name="Test Case 1",
                    description="Test case with known values",
                    point_loads=[
                        PointLoad(
                            name="Point A",
                            force_moment=ForceMoment(
                                fx=1000.0,  # 1000 N
                                fy=2000.0,  # 2000 N
                                fz=3000.0,  # 3000 N
                                mx=100.0,  # 100 Nm
                                my=200.0,  # 200 Nm
                                mz=300.0,  # 300 Nm
                            ),
                        ),
                        PointLoad(
                            name="Point B",
                            force_moment=ForceMoment(
                                fx=500.0,  # 500 N
                                fy=1000.0,  # 1000 N
                                fz=0.0,
                                mx=50.0,  # 50 Nm
                                my=0.0,
                                mz=0.0,
                            ),
                        ),
                    ],
                )
            ],
        )

    def test_convert_to_same_units(self):
        """Test converting to the same units (should return copy)."""
        converted = self.sample_loadset.convert_to("N")

        # Should be a different instance
        assert converted is not self.sample_loadset

        # But with same values
        assert converted.units.forces == "N"
        assert converted.units.moments == "Nm"

        # Force values should be unchanged
        point_a = converted.load_cases[0].point_loads[0]
        assert point_a.force_moment.fx == 1000.0
        assert point_a.force_moment.fy == 2000.0
        assert point_a.force_moment.fz == 3000.0
        assert point_a.force_moment.mx == 100.0
        assert point_a.force_moment.my == 200.0
        assert point_a.force_moment.mz == 300.0

    def test_convert_to_kN(self):
        """Test converting from N to kN."""
        converted = self.sample_loadset.convert_to("kN")

        assert converted.units.forces == "kN"
        assert converted.units.moments == "kNm"

        # Force values should be divided by 1000
        point_a = converted.load_cases[0].point_loads[0]
        assert point_a.force_moment.fx == 1.0  # 1000 N -> 1 kN
        assert point_a.force_moment.fy == 2.0  # 2000 N -> 2 kN
        assert point_a.force_moment.fz == 3.0  # 3000 N -> 3 kN
        assert point_a.force_moment.mx == 0.1  # 100 Nm -> 0.1 kNm
        assert point_a.force_moment.my == 0.2  # 200 Nm -> 0.2 kNm
        assert point_a.force_moment.mz == 0.3  # 300 Nm -> 0.3 kNm

        # Point B
        point_b = converted.load_cases[0].point_loads[1]
        assert point_b.force_moment.fx == 0.5  # 500 N -> 0.5 kN
        assert point_b.force_moment.fy == 1.0  # 1000 N -> 1 kN
        assert point_b.force_moment.mx == 0.05  # 50 Nm -> 0.05 kNm

    def test_convert_to_lbf(self):
        """Test converting from N to lbf."""
        converted = self.sample_loadset.convert_to("lbf")

        assert converted.units.forces == "lbf"
        assert converted.units.moments == "lbf-ft"

        # Force values should be multiplied by ~4.448 (N to lbf conversion)
        point_a = converted.load_cases[0].point_loads[0]
        assert abs(point_a.force_moment.fx - 224.809) < 0.001  # 1000 N -> ~224.809 lbf
        assert abs(point_a.force_moment.fy - 449.618) < 0.001  # 2000 N -> ~449.618 lbf
        assert abs(point_a.force_moment.fz - 674.427) < 0.001  # 3000 N -> ~674.427 lbf

        # Moment values should be converted from Nm to lbf-ft
        assert abs(point_a.force_moment.mx - 73.756) < 0.001  # 100 Nm -> ~73.756 lbf-ft
        assert (
            abs(point_a.force_moment.my - 147.513) < 0.001
        )  # 200 Nm -> ~147.513 lbf-ft
        assert (
            abs(point_a.force_moment.mz - 221.269) < 0.001
        )  # 300 Nm -> ~221.269 lbf-ft

    def test_convert_to_klbf(self):
        """Test converting from N to klbf."""
        converted = self.sample_loadset.convert_to("klbf")

        assert converted.units.forces == "klbf"
        assert converted.units.moments == "lbf-ft"

        # Force values should be converted to klbf
        point_a = converted.load_cases[0].point_loads[0]
        assert (
            abs(point_a.force_moment.fx - 0.224809) < 0.000001
        )  # 1000 N -> ~0.224809 klbf
        assert (
            abs(point_a.force_moment.fy - 0.449618) < 0.000001
        )  # 2000 N -> ~0.449618 klbf
        assert (
            abs(point_a.force_moment.fz - 0.674427) < 0.000001
        )  # 3000 N -> ~0.674427 klbf

    def test_convert_invalid_units(self):
        """Test converting to invalid units."""
        with pytest.raises(ValueError, match="Unsupported force unit"):
            self.sample_loadset.convert_to("InvalidUnit")

    def test_convert_preserves_metadata(self):
        """Test that conversion preserves all metadata."""
        converted = self.sample_loadset.convert_to("kN")

        # Check that all metadata is preserved
        assert converted.name == self.sample_loadset.name
        assert converted.version == self.sample_loadset.version
        assert converted.description == self.sample_loadset.description

        # Check load case metadata
        assert len(converted.load_cases) == len(self.sample_loadset.load_cases)
        assert converted.load_cases[0].name == self.sample_loadset.load_cases[0].name
        assert (
            converted.load_cases[0].description
            == self.sample_loadset.load_cases[0].description
        )

        # Check point load metadata
        assert len(converted.load_cases[0].point_loads) == len(
            self.sample_loadset.load_cases[0].point_loads
        )
        assert (
            converted.load_cases[0].point_loads[0].name
            == self.sample_loadset.load_cases[0].point_loads[0].name
        )
        assert (
            converted.load_cases[0].point_loads[1].name
            == self.sample_loadset.load_cases[0].point_loads[1].name
        )

    def test_convert_chain_conversions(self):
        """Test chaining multiple conversions."""
        # N -> kN -> lbf
        converted1 = self.sample_loadset.convert_to("kN")
        converted2 = converted1.convert_to("lbf")

        assert converted2.units.forces == "lbf"
        assert converted2.units.moments == "lbf-ft"

        # Should be approximately the same as direct N -> lbf conversion
        direct_conversion = self.sample_loadset.convert_to("lbf")

        point_a_chain = converted2.load_cases[0].point_loads[0]
        point_a_direct = direct_conversion.load_cases[0].point_loads[0]

        assert (
            abs(point_a_chain.force_moment.fx - point_a_direct.force_moment.fx) < 0.001
        )
        assert (
            abs(point_a_chain.force_moment.fy - point_a_direct.force_moment.fy) < 0.001
        )
        assert (
            abs(point_a_chain.force_moment.fz - point_a_direct.force_moment.fz) < 0.001
        )


class TestLoadSetFactor:
    """Test LoadSet.factor() method."""

    def setup_method(self):
        """Set up test data for each test method."""
        self.sample_loadset = LoadSet(
            name="Test Load Set",
            version=1,
            description="Test load set for scaling",
            units=Units(forces="N", moments="Nm"),
            load_cases=[
                LoadCase(
                    name="Test Case 1",
                    description="Test case with known values",
                    point_loads=[
                        PointLoad(
                            name="Point A",
                            force_moment=ForceMoment(
                                fx=100.0, fy=200.0, fz=300.0, mx=50.0, my=75.0, mz=100.0
                            ),
                        ),
                        PointLoad(
                            name="Point B",
                            force_moment=ForceMoment(
                                fx=80.0, fy=160.0, fz=0.0, mx=40.0, my=0.0, mz=0.0
                            ),
                        ),
                    ],
                ),
                LoadCase(
                    name="Test Case 2",
                    description="Second test case",
                    point_loads=[
                        PointLoad(
                            name="Point C",
                            force_moment=ForceMoment(
                                fx=60.0, fy=120.0, fz=180.0, mx=30.0, my=45.0, mz=60.0
                            ),
                        )
                    ],
                ),
            ],
        )

    def test_factor_by_two(self):
        """Test scaling by factor of 2."""
        factored = self.sample_loadset.factor(2.0)

        # Should be a different instance
        assert factored is not self.sample_loadset

        # Units should remain the same
        assert factored.units.forces == "N"
        assert factored.units.moments == "Nm"

        # All values should be doubled
        point_a = factored.load_cases[0].point_loads[0]
        assert point_a.force_moment.fx == 200.0  # 100 * 2
        assert point_a.force_moment.fy == 400.0  # 200 * 2
        assert point_a.force_moment.fz == 600.0  # 300 * 2
        assert point_a.force_moment.mx == 100.0  # 50 * 2
        assert point_a.force_moment.my == 150.0  # 75 * 2
        assert point_a.force_moment.mz == 200.0  # 100 * 2

        # Point B
        point_b = factored.load_cases[0].point_loads[1]
        assert point_b.force_moment.fx == 160.0  # 80 * 2
        assert point_b.force_moment.fy == 320.0  # 160 * 2
        assert point_b.force_moment.fz == 0.0  # 0 * 2
        assert point_b.force_moment.mx == 80.0  # 40 * 2
        assert point_b.force_moment.my == 0.0  # 0 * 2
        assert point_b.force_moment.mz == 0.0  # 0 * 2

        # Point C (second load case)
        point_c = factored.load_cases[1].point_loads[0]
        assert point_c.force_moment.fx == 120.0  # 60 * 2
        assert point_c.force_moment.fy == 240.0  # 120 * 2
        assert point_c.force_moment.fz == 360.0  # 180 * 2
        assert point_c.force_moment.mx == 60.0  # 30 * 2
        assert point_c.force_moment.my == 90.0  # 45 * 2
        assert point_c.force_moment.mz == 120.0  # 60 * 2

    def test_factor_by_half(self):
        """Test scaling by factor of 0.5."""
        factored = self.sample_loadset.factor(0.5)

        # All values should be halved
        point_a = factored.load_cases[0].point_loads[0]
        assert point_a.force_moment.fx == 50.0  # 100 * 0.5
        assert point_a.force_moment.fy == 100.0  # 200 * 0.5
        assert point_a.force_moment.fz == 150.0  # 300 * 0.5
        assert point_a.force_moment.mx == 25.0  # 50 * 0.5
        assert point_a.force_moment.my == 37.5  # 75 * 0.5
        assert point_a.force_moment.mz == 50.0  # 100 * 0.5

    def test_factor_by_zero(self):
        """Test scaling by factor of 0."""
        factored = self.sample_loadset.factor(0.0)

        # All values should be zero
        point_a = factored.load_cases[0].point_loads[0]
        assert point_a.force_moment.fx == 0.0
        assert point_a.force_moment.fy == 0.0
        assert point_a.force_moment.fz == 0.0
        assert point_a.force_moment.mx == 0.0
        assert point_a.force_moment.my == 0.0
        assert point_a.force_moment.mz == 0.0

    def test_factor_by_negative(self):
        """Test scaling by negative factor."""
        factored = self.sample_loadset.factor(-1.5)

        # All values should be negative and scaled by 1.5
        point_a = factored.load_cases[0].point_loads[0]
        assert point_a.force_moment.fx == -150.0  # 100 * -1.5
        assert point_a.force_moment.fy == -300.0  # 200 * -1.5
        assert point_a.force_moment.fz == -450.0  # 300 * -1.5
        assert point_a.force_moment.mx == -75.0  # 50 * -1.5
        assert point_a.force_moment.my == -112.5  # 75 * -1.5
        assert point_a.force_moment.mz == -150.0  # 100 * -1.5

    def test_factor_by_one(self):
        """Test scaling by factor of 1 (should be unchanged)."""
        factored = self.sample_loadset.factor(1.0)

        # Should be a different instance
        assert factored is not self.sample_loadset

        # But values should be the same
        point_a_orig = self.sample_loadset.load_cases[0].point_loads[0]
        point_a_fact = factored.load_cases[0].point_loads[0]

        assert point_a_fact.force_moment.fx == point_a_orig.force_moment.fx
        assert point_a_fact.force_moment.fy == point_a_orig.force_moment.fy
        assert point_a_fact.force_moment.fz == point_a_orig.force_moment.fz
        assert point_a_fact.force_moment.mx == point_a_orig.force_moment.mx
        assert point_a_fact.force_moment.my == point_a_orig.force_moment.my
        assert point_a_fact.force_moment.mz == point_a_orig.force_moment.mz

    def test_factor_preserves_metadata(self):
        """Test that factoring preserves all metadata."""
        factored = self.sample_loadset.factor(2.0)

        # Check that all metadata is preserved
        assert factored.name == self.sample_loadset.name
        assert factored.version == self.sample_loadset.version
        assert factored.description == self.sample_loadset.description
        assert factored.units.forces == self.sample_loadset.units.forces
        assert factored.units.moments == self.sample_loadset.units.moments

        # Check load case metadata
        assert len(factored.load_cases) == len(self.sample_loadset.load_cases)
        for i, (orig_case, fact_case) in enumerate(
            zip(self.sample_loadset.load_cases, factored.load_cases)
        ):
            assert fact_case.name == orig_case.name
            assert fact_case.description == orig_case.description

            # Check point load metadata
            assert len(fact_case.point_loads) == len(orig_case.point_loads)
            for j, (orig_point, fact_point) in enumerate(
                zip(orig_case.point_loads, fact_case.point_loads)
            ):
                assert fact_point.name == orig_point.name

    def test_factor_with_different_units(self):
        """Test factoring with different unit systems."""
        # Create a LoadSet with kN units
        kn_loadset = self.sample_loadset.convert_to("kN")
        factored = kn_loadset.factor(3.0)

        # Units should be preserved
        assert factored.units.forces == "kN"
        assert factored.units.moments == "kNm"

        # Values should be scaled appropriately
        point_a = factored.load_cases[0].point_loads[0]
        # Original 100 N becomes 0.1 kN, then * 3 = 0.3 kN
        assert abs(point_a.force_moment.fx - 0.3) < 1e-10
        # Original 200 N becomes 0.2 kN, then * 3 = 0.6 kN
        assert abs(point_a.force_moment.fy - 0.6) < 1e-10

    def test_factor_chain_operations(self):
        """Test chaining factor operations."""
        # Factor by 2, then by 3 (should be same as factor by 6)
        factored1 = self.sample_loadset.factor(2.0)
        factored2 = factored1.factor(3.0)

        # Should be same as direct factor by 6
        direct_factored = self.sample_loadset.factor(6.0)

        point_a_chain = factored2.load_cases[0].point_loads[0]
        point_a_direct = direct_factored.load_cases[0].point_loads[0]

        assert point_a_chain.force_moment.fx == point_a_direct.force_moment.fx
        assert point_a_chain.force_moment.fy == point_a_direct.force_moment.fy
        assert point_a_chain.force_moment.fz == point_a_direct.force_moment.fz
        assert point_a_chain.force_moment.mx == point_a_direct.force_moment.mx
        assert point_a_chain.force_moment.my == point_a_direct.force_moment.my
        assert point_a_chain.force_moment.mz == point_a_direct.force_moment.mz


class TestLoadSetToAnsys:
    """Test LoadSet.to_ansys() method."""

    def setup_method(self):
        """Set up test data for each test method."""
        self.sample_loadset = LoadSet(
            name="Test Load Set",
            version=1,
            description="Test load set for ANSYS export",
            units=Units(forces="N", moments="Nm"),
            load_cases=[
                LoadCase(
                    name="Load_Case_1",
                    description="First load case",
                    point_loads=[
                        PointLoad(
                            name="Node_1001",
                            force_moment=ForceMoment(
                                fx=1000.0,
                                fy=2000.0,
                                fz=3000.0,
                                mx=100.0,
                                my=200.0,
                                mz=300.0,
                            ),
                        ),
                        PointLoad(
                            name="Node_1002",
                            force_moment=ForceMoment(
                                fx=500.0, fy=1000.0, fz=0.0, mx=50.0, my=0.0, mz=0.0
                            ),
                        ),
                    ],
                ),
                LoadCase(
                    name="Load_Case_2",
                    description="Second load case",
                    point_loads=[
                        PointLoad(
                            name="Node_1003",
                            force_moment=ForceMoment(
                                fx=800.0,
                                fy=1200.0,
                                fz=1600.0,
                                mx=80.0,
                                my=120.0,
                                mz=160.0,
                            ),
                        )
                    ],
                ),
            ],
        )

    def test_to_ansys_creates_files(self):
        """Test that to_ansys creates the expected files."""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as temp_dir:
            # Export to ANSYS
            self.sample_loadset.to_ansys(temp_dir, "test_loads")

            # Check that files were created
            expected_files = [
                "test_loads_Load_Case_1.inp",
                "test_loads_Load_Case_2.inp",
            ]

            for expected_file in expected_files:
                file_path = os.path.join(temp_dir, expected_file)
                assert os.path.exists(file_path), (
                    f"Expected file {expected_file} was not created"
                )

    def test_to_ansys_file_content_format(self):
        """Test that ANSYS files have correct format."""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as temp_dir:
            # Export to ANSYS
            self.sample_loadset.to_ansys(temp_dir, "test_loads")

            # Read the first load case file
            file_path = os.path.join(temp_dir, "test_loads_Load_Case_1.inp")
            with open(file_path, "r") as f:
                content = f.read()

            # Check that content contains expected ANSYS commands
            assert "/TITLE,Load_Case_1" in content
            assert "nsel,u,,,all" in content
            assert "alls" in content

            # Check for force/moment commands with pilot_ prefix
            assert "cmsel,s,pilot_Node_1001" in content
            assert "f,all,fx,1.000e+03" in content
            assert "f,all,fy,2.000e+03" in content
            assert "f,all,fz,3.000e+03" in content
            assert "f,all,mx,1.000e+02" in content
            assert "f,all,my,2.000e+02" in content
            assert "f,all,mz,3.000e+02" in content

            assert "cmsel,s,pilot_Node_1002" in content
            assert "f,all,fx,5.000e+02" in content
            assert "f,all,fy,1.000e+03" in content
            # Zero values should not be written
            assert "f,all,fz,0.000e+00" not in content
            assert "f,all,my,0.000e+00" not in content
            assert "f,all,mz,0.000e+00" not in content

    def test_to_ansys_with_different_units(self):
        """Test ANSYS export with different units."""
        import tempfile
        import os

        # Convert to kN and export
        kn_loadset = self.sample_loadset.convert_to("kN")

        with tempfile.TemporaryDirectory() as temp_dir:
            kn_loadset.to_ansys(temp_dir, "kn_loads")

            file_path = os.path.join(temp_dir, "kn_loads_Load_Case_1.inp")
            with open(file_path, "r") as f:
                content = f.read()

            # Check title command
            assert "/TITLE,Load_Case_1" in content

            # Check converted values (1000 N = 1 kN)
            assert "f,all,fx,1.000e+00" in content
            assert "f,all,fy,2.000e+00" in content
            assert "f,all,fz,3.000e+00" in content

    def test_to_ansys_creates_folder(self):
        """Test to_ansys creates folder if it doesn't exist."""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as temp_dir:
            # Use a non-existent subfolder
            test_folder = os.path.join(temp_dir, "new_folder")
            assert not os.path.exists(test_folder)

            # Export to ANSYS - should create the folder
            self.sample_loadset.to_ansys(test_folder, "test_loads")  # type: ignore

            # Check that folder was created and files exist
            assert os.path.exists(test_folder)
            assert os.path.isdir(test_folder)
            files = os.listdir(test_folder)
            assert len(files) == 2  # Two load cases

    def test_to_ansys_with_file_path(self):
        """Test to_ansys when given a file path instead of directory."""
        import tempfile

        with tempfile.NamedTemporaryFile() as temp_file:
            # Pass a file path instead of directory path
            with pytest.raises(
                FileNotFoundError, match="Path exists but is not a directory"
            ):
                self.sample_loadset.to_ansys(temp_file.name, "test")

    def test_to_ansys_empty_loadset(self):
        """Test ANSYS export with empty load cases."""
        empty_loadset = LoadSet(
            name="Empty Load Set",
            version=1,
            units=Units(forces="N", moments="Nm"),
            load_cases=[],
        )

        import tempfile
        import os

        with tempfile.TemporaryDirectory() as temp_dir:
            empty_loadset.to_ansys(temp_dir, "empty")

            # Should not create any files
            files = os.listdir(temp_dir)
            assert len(files) == 0

    def test_to_ansys_cleans_existing_files(self):
        """Test to_ansys cleans existing files before creating new ones."""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some existing files
            existing_file1 = os.path.join(temp_dir, "old_file1.txt")
            existing_file2 = os.path.join(temp_dir, "old_file2.inp")

            with open(existing_file1, "w") as f:
                f.write("old content")
            with open(existing_file2, "w") as f:
                f.write("old ansys file")

            # Verify files exist
            assert os.path.exists(existing_file1)
            assert os.path.exists(existing_file2)
            assert len(os.listdir(temp_dir)) == 2

            # Export to ANSYS - should clean existing files
            self.sample_loadset.to_ansys(temp_dir, "test_loads")

            # Check that old files were removed and new files created
            files = os.listdir(temp_dir)
            assert len(files) == 2  # Only the new ANSYS files
            assert "old_file1.txt" not in files
            assert "old_file2.inp" not in files
            assert "test_loads_Load_Case_1.inp" in files
            assert "test_loads_Load_Case_2.inp" in files

    def test_to_ansys_special_characters_in_names(self):
        """Test ANSYS export with special characters in names."""
        special_loadset = LoadSet(
            name="Special Load Set",
            version=1,
            units=Units(forces="N", moments="Nm"),
            load_cases=[
                LoadCase(
                    name="Load Case-1 (Test)",
                    description="Case with special chars",
                    point_loads=[
                        PointLoad(
                            name="Node-1001",
                            force_moment=ForceMoment(
                                fx=100.0, fy=0.0, fz=0.0, mx=0.0, my=0.0, mz=0.0
                            ),
                        )
                    ],
                )
            ],
        )

        import tempfile
        import os

        with tempfile.TemporaryDirectory() as temp_dir:
            special_loadset.to_ansys(temp_dir, "special")

            # Check that file was created with sanitized name
            files = os.listdir(temp_dir)
            assert len(files) == 1

            # File name should have special characters replaced
            # The actual sanitization keeps hyphens, so we expect "Load_Case-1_Test"
            expected_filename = "special_Load_Case-1_Test.inp"
            assert expected_filename in files

    def test_to_ansys_with_pathlib_path(self):
        """Test to_ansys with Path object."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            path_obj = Path(temp_dir)
            self.sample_loadset.to_ansys(path_obj, "pathlib_test")

            # Check that files were created
            files = list(path_obj.glob("pathlib_test_*.inp"))
            assert len(files) == 2


# =============================================================================
# COMPARISON FUNCTIONALITY TESTS
# =============================================================================


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


# =============================================================================
# ENVELOPE FUNCTIONALITY TESTS
# =============================================================================


class TestLoadSetEnvelope:
    """Test LoadSet.envelope() method."""

    def setup_method(self):
        """Set up test data for each test method."""
        # Create a comprehensive test LoadSet with mixed positive/negative values
        self.sample_loadset = LoadSet(
            name="Test Envelope LoadSet",
            version=1,
            description="Test load set for envelope functionality",
            units=Units(forces="N", moments="Nm"),
            load_cases=[
                LoadCase(
                    name="Case_Max_Fx",  # Will have max fx at Point_A
                    description="Load case with maximum fx",
                    point_loads=[
                        PointLoad(
                            name="Point_A",
                            force_moment=ForceMoment(
                                fx=1000.0,  # MAX for Point_A fx
                                fy=100.0,
                                fz=50.0,
                                mx=10.0,
                                my=20.0,
                                mz=30.0,
                            ),
                        ),
                        PointLoad(
                            name="Point_B",
                            force_moment=ForceMoment(
                                fx=200.0,
                                fy=300.0,
                                fz=400.0,
                                mx=25.0,
                                my=35.0,
                                mz=45.0,
                            ),
                        ),
                    ],
                ),
                LoadCase(
                    name="Case_Min_Fx",  # Will have min fx at Point_A (negative)
                    description="Load case with negative minimum fx",
                    point_loads=[
                        PointLoad(
                            name="Point_A",
                            force_moment=ForceMoment(
                                fx=-500.0,  # MIN for Point_A fx (negative, should be included)
                                fy=150.0,
                                fz=75.0,
                                mx=15.0,
                                my=25.0,
                                mz=35.0,
                            ),
                        ),
                        PointLoad(
                            name="Point_B",
                            force_moment=ForceMoment(
                                fx=100.0,
                                fy=800.0,  # MAX for Point_B fy
                                fz=200.0,
                                mx=30.0,
                                my=40.0,
                                mz=50.0,
                            ),
                        ),
                    ],
                ),
                LoadCase(
                    name="Case_Positive_Min",  # Has positive min values (should not be included for mins)
                    description="Load case with positive minimum values",
                    point_loads=[
                        PointLoad(
                            name="Point_A",
                            force_moment=ForceMoment(
                                fx=200.0,  # Positive min (should not be included as min)
                                fy=50.0,  # MIN for Point_A fy (positive, should not be included)
                                fz=800.0,  # MAX for Point_A fz
                                mx=-100.0,  # MIN for Point_A mx (negative, should be included)
                                my=10.0,  # MIN for Point_A my (positive, should not be included)
                                mz=200.0,  # MAX for Point_A mz
                            ),
                        ),
                    ],
                ),
                LoadCase(
                    name="Case_Not_Extreme",  # No extreme values, should not be included
                    description="Load case with no extreme values",
                    point_loads=[
                        PointLoad(
                            name="Point_A",
                            force_moment=ForceMoment(
                                fx=300.0,  # Between min and max
                                fy=125.0,  # Between min and max
                                fz=100.0,  # Between min and max
                                mx=12.0,  # Between min and max (not 50.0 which would be max)
                                my=15.0,  # Between min and max
                                mz=100.0,  # Between min and max
                            ),
                        ),
                    ],
                ),
            ],
        )

    def test_envelope_basic_functionality(self):
        """Test basic envelope functionality."""
        envelope_loadset = self.sample_loadset.envelope()

        # Should be a different instance
        assert envelope_loadset is not self.sample_loadset

        # Should have fewer load cases (envelope should filter out non-extreme cases)
        assert len(envelope_loadset.load_cases) <= len(self.sample_loadset.load_cases)
        assert len(envelope_loadset.load_cases) > 0

        # Should preserve metadata
        assert envelope_loadset.name == self.sample_loadset.name
        assert envelope_loadset.version == self.sample_loadset.version
        assert envelope_loadset.description == self.sample_loadset.description
        assert envelope_loadset.units.forces == self.sample_loadset.units.forces
        assert envelope_loadset.units.moments == self.sample_loadset.units.moments

    def test_envelope_includes_correct_cases(self):
        """Test that envelope includes the correct extreme cases."""
        envelope_loadset = self.sample_loadset.envelope()

        # Get load case names in envelope
        envelope_case_names = {lc.name for lc in envelope_loadset.load_cases}

        # Should include Case_Max_Fx (has max fx for Point_A)
        assert "Case_Max_Fx" in envelope_case_names

        # Should include Case_Min_Fx (has negative min fx for Point_A and max fy for Point_B)
        assert "Case_Min_Fx" in envelope_case_names

        # Should include Case_Positive_Min (has max fz and mz for Point_A, and negative min mx)
        assert "Case_Positive_Min" in envelope_case_names

        # Should NOT include Case_Not_Extreme (has no extreme values)
        assert "Case_Not_Extreme" not in envelope_case_names

    def test_envelope_extremes_logic(self):
        """Test that envelope correctly identifies extreme values."""
        # Create specific test case to validate the logic
        extremes = self.sample_loadset.get_point_extremes()

        # Point_A extremes
        point_a = extremes["Point_A"]

        # fx: max = 1000 (Case_Max_Fx), min = -500 (Case_Min_Fx, negative - should include)
        assert point_a["fx"]["max"]["value"] == 1000.0
        assert point_a["fx"]["max"]["loadcase"] == "Case_Max_Fx"
        assert point_a["fx"]["min"]["value"] == -500.0
        assert point_a["fx"]["min"]["loadcase"] == "Case_Min_Fx"

        # fy: max = 150 (Case_Min_Fx), min = 50 (Case_Positive_Min, positive - should not include)
        assert point_a["fy"]["max"]["value"] == 150.0
        assert point_a["fy"]["max"]["loadcase"] == "Case_Min_Fx"
        assert point_a["fy"]["min"]["value"] == 50.0
        assert point_a["fy"]["min"]["loadcase"] == "Case_Positive_Min"

        # fz: max = 800 (Case_Positive_Min), min = 50 (Case_Max_Fx, positive - should not include)
        assert point_a["fz"]["max"]["value"] == 800.0
        assert point_a["fz"]["max"]["loadcase"] == "Case_Positive_Min"

        # mx: max = 15 (Case_Min_Fx), min = -100 (Case_Positive_Min, negative - should include)
        assert point_a["mx"]["max"]["value"] == 15.0
        assert point_a["mx"]["max"]["loadcase"] == "Case_Min_Fx"
        assert point_a["mx"]["min"]["value"] == -100.0
        assert point_a["mx"]["min"]["loadcase"] == "Case_Positive_Min"

    def test_envelope_with_all_positive_values(self):
        """Test envelope when all values are positive (no negative mins should be included)."""
        positive_loadset = LoadSet(
            name="All Positive LoadSet",
            version=1,
            units=Units(forces="N", moments="Nm"),
            load_cases=[
                LoadCase(
                    name="Case_1",
                    point_loads=[
                        PointLoad(
                            name="Point_A",
                            force_moment=ForceMoment(fx=100.0, fy=200.0, fz=300.0),
                        ),
                    ],
                ),
                LoadCase(
                    name="Case_2",
                    point_loads=[
                        PointLoad(
                            name="Point_A",
                            force_moment=ForceMoment(
                                fx=50.0, fy=400.0, fz=150.0
                            ),  # fy is max
                        ),
                    ],
                ),
                LoadCase(
                    name="Case_3",
                    point_loads=[
                        PointLoad(
                            name="Point_A",
                            force_moment=ForceMoment(
                                fx=150.0, fy=100.0, fz=500.0
                            ),  # fx is max, fz is max
                        ),
                    ],
                ),
            ],
        )

        envelope = positive_loadset.envelope()
        envelope_case_names = {lc.name for lc in envelope.load_cases}

        # Should only include cases with max values, not mins (since all mins are positive)
        # Case_2 has max fy, Case_3 has max fx and fz
        assert "Case_2" in envelope_case_names
        assert "Case_3" in envelope_case_names
        # Case_1 might not be included unless it has some max value

    def test_envelope_with_duplicate_extremes(self):
        """Test envelope when same load case has multiple extremes."""
        duplicate_loadset = LoadSet(
            name="Duplicate Extremes LoadSet",
            version=1,
            units=Units(forces="N", moments="Nm"),
            load_cases=[
                LoadCase(
                    name="Multi_Extreme_Case",  # Has both max fx and max fy
                    point_loads=[
                        PointLoad(
                            name="Point_A",
                            force_moment=ForceMoment(fx=1000.0, fy=2000.0, fz=100.0),
                        ),
                    ],
                ),
                LoadCase(
                    name="Other_Case",
                    point_loads=[
                        PointLoad(
                            name="Point_A",
                            force_moment=ForceMoment(
                                fx=500.0, fy=1000.0, fz=3000.0
                            ),  # max fz
                        ),
                    ],
                ),
            ],
        )

        envelope = duplicate_loadset.envelope()

        # Should have both cases (Multi_Extreme_Case for fx,fy maxes; Other_Case for fz max)
        assert len(envelope.load_cases) == 2
        envelope_case_names = {lc.name for lc in envelope.load_cases}
        assert "Multi_Extreme_Case" in envelope_case_names
        assert "Other_Case" in envelope_case_names

    def test_envelope_with_zero_values(self):
        """Test envelope behavior with zero values."""
        zero_loadset = LoadSet(
            name="Zero Values LoadSet",
            version=1,
            units=Units(forces="N", moments="Nm"),
            load_cases=[
                LoadCase(
                    name="Zero_Case",
                    point_loads=[
                        PointLoad(
                            name="Point_A",
                            force_moment=ForceMoment(fx=0.0, fy=100.0, fz=0.0),
                        ),
                    ],
                ),
                LoadCase(
                    name="Positive_Case",
                    point_loads=[
                        PointLoad(
                            name="Point_A",
                            force_moment=ForceMoment(fx=200.0, fy=50.0, fz=300.0),
                        ),
                    ],
                ),
                LoadCase(
                    name="Negative_Case",
                    point_loads=[
                        PointLoad(
                            name="Point_A",
                            force_moment=ForceMoment(fx=-100.0, fy=75.0, fz=-50.0),
                        ),
                    ],
                ),
            ],
        )

        envelope = zero_loadset.envelope()
        envelope_case_names = {lc.name for lc in envelope.load_cases}

        # Zero_Case has max fy
        assert "Zero_Case" in envelope_case_names
        # Positive_Case has max fx and fz
        assert "Positive_Case" in envelope_case_names
        # Negative_Case has negative mins for fx and fz
        assert "Negative_Case" in envelope_case_names

    def test_envelope_empty_loadset(self):
        """Test envelope with empty LoadSet."""
        empty_loadset = LoadSet(
            name="Empty LoadSet",
            version=1,
            units=Units(forces="N", moments="Nm"),
            load_cases=[],
        )

        with pytest.raises(ValueError, match="Cannot create envelope of empty LoadSet"):
            empty_loadset.envelope()

    def test_envelope_single_load_case(self):
        """Test envelope with single load case."""
        single_loadset = LoadSet(
            name="Single LoadSet",
            version=1,
            units=Units(forces="N", moments="Nm"),
            load_cases=[
                LoadCase(
                    name="Only_Case",
                    point_loads=[
                        PointLoad(
                            name="Point_A",
                            force_moment=ForceMoment(fx=100.0, fy=-50.0, fz=200.0),
                        ),
                    ],
                ),
            ],
        )

        envelope = single_loadset.envelope()

        # Should include the single case (it has all the extremes)
        assert len(envelope.load_cases) == 1
        assert envelope.load_cases[0].name == "Only_Case"

    def test_envelope_preserves_structure(self):
        """Test that envelope preserves the internal structure of load cases."""
        envelope = self.sample_loadset.envelope()

        # Find a specific load case and verify its structure is preserved
        case_max_fx = None
        for lc in envelope.load_cases:
            if lc.name == "Case_Max_Fx":
                case_max_fx = lc
                break

        assert case_max_fx is not None
        assert case_max_fx.description == "Load case with maximum fx"
        assert len(case_max_fx.point_loads) == 2  # Should have both Point_A and Point_B

        # Check Point_A values are preserved
        point_a = None
        for pl in case_max_fx.point_loads:
            if pl.name == "Point_A":
                point_a = pl
                break

        assert point_a is not None
        assert point_a.force_moment.fx == 1000.0
        assert point_a.force_moment.fy == 100.0
        assert point_a.force_moment.fz == 50.0

    def test_envelope_with_multiple_points(self):
        """Test envelope with multiple points having different extremes."""
        multi_point_loadset = LoadSet(
            name="Multi Point LoadSet",
            version=1,
            units=Units(forces="N", moments="Nm"),
            load_cases=[
                LoadCase(
                    name="Case_Point_A_Max",
                    point_loads=[
                        PointLoad(
                            name="Point_A",
                            force_moment=ForceMoment(fx=1000.0),  # max for Point_A
                        ),
                        PointLoad(
                            name="Point_B",
                            force_moment=ForceMoment(fx=200.0),
                        ),
                    ],
                ),
                LoadCase(
                    name="Case_Point_B_Max",
                    point_loads=[
                        PointLoad(
                            name="Point_A",
                            force_moment=ForceMoment(fx=500.0),
                        ),
                        PointLoad(
                            name="Point_B",
                            force_moment=ForceMoment(fx=800.0),  # max for Point_B
                        ),
                    ],
                ),
            ],
        )

        envelope = multi_point_loadset.envelope()
        envelope_case_names = {lc.name for lc in envelope.load_cases}

        # Both cases should be included since each has a max for different points
        assert "Case_Point_A_Max" in envelope_case_names
        assert "Case_Point_B_Max" in envelope_case_names
        assert len(envelope.load_cases) == 2


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
