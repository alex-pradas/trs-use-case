"""
Tests for enhanced LoadSet functionality.

This module tests the load-transform-export functionality of the LoadSet class.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path


from tools.loads import LoadSet, Units, LoadCase, PointLoad, ForceMoment


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


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
