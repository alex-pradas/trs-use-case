#!/usr/bin/env python3
"""
Step 02: load_comparison_loadset

Load the comparison LoadSet from JSON file
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to Python path
PROJECT_ROOT = Path("/Users/alex/repos/trs-use-case")
sys.path.insert(0, str(PROJECT_ROOT))

# Import project modules
from tools.loads import LoadSet

# Define paths
CURRENT_DIR = Path(__file__).parent
INPUT_DIR = CURRENT_DIR / "inputs"
OUTPUT_DIR = CURRENT_DIR / "outputs"
WORKFLOW_DIR = CURRENT_DIR.parent

# Ensure output directory exists
OUTPUT_DIR.mkdir(exist_ok=True)


def load_inputs() -> Dict[str, Any]:
    """Load inputs for this step."""
    inputs = {}
    
    # Load input mappings
    # Load loadset_file from inputs/comparison_loadset.json
    with open(Path("inputs/comparison_loadset.json"), "r") as f:
        inputs["loadset_file"] = json.load(f)
    
    return inputs


def validate_inputs(inputs: Dict[str, Any]) -> bool:
    """Validate input data."""
    try:
        # Validate loadset_file
        if "loadset_file" not in inputs:
            raise ValueError("loadset_file not found in inputs")
        # Validate LoadSet structure
        if isinstance(inputs["loadset_file"], dict):
            if "load_cases" not in inputs["loadset_file"]:
                raise ValueError("Invalid LoadSet: missing load_cases")
        return True
    except Exception as e:
        logger.error(f"Input validation failed: {e}")
        return False


def save_outputs(outputs: Dict[str, Any]) -> None:
    """Save outputs from this step."""
    # Save loadset to comparison_loadset.json
    with open(OUTPUT_DIR / "comparison_loadset.json", "w") as f:
        json.dump(outputs["loadset"], f, indent=2)


def main() -> None:
    """Main execution function."""
    logger.info("Starting step 02: load_comparison_loadset")
    
    try:
        # Load inputs
        inputs = load_inputs()
        logger.info(f"Loaded inputs: {list(inputs.keys())}")
        
        # Validate inputs
        if not validate_inputs(inputs):
            logger.error("Input validation failed")
            sys.exit(1)
        
        # Main processing logic
        # Load comparison LoadSet from JSON file
        loadset_file = inputs["loadset_file"]
        
        logger.info(f"Loading comparison LoadSet from: {loadset_file}")
        loadset = LoadSet.read_json(loadset_file)
        
        logger.info(f"Loaded comparison LoadSet: {loadset.name}")
        logger.info(f"Number of load cases: {len(loadset.load_cases)}")
        logger.info(f"Units: {loadset.units.forces}, {loadset.units.moments}")
        
        # Prepare outputs
        outputs = {
            "loadset": loadset.to_dict()
        }
        
        logger.info("Comparison LoadSet loaded successfully")
        
        # Save outputs
        save_outputs(outputs)
        
        logger.info("Step 02 completed successfully")
        
    except Exception as e:
        logger.error(f"Step 02 failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
