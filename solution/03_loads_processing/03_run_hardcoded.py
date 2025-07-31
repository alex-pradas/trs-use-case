from pathlib import Path


import sys

# Add the repository root to the Python path dynamically
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))

from tools.loads import LoadSet  # noqa: E402

# Global settings
delete_output = True

# Activity configurations
ACTIVITIES = {
    "03A": {
        "input_file": "use_case_definition/data/loads/03_A_new_loads.json",
        "old_loads_file": None,  # Path to old loads if needed for comparison
        "expected_values": {
            "Point A": {
                "fx": {"max": {"loadcase": "landing_011", "value": 1.4958699}},
                "my": {"min": {"loadcase": "cruise2_098", "value": 0.213177015}},
            },
            "Point B": {
                "fy": {"max": {"loadcase": "landing_012", "value": 1.462682895}}
            },
        },
    },
    "03B": {
        "input_file": "use_case_definition/data/loads/03_B_new_loads.json",
        "old_loads_file": None,  # Path to old loads if needed for comparison
        "expected_values": {
            "Point A": {
                "fx": {"max": {"loadcase": "landing_011", "value": 6.6539613983178}},
                "my": {"min": {"loadcase": "cruise2_098", "value": 0.28902923412327}},
            },
            "Point B": {
                "fy": {"max": {"loadcase": "landing_012", "value": 6.506338232562691}}
            },
        },
    },
}


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
    inp_files = list(output_path.glob("*.inp"))
    exported_files = len(inp_files)
    ### print the first 5 files
    print(f"Ansys Files exported ({exported_files}) to {output_path}:")
    for file in inp_files[:5]:
        print(f" - {file.name}")
    if exported_files > 5:
        print(f" - ... and {exported_files - 5} more")
    # Get the values
    results = enveloped_loadset.get_point_extremes()
    print("\nExtreme values in the LoadSet:")
    from pprint import pprint

    pprint(results)

    return results


def validate_activity(activity_name, results):
    """
    Validate the extreme values results for any activity.

    Args:
        activity_name: Name of the activity (e.g., "03A", "03B")
        results: Dictionary containing extreme values from enveloped loadset

    Raises:
        AssertionError: If validation fails
        KeyError: If activity_name is not found in ACTIVITIES
    """
    if activity_name not in ACTIVITIES:
        raise KeyError(
            f"Activity '{activity_name}' not found in ACTIVITIES configuration"
        )

    expected_values = ACTIVITIES[activity_name]["expected_values"]
    tolerance = 1e-6

    # Validate each expected value
    for point_name, point_data in expected_values.items():
        for component, component_data in point_data.items():
            for extremes_type, expected in component_data.items():
                # Get actual values
                actual = results[point_name][component][extremes_type]

                # Validate loadcase
                assert actual["loadcase"] == expected["loadcase"], (
                    f"Activity {activity_name}: Expected {point_name} {component} {extremes_type} from {expected['loadcase']}, got {actual['loadcase']}"
                )

                # Validate value with tolerance
                assert abs(actual["value"] - expected["value"]) < tolerance, (
                    f"Activity {activity_name}: {point_name} {component} {extremes_type} value mismatch: expected {expected['value']}, got {actual['value']}"
                )

    print(f"✅ All Activity {activity_name} validations passed!")


def main(activity="03A"):
    """
    Main function to execute the load processing workflow.

    Args:
        activity: Activity name (e.g., "03A", "03B")
    """
    if activity not in ACTIVITIES:
        raise KeyError(f"Activity '{activity}' not found in ACTIVITIES configuration")

    # Get configuration for the specified activity
    config = ACTIVITIES[activity]

    # Set up paths
    new_loads_path = repo_root / config["input_file"]
    old_loads_path = (
        repo_root / config["old_loads_file"] if config["old_loads_file"] else None
    )
    output_path = repo_root / f"solution/03_loads_processing/outputs/{activity}"

    print(f"\n ==== 🚀 Running Activity {activity} ====\n ")
    print(f" * Input file: {config['input_file']}")
    print(f" * Output folder: outputs/{activity}/\n")

    # Call the function with correct argument order
    results = process_loads(new_loads_path, output_path, old_loads_path)

    # Validate results using the generic validation function
    validate_activity(activity, results)

    # Clean up output directory if requested
    if delete_output:
        for file in output_path.glob("*.inp"):
            file.unlink()
        print(f"Deleted all files in {output_path}")


if __name__ == "__main__":
    # Default to Activity 03A for backward compatibility
    # You can also run: python script.py and modify this line for different activities
    activity_to_run = "03A"  # Change to "03B" to run Activity 03B
    main(activity_to_run)
