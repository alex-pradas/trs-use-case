"""Tests for the load_balance module."""

import numpy as np
import pytest
from tools.load_balance import (
    generate_balanced_loadset,
    _build_equilibrium_matrix,
    _verify_equilibrium,
    DEFAULT_INTERFACES,
    COMPONENTS,
)
from tools.loads import LoadSet


class TestGenerateBalancedLoadset:
    """Tests for the main generate_balanced_loadset function."""

    def test_returns_loadset(self):
        """Should return a LoadSet object."""
        result = generate_balanced_loadset(
            DEFAULT_INTERFACES,
            num_cases=5,
            seed=42,
        )
        assert isinstance(result, LoadSet)

    def test_generates_correct_number_of_cases(self):
        """Should generate the requested number of load cases."""
        result = generate_balanced_loadset(
            DEFAULT_INTERFACES,
            num_cases=10,
            seed=42,
        )
        assert len(result.load_cases) == 10

    def test_all_cases_are_balanced(self):
        """All generated cases should satisfy equilibrium."""
        load_ranges = {
            "Engine Mount (Port)": {"Fy": (3000.0, 7000.0), "Fz": (3000.0, 7000.0)},
            "Engine Mount (Starboard)": {"Fy": (3000.0, 7000.0), "Fz": (3000.0, 7000.0)},
        }

        result = generate_balanced_loadset(
            DEFAULT_INTERFACES,
            load_ranges,
            num_cases=20,
            seed=42,
        )

        # Build equilibrium matrix to verify balance
        interface_names = list(DEFAULT_INTERFACES.keys())
        A = _build_equilibrium_matrix(DEFAULT_INTERFACES, interface_names)

        for load_case in result.load_cases:
            # Extract values in order
            values = []
            for name in interface_names:
                point_load = next(p for p in load_case.point_loads if p.name == name)
                fm = point_load.force_moment
                values.extend([fm.fx, fm.fy, fm.fz, fm.mx, fm.my, fm.mz])

            verification = _verify_equilibrium(A, np.array(values))
            assert verification["is_balanced"], f"{load_case.name} is not balanced"

    def test_constrained_values_within_ranges(self):
        """Constrained values should fall within specified ranges."""
        load_ranges = {
            "Engine Mount (Port)": {"Fy": (3000.0, 7000.0), "Fz": (4000.0, 5000.0)},
            "Forward Outer Flange": {"My": (500000.0, 600000.0)},
        }

        result = generate_balanced_loadset(
            DEFAULT_INTERFACES,
            load_ranges,
            num_cases=50,
            seed=42,
        )

        for load_case in result.load_cases:
            # Check Engine Mount (Port) ranges
            em_port = next(p for p in load_case.point_loads if p.name == "Engine Mount (Port)")
            assert 3000 <= em_port.force_moment.fy <= 7000, f"Fy out of range: {em_port.force_moment.fy}"
            assert 4000 <= em_port.force_moment.fz <= 5000, f"Fz out of range: {em_port.force_moment.fz}"

            # Check Forward Outer Flange My
            fof = next(p for p in load_case.point_loads if p.name == "Forward Outer Flange")
            assert 500000 <= fof.force_moment.my <= 600000, f"My out of range: {fof.force_moment.my}"

    def test_seed_reproducibility(self):
        """Same seed should produce identical results."""
        load_ranges = {"Engine Mount (Port)": {"Fy": (1000.0, 5000.0)}}

        result1 = generate_balanced_loadset(
            DEFAULT_INTERFACES, load_ranges, num_cases=5, seed=12345
        )
        result2 = generate_balanced_loadset(
            DEFAULT_INTERFACES, load_ranges, num_cases=5, seed=12345
        )

        for lc1, lc2 in zip(result1.load_cases, result2.load_cases):
            for p1, p2 in zip(lc1.point_loads, lc2.point_loads):
                assert p1.force_moment.fx == p2.force_moment.fx
                assert p1.force_moment.fy == p2.force_moment.fy
                assert p1.force_moment.fz == p2.force_moment.fz
                assert p1.force_moment.mx == p2.force_moment.mx
                assert p1.force_moment.my == p2.force_moment.my
                assert p1.force_moment.mz == p2.force_moment.mz

    def test_no_constraints_produces_zero_solution(self):
        """With no constraints, minimum norm solution should be zeros."""
        result = generate_balanced_loadset(
            DEFAULT_INTERFACES,
            load_ranges=None,  # No constraints
            num_cases=1,
        )

        load_case = result.load_cases[0]
        for point_load in load_case.point_loads:
            fm = point_load.force_moment
            assert fm.fx == 0.0
            assert fm.fy == 0.0
            assert fm.fz == 0.0
            assert fm.mx == 0.0
            assert fm.my == 0.0
            assert fm.mz == 0.0

    def test_loadset_structure(self):
        """LoadSet should have expected structure."""
        load_ranges = {"Engine Mount (Port)": {"Fx": (100.0, 200.0)}}

        result = generate_balanced_loadset(
            DEFAULT_INTERFACES,
            load_ranges,
            num_cases=3,
            name="Test LoadSet",
        )

        assert result.name == "Test LoadSet"
        assert len(result.load_cases) == 3
        assert result.units.forces == "N"
        assert result.units.moments == "Nm"

    def test_all_interfaces_in_output(self):
        """All interfaces should appear in each load case output."""
        result = generate_balanced_loadset(
            DEFAULT_INTERFACES,
            num_cases=1,
        )

        load_case = result.load_cases[0]
        point_names = {p.name for p in load_case.point_loads}
        for interface in DEFAULT_INTERFACES:
            assert interface in point_names


class TestEquilibriumMatrix:
    """Tests for equilibrium matrix construction."""

    def test_matrix_shape(self):
        """Matrix should be 6 x 6N."""
        interfaces = {
            "A": (0, 0, 0),
            "B": (1, 0, 0),
            "C": (0, 1, 0),
        }
        A = _build_equilibrium_matrix(interfaces, list(interfaces.keys()))
        assert A.shape == (6, 18)  # 6 equations, 6*3 unknowns

    def test_force_balance_rows(self):
        """First three rows should sum force components."""
        interfaces = {"A": (1, 2, 3), "B": (4, 5, 6)}
        A = _build_equilibrium_matrix(interfaces, list(interfaces.keys()))

        # Row 0: ΣFx - should have 1s in Fx columns (0 and 6)
        assert A[0, 0] == 1  # Fx of A
        assert A[0, 6] == 1  # Fx of B
        # All other Fx-row entries should be 0
        assert A[0, 1] == 0  # Fy of A

        # Row 1: ΣFy
        assert A[1, 1] == 1  # Fy of A
        assert A[1, 7] == 1  # Fy of B

        # Row 2: ΣFz
        assert A[2, 2] == 1  # Fz of A
        assert A[2, 8] == 1  # Fz of B


class TestVerifyEquilibrium:
    """Tests for equilibrium verification."""

    def test_balanced_system_passes(self):
        """A balanced system should pass verification."""
        # Simple case: two interfaces with equal and opposite forces
        interfaces = {"A": (0, 0, 0), "B": (1, 0, 0)}
        A = _build_equilibrium_matrix(interfaces, list(interfaces.keys()))

        # F_A = (100, 0, 0, 0, 0, 0), F_B = (-100, 0, 0, 0, 0, 0)
        values = np.array([100, 0, 0, 0, 0, 0, -100, 0, 0, 0, 0, 0])

        verification = _verify_equilibrium(A, values)
        assert verification["is_balanced"]

    def test_unbalanced_system_fails(self):
        """An unbalanced system should fail verification."""
        interfaces = {"A": (0, 0, 0), "B": (1, 0, 0)}
        A = _build_equilibrium_matrix(interfaces, list(interfaces.keys()))

        # Unbalanced: both have positive Fx
        values = np.array([100, 0, 0, 0, 0, 0, 100, 0, 0, 0, 0, 0])

        verification = _verify_equilibrium(A, values)
        assert not verification["is_balanced"]
        assert verification["sum_Fx"] == 200


class TestCustomInterfaces:
    """Tests with custom interface configurations."""

    def test_two_interfaces_opposite_forces(self):
        """Two interfaces should balance with opposite forces."""
        interfaces = {"A": (0.0, 0.0, 0.0), "B": (100.0, 0.0, 0.0)}

        # Constrain Fz at A, solver should find balancing values
        result = generate_balanced_loadset(
            interfaces,
            load_ranges={"A": {"Fz": (1000.0, 2000.0)}},
            num_cases=5,
            seed=42,
        )

        interface_names = list(interfaces.keys())
        A_matrix = _build_equilibrium_matrix(interfaces, interface_names)

        for load_case in result.load_cases:
            # Extract values in order
            values = []
            for name in interface_names:
                point_load = next(p for p in load_case.point_loads if p.name == name)
                fm = point_load.force_moment
                values.extend([fm.fx, fm.fy, fm.fz, fm.mx, fm.my, fm.mz])

            verification = _verify_equilibrium(A_matrix, np.array(values))
            assert verification["is_balanced"]

            # Fz at A and B should be opposite (sum to zero)
            pt_a = next(p for p in load_case.point_loads if p.name == "A")
            pt_b = next(p for p in load_case.point_loads if p.name == "B")
            assert 1000 <= pt_a.force_moment.fz <= 2000  # Constrained range
            assert abs(pt_a.force_moment.fz + pt_b.force_moment.fz) < 1e-6  # Force balance

    def test_colinear_interfaces(self):
        """Interfaces along a line should still produce balanced loads."""
        interfaces = {
            "A": (0.0, 0.0, 0.0),
            "B": (0.0, 0.0, 100.0),
            "C": (0.0, 0.0, 200.0),
        }

        load_ranges = {
            "A": {"Fz": (1000.0, 2000.0)},
            "C": {"Fz": (500.0, 1000.0)},
        }

        result = generate_balanced_loadset(
            interfaces,
            load_ranges,
            num_cases=10,
            seed=42,
        )

        interface_names = list(interfaces.keys())
        A_matrix = _build_equilibrium_matrix(interfaces, interface_names)

        for load_case in result.load_cases:
            values = []
            for name in interface_names:
                point_load = next(p for p in load_case.point_loads if p.name == name)
                fm = point_load.force_moment
                values.extend([fm.fx, fm.fy, fm.fz, fm.mx, fm.my, fm.mz])

            verification = _verify_equilibrium(A_matrix, np.array(values))
            assert verification["is_balanced"]
