# Balanced Mechanical Loads Generator

Generate multiple balanced load cases for structural interfaces, ensuring static equilibrium (ΣF = 0, ΣM = 0).

## Usage

```python
from tools.load_balance import generate_balanced_loadset, DEFAULT_INTERFACES

# Specify ranges for forces/moments at certain interfaces (in N and N·mm)
load_ranges = {
    "Engine Mount (Port)": {"Fy": (3000.0, 7000.0), "Fz": (3000.0, 7000.0)},
    "Engine Mount (Starboard)": {"Fy": (3000.0, 7000.0), "Fz": (3000.0, 7000.0)},
    "Forward Outer Flange": {"My": (500000.0, 600000.0)},
}

# Generate 50 balanced load cases
loadset = generate_balanced_loadset(
    DEFAULT_INTERFACES,
    load_ranges,
    num_cases=50,
    seed=42,  # Optional: for reproducibility
    name="Engine Mount Balanced Loads",
)

# Returns a LoadSet object - use all LoadSet methods
loadset.to_ansys("output/")  # Export to ANSYS
loadset.get_point_extremes()  # Get extreme values
```

## How It Works

1. **Specify ranges** for forces/moments at specific interfaces
2. **Random sampling** within those ranges for each load case
3. **Minimum-norm solver** calculates remaining values to satisfy equilibrium
4. **Returns LoadSet** object compatible with existing tools

## Default Interfaces

```python
DEFAULT_INTERFACES = {
    "Engine Mount (Port)": (-317.7275, 378.6529, 3984.2688),
    "Engine Mount (Fail Safe)": (0.0, 494.2962, 3984.2688),
    "Engine Mount (Starboard)": (317.7275, 378.6529, 3984.2688),
    "Forward Outer Flange": (0.0, 0.0, 3874.2688),
    "Forward Inner Flange": (-0.0014, 0.0, 3896.0),
    "Aft Outer Flange": (0.0, 0.0, 4153.8389),
    "Aft Inner Flange": (0.0, 0.0, 4152.3335),
}
```

## Iterative Workflow

Run multiple times with additional constraints to raise values at other interfaces:

```python
# First run: constrain engine mounts
loadset1 = generate_balanced_loadset(interfaces, {"Engine Mount (Port)": {"Fz": (5000, 10000)}})

# Second run: also constrain flanges
loadset2 = generate_balanced_loadset(interfaces, {
    "Engine Mount (Port)": {"Fz": (5000, 10000)},
    "Forward Outer Flange": {"My": (100000, 200000)},
})
```

## Units

- Forces: N (Newtons)
- Moments: N·mm (Newton-millimeters)
- Positions: mm (millimeters)
