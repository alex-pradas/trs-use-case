#!/usr/bin/env python3
"""
Step 05: compare_loadsets

Compare the processed LoadSet with the comparison LoadSet
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
    # Load primary_loadset from ../04_scale_loads/outputs/scaled_loadset.json
    with open(Path("../04_scale_loads/outputs/scaled_loadset.json"), "r") as f:
        inputs["primary_loadset"] = json.load(f)
    # Load comparison_loadset from ../02_load_comparison_loadset/outputs/comparison_loadset.json
    with open(Path("../02_load_comparison_loadset/outputs/comparison_loadset.json"), "r") as f:
        inputs["comparison_loadset"] = json.load(f)
    
    return inputs


def validate_inputs(inputs: Dict[str, Any]) -> bool:
    """Validate input data."""
    try:
        # Validate primary_loadset
        if "primary_loadset" not in inputs:
            raise ValueError("primary_loadset not found in inputs")
        # Validate LoadSet structure
        if isinstance(inputs["primary_loadset"], dict):
            if "load_cases" not in inputs["primary_loadset"]:
                raise ValueError("Invalid LoadSet: missing load_cases")
        # Validate comparison_loadset
        if "comparison_loadset" not in inputs:
            raise ValueError("comparison_loadset not found in inputs")
        # Validate LoadSet structure
        if isinstance(inputs["comparison_loadset"], dict):
            if "load_cases" not in inputs["comparison_loadset"]:
                raise ValueError("Invalid LoadSet: missing load_cases")
        return True
    except Exception as e:
        logger.error(f"Input validation failed: {e}")
        return False


def save_outputs(outputs: Dict[str, Any]) -> None:
    """Save outputs from this step."""
    # Save comparison to comparison.json
    with open(OUTPUT_DIR / "comparison.json", "w") as f:
        json.dump(outputs["comparison"], f, indent=2)


def main() -> None:
    """Main execution function."""
    logger.info("Starting step 05: compare_loadsets")
    
    try:
        # Load inputs
        inputs = load_inputs()
        logger.info(f"Loaded inputs: {list(inputs.keys())}")
        
        # Validate inputs
        if not validate_inputs(inputs):
            logger.error("Input validation failed")
            sys.exit(1)
        
        # Main processing logic
        # Load both LoadSets
        primary_data = inputs["primary_loadset"]
        comparison_data = inputs["comparison_loadset"]
        
        primary_loadset = LoadSet.from_dict(primary_data)
        comparison_loadset = LoadSet.from_dict(comparison_data)
        
        logger.info(f"Comparing LoadSets: {primary_loadset.name} vs {comparison_loadset.name}")
        
        # Perform comparison
        comparison = primary_loadset.compare_to(comparison_loadset)
        
        logger.info(f"Comparison complete. Found {len(comparison.comparison_rows)} comparison rows")
        
        # Prepare outputs
        outputs = {
            "comparison": comparison.to_dict()
        }
        
        logger.info("LoadSet comparison completed successfully")
        
        # Save outputs
        save_outputs(outputs)
        
        logger.info("Step 05 completed successfully")
        
    except Exception as e:
        logger.error(f"Step 05 failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
