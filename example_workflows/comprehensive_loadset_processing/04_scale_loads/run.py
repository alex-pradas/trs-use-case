#!/usr/bin/env python3
"""
Step 04: scale_loads

Apply scaling factor to all loads
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
    # Load loadset from ../03_convert_units/outputs/converted_loadset.json
    with open(Path("../03_convert_units/outputs/converted_loadset.json"), "r") as f:
        inputs["loadset"] = json.load(f)
    # Load scale_factor from inputs/scale_factor.txt
    inputs["scale_factor"] = Path("inputs/scale_factor.txt")
    
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
        # Validate scale_factor
        if "scale_factor" not in inputs:
            raise ValueError("scale_factor not found in inputs")
        return True
    except Exception as e:
        logger.error(f"Input validation failed: {e}")
        return False


def save_outputs(outputs: Dict[str, Any]) -> None:
    """Save outputs from this step."""
    # Save scaled_loadset to scaled_loadset.json
    with open(OUTPUT_DIR / "scaled_loadset.json", "w") as f:
        json.dump(outputs["scaled_loadset"], f, indent=2)


def main() -> None:
    """Main execution function."""
    logger.info("Starting step 04: scale_loads")
    
    try:
        # Load inputs
        inputs = load_inputs()
        logger.info(f"Loaded inputs: {list(inputs.keys())}")
        
        # Validate inputs
        if not validate_inputs(inputs):
            logger.error("Input validation failed")
            sys.exit(1)
        
        # Main processing logic
        # Load LoadSet and scale factor
        loadset_data = inputs["loadset"]
        
        with open(inputs["scale_factor"], "r") as f:
            scale_factor = float(f.read().strip())
        
        logger.info(f"Scaling LoadSet by factor: {scale_factor}")
        
        # Scale LoadSet
        loadset = LoadSet.from_dict(loadset_data)
        scaled_loadset = loadset.factor(scale_factor)
        
        logger.info("Scaling complete")
        
        # Prepare outputs
        outputs = {
            "scaled_loadset": scaled_loadset.to_dict()
        }
        
        logger.info("Load scaling completed successfully")
        
        # Save outputs
        save_outputs(outputs)
        
        logger.info("Step 04 completed successfully")
        
    except Exception as e:
        logger.error(f"Step 04 failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
