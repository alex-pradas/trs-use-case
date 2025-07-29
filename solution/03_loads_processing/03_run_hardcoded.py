from pathlib import Path


import sys
sys.path.insert(0, '/Users/alex/repos/trs-use-case')

from tools.loads import LoadSet

# inputs
new_loads_path = Path("/Users/alex/repos/trs-use-case/solution/loads/03_01_new_loads.json")
output_path = Path("/Users/alex/repos/trs-use-case/solution/03_loads_processing") / "output"
delete_output = True

# Read the LoadSet from a JSON file
new_loadset: LoadSet = LoadSet.read_json(new_loads_path)

# Check if conversion to N and Nm is needed
if new_loadset.units != "N":
    new_loadset = new_loadset.convert_to("N")

# Check for ultimate loads
if new_loadset.loads_type != "ultimate":
    new_loadset = new_loadset.factor(1.5)

# Envelope Loads
enveloped_loadset = new_loadset.envelope()

# Convert to ANSYS format
enveloped_loadset.to_ansys(output_path, name_stem="ultimate")

# Analysis done, now comes the sanity check


# Count files exported
exported_files = len(list(output_path.glob("*.inp")))
print(f"Exported {exported_files} ANSYS files to {output_path}")
assert exported_files == 9

# Get the values
results = enveloped_loadset.get_point_extremes()
print("Extreme values in the LoadSet:")
from pprint import pprint
pprint(results)


# Check values for specific points
assert results["Point A"]["fx"]["max"]["loadcase"] == "landing_011"
assert results["Point A"]["fx"]["max"]["value"] - 1.4958699 < 0.0001

assert results["Point A"]["my"]["min"]["loadcase"] == "cruise2_098"
assert results["Point A"]["my"]["min"]["value"] - 0.213177015 < 0.0001

assert results["Point B"]["fy"]["max"]["loadcase"] == "landing_012"
assert results["Point B"]["fy"]["max"]["value"] - 1.462682895 < 0.0001

if delete_output:
    # Clean up output directory
    for file in output_path.glob("*.inp"):
        file.unlink()
    print(f"Deleted all files in {output_path}")