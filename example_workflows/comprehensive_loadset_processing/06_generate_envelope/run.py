#!/usr/bin/env python3
"""
Step 06: generate_envelope

Generate envelope LoadSet with extreme values
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
    # Load loadset from ../04_scale_loads/outputs/scaled_loadset.json
    with open(Path("../04_scale_loads/outputs/scaled_loadset.json"), "r") as f:
        inputs["loadset"] = json.load(f)
    
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
        return True
    except Exception as e:
        logger.error(f"Input validation failed: {e}")
        return False


def save_outputs(outputs: Dict[str, Any]) -> None:
    """Save outputs from this step."""
    # Save envelope_loadset to envelope_loadset.json
    with open(OUTPUT_DIR / "envelope_loadset.json", "w") as f:
        json.dump(outputs["envelope_loadset"], f, indent=2)


def main() -> None:
    """Main execution function."""
    logger.info("Starting step 06: generate_envelope")
    
    try:
        # Load inputs
        inputs = load_inputs()
        logger.info(f"Loaded inputs: {list(inputs.keys())}")
        
        # Validate inputs
        if not validate_inputs(inputs):
            logger.error("Input validation failed")
            sys.exit(1)
        
        # Main processing logic
        # Load LoadSet
        loadset_data = inputs["loadset"]
        loadset = LoadSet.from_dict(loadset_data)
        
        logger.info(f"Generating envelope for LoadSet: {loadset.name}")
        logger.info(f"Original load cases: {len(loadset.load_cases)}")
        
        # Generate envelope
        envelope_loadset = loadset.envelope()
        
        logger.info(f"Envelope load cases: {len(envelope_loadset.load_cases)}")
        reduction = ((len(loadset.load_cases) - len(envelope_loadset.load_cases)) / len(loadset.load_cases)) * 100
        logger.info(f"Reduction: {reduction:.1f}%")
        
        # Prepare outputs
        outputs = {
            "envelope_loadset": envelope_loadset.to_dict()
        }
        
        logger.info("Envelope generation completed successfully")
        
        # Save outputs
        save_outputs(outputs)
        
        logger.info("Step 06 completed successfully")
        
    except Exception as e:
        logger.error(f"Step 06 failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
