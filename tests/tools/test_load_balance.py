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


class TestGenerateBalancedLoadset:
    """Tests for the main generate_balanced_loadset function."""

    def test_generates_correct_number_of_cases(self):
        """Should generate the requested number of load cases."""
        result = generate_balanced_loadset(
            DEFAULT_INTERFACES,
            num_cases=10,
            seed=42,
        )
        assert len(result["load_cases"]) == 10

    def test_all_cases_are_balanced(self):
        """All generated cases should satisfy equilibrium."""
        load_ranges = {
            "Engine Mount (Port)": {"Fy": (3000, 7000), "Fz": (3000, 7000)},
            "Engine Mount (Starboard)": {"Fy": (3000, 7000), "Fz": (3000, 7000)},
        }

        result = generate_balanced_loadset(
            DEFAULT_INTERFACES,
            load_ranges,
            num_cases=20,
            seed=42,
        )

        for case in result["load_cases"]:
            assert case["verification"]["is_balanced"], f"Case {case['case_id']} is not balanced"
            # Check residuals are near zero
            assert abs(case["verification"]["sum_Fx"]) < 1e-6
            assert abs(case["verification"]["sum_Fy"]) < 1e-6
            assert abs(case["verification"]["sum_Fz"]) < 1e-6
            assert abs(case["verification"]["sum_Mx"]) < 1e-6
            assert abs(case["verification"]["sum_My"]) < 1e-6
            assert abs(case["verification"]["sum_Mz"]) < 1e-6

    def test_constrained_values_within_ranges(self):
        """Constrained values should fall within specified ranges."""
        load_ranges = {
            "Engine Mount (Port)": {"Fy": (3000, 7000), "Fz": (4000, 5000)},
            "Forward Outer Flange": {"My": (500000, 600000)},
        }

        result = generate_balanced_loadset(
            DEFAULT_INTERFACES,
            load_ranges,
            num_cases=50,
            seed=42,
        )

        for case in result["load_cases"]:
            # Check Engine Mount (Port) ranges
            em_port = case["interfaces"]["Engine Mount (Port)"]
            assert 3000 <= em_port["Fy"] <= 7000, f"Fy out of range: {em_port['Fy']}"
            assert 4000 <= em_port["Fz"] <= 5000, f"Fz out of range: {em_port['Fz']}"

            # Check Forward Outer Flange My
            fof = case["interfaces"]["Forward Outer Flange"]
            assert 500000 <= fof["My"] <= 600000, f"My out of range: {fof['My']}"

    def test_seed_reproducibility(self):
        """Same seed should produce identical results."""
        load_ranges = {"Engine Mount (Port)": {"Fy": (1000, 5000)}}

        result1 = generate_balanced_loadset(
            DEFAULT_INTERFACES, load_ranges, num_cases=5, seed=12345
        )
        result2 = generate_balanced_loadset(
            DEFAULT_INTERFACES, load_ranges, num_cases=5, seed=12345
        )

        for c1, c2 in zip(result1["load_cases"], result2["load_cases"]):
            for interface in DEFAULT_INTERFACES:
                for comp in COMPONENTS:
                    assert c1["interfaces"][interface][comp] == c2["interfaces"][interface][comp]

    def test_no_constraints_produces_zero_solution(self):
        """With no constraints, minimum norm solution should be zeros."""
        result = generate_balanced_loadset(
            DEFAULT_INTERFACES,
            load_ranges=None,  # No constraints
            num_cases=1,
        )

        case = result["load_cases"][0]
        for interface in DEFAULT_INTERFACES:
            for comp in COMPONENTS:
                assert case["interfaces"][interface][comp] == 0.0

    def test_metadata_structure(self):
        """Metadata should contain expected fields."""
        load_ranges = {"Engine Mount (Port)": {"Fx": (100, 200)}}

        result = generate_balanced_loadset(
            DEFAULT_INTERFACES,
            load_ranges,
            num_cases=3,
        )

        assert "metadata" in result
        assert result["metadata"]["num_cases"] == 3
        assert "interfaces" in result["metadata"]
        assert "specified_ranges" in result["metadata"]
        assert result["metadata"]["units"]["force"] == "N"
        assert result["metadata"]["units"]["moment"] == "N·mm"

    def test_all_interfaces_in_output(self):
        """All interfaces should appear in each load case output."""
        result = generate_balanced_loadset(
            DEFAULT_INTERFACES,
            num_cases=1,
        )

        case = result["load_cases"][0]
        for interface in DEFAULT_INTERFACES:
            assert interface in case["interfaces"]
            # Check all components present
            for comp in COMPONENTS:
                assert comp in case["interfaces"][interface]


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
        interfaces = {"A": (0, 0, 0), "B": (100, 0, 0)}

        # Constrain Fz at A, solver should find balancing values
        result = generate_balanced_loadset(
            interfaces,
            load_ranges={"A": {"Fz": (1000, 2000)}},
            num_cases=5,
            seed=42,
        )

        for case in result["load_cases"]:
            assert case["verification"]["is_balanced"]
            # Fz at A and B should be opposite (sum to zero)
            fz_a = case["interfaces"]["A"]["Fz"]
            fz_b = case["interfaces"]["B"]["Fz"]
            assert 1000 <= fz_a <= 2000  # Constrained range
            assert abs(fz_a + fz_b) < 1e-6  # Force balance

    def test_colinear_interfaces(self):
        """Interfaces along a line should still produce balanced loads."""
        interfaces = {
            "A": (0, 0, 0),
            "B": (0, 0, 100),
            "C": (0, 0, 200),
        }

        load_ranges = {
            "A": {"Fz": (1000, 2000)},
            "C": {"Fz": (500, 1000)},
        }

        result = generate_balanced_loadset(
            interfaces,
            load_ranges,
            num_cases=10,
            seed=42,
        )

        for case in result["load_cases"]:
            assert case["verification"]["is_balanced"]
