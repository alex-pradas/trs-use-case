"""
Tests for LoadSet envelope functionality.

This module tests the envelope method that downselects load cases based on extreme values.
"""

import pytest
from tools.loads import LoadSet, Units, LoadCase, PointLoad, ForceMoment


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
                                fy=50.0,   # MIN for Point_A fy (positive, should not be included)
                                fz=800.0,  # MAX for Point_A fz
                                mx=-100.0, # MIN for Point_A mx (negative, should be included)
                                my=10.0,   # MIN for Point_A my (positive, should not be included)
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
                                mx=12.0,   # Between min and max (not 50.0 which would be max)
                                my=15.0,   # Between min and max
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
                            force_moment=ForceMoment(fx=50.0, fy=400.0, fz=150.0),  # fy is max
                        ),
                    ],
                ),
                LoadCase(
                    name="Case_3",
                    point_loads=[
                        PointLoad(
                            name="Point_A",
                            force_moment=ForceMoment(fx=150.0, fy=100.0, fz=500.0),  # fx is max, fz is max
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
                            force_moment=ForceMoment(fx=500.0, fy=1000.0, fz=3000.0),  # max fz
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