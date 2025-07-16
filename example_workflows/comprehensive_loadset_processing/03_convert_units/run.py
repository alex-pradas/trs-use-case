#!/usr/bin/env python3
"""
Step 03: convert_units

Convert LoadSet to target units
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
    # Load loadset from ../01_load_primary_loadset/outputs/primary_loadset.json
    with open(Path("../01_load_primary_loadset/outputs/primary_loadset.json"), "r") as f:
        inputs["loadset"] = json.load(f)
    # Load target_units from inputs/target_units.txt
    inputs["target_units"] = Path("inputs/target_units.txt")
    
    return inputs


def validate_inputs(inputs: Dict[str, Any]) -> bool:
    """Validate input data."""
    try:
        # Validate loadset
        if "loadset" not in inputs:
            raise ValueError("loadset not found in inputs")
        # Validate LoadSet structure
        if isinstance(inputs["loadset"], dict):
            if "load_cases" not in inputs["loadset"]:
                raise ValueError("Invalid LoadSet: missing load_cases")
        # Validate target_units
        if "target_units" not in inputs:
            raise ValueError("target_units not found in inputs")
        return True
    except Exception as e:
        logger.error(f"Input validation failed: {e}")
        return False


def save_outputs(outputs: Dict[str, Any]) -> None:
    """Save outputs from this step."""
    # Save converted_loadset to converted_loadset.json
    with open(OUTPUT_DIR / "converted_loadset.json", "w") as f:
        json.dump(outputs["converted_loadset"], f, indent=2)


def main() -> None:
    """Main execution function."""
    logger.info("Starting step 03: convert_units")
    
    try:
        # Load inputs
        inputs = load_inputs()
        logger.info(f"Loaded inputs: {list(inputs.keys())}")
        
        # Validate inputs
        if not validate_inputs(inputs):
            logger.error("Input validation failed")
            sys.exit(1)
        
        # Main processing logic
        # Load LoadSet and target units
        loadset_data = inputs["loadset"]
        
        with open(inputs["target_units"], "r") as f:
            target_units = f.read().strip()
        
        logger.info(f"Converting LoadSet to units: {target_units}")
        
        # Convert LoadSet
        loadset = LoadSet.from_dict(loadset_data)
        converted_loadset = loadset.convert_to(target_units)
        
        logger.info(f"Conversion complete. New units: {converted_loadset.units.forces}, {converted_loadset.units.moments}")
        
        # Prepare outputs
        outputs = {
            "converted_loadset": converted_loadset.to_dict()
        }
        
        logger.info("Unit conversion completed successfully")
        
        # Save outputs
        save_outputs(outputs)
        
        logger.info("Step 03 completed successfully")
        
    except Exception as e:
        logger.error(f"Step 03 failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
