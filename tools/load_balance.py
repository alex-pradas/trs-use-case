"""
Balanced Mechanical Loads Generator

Generates multiple load cases with user-specified ranges at certain interfaces,
ensuring static equilibrium (ΣF = 0, ΣM = 0) for each case.

Unspecified loads are solved using minimum-norm optimization.
"""

import numpy as np
from numpy.typing import NDArray

try:
    from tools.loads import LoadSet, LoadCase, PointLoad, ForceMoment, Units
except ModuleNotFoundError:
    from loads import LoadSet, LoadCase, PointLoad, ForceMoment, Units


# Component ordering for consistent indexing
COMPONENTS = ["Fx", "Fy", "Fz", "Mx", "My", "Mz"]


def generate_balanced_loadset(
    interfaces: dict[str, tuple[float, float, float]],
    load_ranges: dict[str, dict[str, tuple[float, float]]] | None = None,
    num_cases: int = 50,
    seed: int | None = None,
    name: str | None = None,
    description: str | None = None,
) -> LoadSet:
    """
    Generate multiple balanced load cases with specified ranges.

    Args:
        interfaces: Dict mapping interface name to (x, y, z) position in mm
        load_ranges: Dict mapping interface name to component ranges.
                     Example: {"Engine Mount": {"Fy": (3000, 7000), "Fz": (3000, 7000)}}
                     Values in N for forces, N·mm for moments.
        num_cases: Number of load cases to generate
        seed: Random seed for reproducibility
        name: Optional name for the LoadSet
        description: Optional description for the LoadSet

    Returns:
        LoadSet with generated balanced load cases
    """
    if seed is not None:
        np.random.seed(seed)

    load_ranges = load_ranges or {}

    # Build interface list with consistent ordering
    interface_names = list(interfaces.keys())
    n_interfaces = len(interface_names)

    # Build equilibrium matrix (6 equations x 6N unknowns)
    A = _build_equilibrium_matrix(interfaces, interface_names)

    # Identify which variables are constrained (have ranges) vs free
    _, constrained_indices, free_indices = _identify_constrained_variables(
        interface_names, load_ranges
    )

    load_cases: list[LoadCase] = []

    for case_idx in range(num_cases):
        # Sample constrained variables from their ranges
        sampled_values = _sample_constrained_values(
            interface_names, load_ranges, constrained_indices
        )

        # Solve for free variables using minimum-norm solution
        all_values = _solve_for_balance(
            A, sampled_values, constrained_indices, free_indices, n_interfaces
        )

        # Build LoadCase
        load_case = _build_load_case(case_idx + 1, interface_names, all_values)
        load_cases.append(load_case)

    return LoadSet(
        name=name or "Balanced LoadSet",
        description=description or f"Generated {num_cases} balanced load cases",
        version=1,
        units=Units(forces="N", moments="Nm"),
        load_cases=load_cases,
    )


def _build_equilibrium_matrix(
    interfaces: dict[str, tuple[float, float, float]],
    interface_names: list[str],
) -> NDArray[np.float64]:
    """
    Build the 6x6N equilibrium constraint matrix.

    For each interface i at position (x_i, y_i, z_i):
    - Columns 6*i to 6*i+5 correspond to [Fx, Fy, Fz, Mx, My, Mz]

    Rows represent:
    - Row 0: ΣFx = 0
    - Row 1: ΣFy = 0
    - Row 2: ΣFz = 0
    - Row 3: ΣMx = Σ(Mx + y*Fz - z*Fy) = 0
    - Row 4: ΣMy = Σ(My + z*Fx - x*Fz) = 0
    - Row 5: ΣMz = Σ(Mz + x*Fy - y*Fx) = 0
    """
    n = len(interface_names)
    A = np.zeros((6, 6 * n))

    for i, name in enumerate(interface_names):
        x, y, z = interfaces[name]
        col_base = 6 * i

        # Force balance equations (rows 0-2)
        A[0, col_base + 0] = 1  # Fx contributes to ΣFx
        A[1, col_base + 1] = 1  # Fy contributes to ΣFy
        A[2, col_base + 2] = 1  # Fz contributes to ΣFz

        # Moment balance equations (rows 3-5)
        # ΣMx = Σ(Mx + y*Fz - z*Fy) = 0
        A[3, col_base + 1] = -z  # -z*Fy
        A[3, col_base + 2] = y   # +y*Fz
        A[3, col_base + 3] = 1   # +Mx

        # ΣMy = Σ(My + z*Fx - x*Fz) = 0
        A[4, col_base + 0] = z   # +z*Fx
        A[4, col_base + 2] = -x  # -x*Fz
        A[4, col_base + 4] = 1   # +My

        # ΣMz = Σ(Mz + x*Fy - y*Fx) = 0
        A[5, col_base + 0] = -y  # -y*Fx
        A[5, col_base + 1] = x   # +x*Fy
        A[5, col_base + 5] = 1   # +Mz

    return A


def _identify_constrained_variables(
    interface_names: list[str],
    load_ranges: dict[str, dict[str, tuple[float, float]]],
) -> tuple[NDArray[np.bool_], list[int], list[int]]:
    """
    Identify which variables are constrained (have specified ranges).

    Returns:
        constrained_mask: Boolean array of length 6N
        constrained_indices: List of constrained variable indices
        free_indices: List of free variable indices
    """
    n = len(interface_names)
    constrained_mask = np.zeros(6 * n, dtype=bool)

    for i, name in enumerate(interface_names):
        if name in load_ranges:
            for j, comp in enumerate(COMPONENTS):
                if comp in load_ranges[name]:
                    constrained_mask[6 * i + j] = True

    constrained_indices = list(np.where(constrained_mask)[0])
    free_indices = list(np.where(~constrained_mask)[0])

    return constrained_mask, constrained_indices, free_indices


def _sample_constrained_values(
    interface_names: list[str],
    load_ranges: dict[str, dict[str, tuple[float, float]]],
    constrained_indices: list[int],
) -> NDArray[np.float64]:
    """
    Sample random values for constrained variables within their ranges.

    Returns:
        Array of sampled values for constrained variables only
    """
    sampled = np.zeros(len(constrained_indices))

    for idx, global_idx in enumerate(constrained_indices):
        interface_idx = global_idx // 6
        comp_idx = global_idx % 6

        name = interface_names[interface_idx]
        comp = COMPONENTS[comp_idx]

        min_val, max_val = load_ranges[name][comp]
        sampled[idx] = np.random.uniform(min_val, max_val)

    return sampled


def _solve_for_balance(
    A: NDArray[np.float64],
    constrained_values: NDArray[np.float64],
    constrained_indices: list[int],
    free_indices: list[int],
    n_interfaces: int,
) -> NDArray[np.float64]:
    """
    Solve for free variables using minimum-norm solution.

    Given: A @ x = 0, with some x values fixed
    Solve: A_free @ x_free = -A_constrained @ x_constrained
    Using minimum-norm (least squares) solution.
    """
    n_vars = 6 * n_interfaces

    # If no constrained values, solve A @ x = 0 for minimum norm x
    if len(constrained_indices) == 0:
        # All zeros is a valid solution for A @ x = 0
        return np.zeros(n_vars)

    # If no free variables, just check if constraints satisfy equilibrium
    if len(free_indices) == 0:
        result = np.zeros(n_vars)
        for idx, global_idx in enumerate(constrained_indices):
            result[global_idx] = constrained_values[idx]
        return result

    # Partition matrix
    A_constrained = A[:, constrained_indices]
    A_free = A[:, free_indices]

    # RHS: -A_constrained @ x_constrained
    b = -A_constrained @ constrained_values

    # Solve using least squares (minimum norm for underdetermined systems)
    free_values, residuals, rank, s = np.linalg.lstsq(A_free, b, rcond=None)

    # Reconstruct full solution vector
    result = np.zeros(n_vars)
    for idx, global_idx in enumerate(constrained_indices):
        result[global_idx] = constrained_values[idx]
    for idx, global_idx in enumerate(free_indices):
        result[global_idx] = free_values[idx]

    return result


def _build_load_case(
    case_id: int,
    interface_names: list[str],
    all_values: NDArray[np.float64],
) -> LoadCase:
    """Build a LoadCase from the solved values."""
    point_loads: list[PointLoad] = []

    for i, name in enumerate(interface_names):
        col_base = 6 * i
        force_moment = ForceMoment(
            fx=float(all_values[col_base + 0]),
            fy=float(all_values[col_base + 1]),
            fz=float(all_values[col_base + 2]),
            mx=float(all_values[col_base + 3]),
            my=float(all_values[col_base + 4]),
            mz=float(all_values[col_base + 5]),
        )
        point_loads.append(PointLoad(name=name, force_moment=force_moment))

    return LoadCase(
        name=f"Case_{case_id:03d}",
        description=f"Balanced load case {case_id}",
        point_loads=point_loads,
    )


def _verify_equilibrium(
    A: NDArray[np.float64],
    all_values: NDArray[np.float64],
    tolerance: float = 1e-6,
) -> dict:
    """
    Verify that equilibrium is satisfied.

    Returns dict with sum values and a boolean indicating if balanced.
    """
    residual = A @ all_values

    return {
        "sum_Fx": float(residual[0]),
        "sum_Fy": float(residual[1]),
        "sum_Fz": float(residual[2]),
        "sum_Mx": float(residual[3]),
        "sum_My": float(residual[4]),
        "sum_Mz": float(residual[5]),
        "is_balanced": bool(np.allclose(residual, 0, atol=tolerance)),
    }


# Default interfaces from the specification
DEFAULT_INTERFACES = {
    "Engine Mount (Port)": (-317.7275, 378.6529, 3984.2688),
    "Engine Mount (Fail Safe)": (0.0, 494.2962, 3984.2688),
    "Engine Mount (Starboard)": (317.7275, 378.6529, 3984.2688),
    "Forward Outer Flange": (0.0, 0.0, 3874.2688),
    "Forward Inner Flange": (-0.0014, 0.0, 3896.0),
    "Aft Outer Flange": (0.0, 0.0, 4153.8389),
    "Aft Inner Flange": (0.0, 0.0, 4152.3335),
}


if __name__ == "__main__":
    # Example usage
    load_ranges = {
        "Engine Mount (Port)": {"Fy": (3000.0, 7000.0), "Fz": (3000.0, 7000.0)},
        "Engine Mount (Starboard)": {"Fy": (3000.0, 7000.0), "Fz": (3000.0, 7000.0)},
        "Forward Outer Flange": {"My": (500000.0, 600000.0)},
    }

    loadset = generate_balanced_loadset(
        DEFAULT_INTERFACES,
        load_ranges,
        num_cases=5,
        seed=42,
        name="Engine Mount Balanced Loads",
    )

    print(f"Generated LoadSet: {loadset.name}")
    print(f"Number of load cases: {len(loadset.load_cases)}")
    print(f"Units: {loadset.units.forces} / {loadset.units.moments}")

    for load_case in loadset.load_cases:
        print(f"\n{load_case.name}:")
        for point_load in load_case.point_loads:
            fm = point_load.force_moment
            print(f"  {point_load.name}: Fy={fm.fy:.1f} N, Fz={fm.fz:.1f} N")
