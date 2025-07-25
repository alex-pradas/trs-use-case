import sys
from pathlib import Path

# Add tools directory to path for LoadSet imports
tools_dir = Path(r"/Users/alex/repos/trs-use-case/tools")
sys.path.insert(0, str(tools_dir))

try:
    from loads import LoadSet, LoadCase, PointLoad, ForceMoment, ForceUnit  # noqa: E402
    import numpy as np  # noqa: E402
    import matplotlib  # noqa: E402

    matplotlib.use("Agg")  # Non-interactive backend
    import matplotlib.pyplot as plt  # noqa: E402
except ImportError as e:
    print(f"Import error: {e}")
    # Continue anyway


import json  # noqa: E402

# Create list of numbers from 1 to 5
numbers = list(range(1, 6))

# Calculate sum
total = sum(numbers)

# Create result dictionary
result = {"numbers": numbers, "sum": total}

# Save to JSON file
with open("simple_math.json", "w") as f:
    json.dump(result, f, indent=4)

# Print summary
print(f"Numbers: {numbers}")
print(f"Sum: {total}")
print("Results have been saved to 'simple_math.json'")
