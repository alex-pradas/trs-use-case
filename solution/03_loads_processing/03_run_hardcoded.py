from pathlib import Path


import sys
sys.path.insert(0, '/Users/alex/repos/trs-use-case')

from tools.loads import LoadSet


# Read the LoadSet from a JSON file
new_loadset = LoadSet.from_json("/Users/alex/repos/trs-use-case/solution/loads/03_01_new_loads.json")

# Check if conversion to N and Nm is needed
if new_loadset.units != "N":
    new_loadset = new_loadset.convert_units("N")


# Since no load type is proviced, we assume they are limit loads and multily them by 1.5 to get ultimate loads.
ultimate = new_loadset.multiply_by_factor(1.5)


