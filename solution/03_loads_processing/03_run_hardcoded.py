from pathlib import Path


import sys

# Add the repository root to the Python path dynamically
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))

from tools.loads import LoadSet

# inputs
new_loads_path = Path("/Users/alex/repos/trs-use-case/solution/loads/03_01_new_loads.json")
old_loads_path = None # Path("/Users/alex/repos/trs-use-case/solution/loads/03_01_old_loads.json")
output_path = Path("/Users/alex/repos/trs-use-case/solution/03_loads_processing") / "output"

delete_output = True

def process_loads(new_loads_path, output_path, old_loads_path=None):
    """
    Process loads from JSON files, perform enveloping, and export to ANSYS format.
    
    Args:
        new_loads_path: Path to new loads JSON file
        output_path: Output directory for ANSYS files
        old_loads_path: Optional path to old loads JSON file for comparison
    
    Returns:
        dict: Extreme values results from enveloped loadset
    """
    # Read the LoadSet from a JSON file
    new_loadset: LoadSet = LoadSet.read_json(new_loads_path)

    # compare to old_loadset if provided
    if old_loads_path:
        old_loadset = LoadSet.read_json(old_loads_path)
        comparison = new_loadset.compare_to(old_loadset)
        comparison.export_comparison_report(output_path)

    # Check if conversion to N and Nm is needed
    if new_loadset.units != "N":
        new_loadset = new_loadset.convert_to("N")

    # Check for ultimate loads
    if new_loadset.loads_type != "ultimate":
        new_loadset = new_loadset.factor(1.5)

    # Envelope Loads
    enveloped_loadset = new_loadset.envelope()

    # Convert to ANSYS format
    enveloped_loadset.to_ansys(output_path)

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
    
    return results

def validation_Activity_03A(results):
    """
    Validate the extreme values results from Activity 03A.
    
    Args:
        results: Dictionary containing extreme values from enveloped loadset
        
    Raises:
        AssertionError: If validation fails
    """
    tolerance = 1e-6
    
    # Point A fx max validation
    assert results["Point A"]["fx"]["max"]["loadcase"] == "landing_011", \
        f"Expected Point A fx max from landing_011, got {results['Point A']['fx']['max']['loadcase']}"
    assert abs(results["Point A"]["fx"]["max"]["value"] - 1.4958699) < tolerance, \
        f"Point A fx max value mismatch: expected 1.4958699, got {results['Point A']['fx']['max']['value']}"
    
    # Point A my min validation
    assert results["Point A"]["my"]["min"]["loadcase"] == "cruise2_098", \
        f"Expected Point A my min from cruise2_098, got {results['Point A']['my']['min']['loadcase']}"
    assert abs(results["Point A"]["my"]["min"]["value"] - 0.213177015) < tolerance, \
        f"Point A my min value mismatch: expected 0.213177015, got {results['Point A']['my']['min']['value']}"
    
    # Point B fy max validation
    assert results["Point B"]["fy"]["max"]["loadcase"] == "landing_012", \
        f"Expected Point B fy max from landing_012, got {results['Point B']['fy']['max']['loadcase']}"
    assert abs(results["Point B"]["fy"]["max"]["value"] - 1.462682895) < tolerance, \
        f"Point B fy max value mismatch: expected 1.462682895, got {results['Point B']['fy']['max']['value']}"
    
    print("✅ All Activity 03A validations passed!")


def main():
    """
    Main function to execute the load processing workflow.
    """
    # Call the function with correct argument order
    results = process_loads(new_loads_path, output_path, old_loads_path)
    
    # Validate results
    validation_Activity_03A(results)
    
    # Clean up output directory if requested
    if delete_output:
        for file in output_path.glob("*.inp"):
            file.unlink()
        print(f"Deleted all files in {output_path}")


if __name__ == "__main__":
    main()