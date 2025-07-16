#!/usr/bin/env python3
"""
Step 08: generate_report

Generate comprehensive processing report
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
    # Load comparison from ../05_compare_loadsets/outputs/comparison.json
    with open(Path("../05_compare_loadsets/outputs/comparison.json"), "r") as f:
        inputs["comparison"] = json.load(f)
    # Load ansys_files from ../07_export_to_ansys/outputs/ansys_files/
    inputs["ansys_files"] = Path("../07_export_to_ansys/outputs/ansys_files/")
    
    return inputs


def validate_inputs(inputs: Dict[str, Any]) -> bool:
    """Validate input data."""
    try:
        # Validate comparison
        if "comparison" not in inputs:
            raise ValueError("comparison not found in inputs")
        # Validate ansys_files
        if "ansys_files" not in inputs:
            raise ValueError("ansys_files not found in inputs")
        return True
    except Exception as e:
        logger.error(f"Input validation failed: {e}")
        return False


def save_outputs(outputs: Dict[str, Any]) -> None:
    """Save outputs from this step."""
    # Save report to processing_report.txt
    # TODO: Implement saving for report
    # Save summary to summary.json
    with open(OUTPUT_DIR / "summary.json", "w") as f:
        json.dump(outputs["summary"], f, indent=2)


def main() -> None:
    """Main execution function."""
    logger.info("Starting step 08: generate_report")
    
    try:
        # Load inputs
        inputs = load_inputs()
        logger.info(f"Loaded inputs: {list(inputs.keys())}")
        
        # Validate inputs
        if not validate_inputs(inputs):
            logger.error("Input validation failed")
            sys.exit(1)
        
        # Main processing logic
        # Load comparison results
        comparison_data = inputs["comparison"]
        ansys_files_dir = Path(inputs["ansys_files"])
        
        logger.info("Generating comprehensive processing report")
        
        # Count ANSYS files
        ansys_files = list(ansys_files_dir.glob("*.inp"))
        
        # Generate report
        report_lines = [
            "LoadSet Processing Report",
            "=" * 50,
            "",
            f"Processing completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "Summary:",
            f"- Comparison rows generated: {len(comparison_data['comparison_rows'])}",
            f"- ANSYS files generated: {len(ansys_files)}",
            "",
            "ANSYS Files:",
        ]
        
        for file in ansys_files:
            report_lines.append(f"  - {file.name}")
        
        report_lines.extend([
            "",
            "Comparison Summary:",
            f"- LoadSet 1: {comparison_data['metadata']['loadset1']['name']}",
            f"- LoadSet 2: {comparison_data['metadata']['loadset2']['name']}",
            f"- Total comparison rows: {len(comparison_data['comparison_rows'])}",
        ])
        
        report_content = "\n".join(report_lines)
        
        # Generate summary
        summary = {
            "processing_date": datetime.now().isoformat(),
            "comparison_rows": len(comparison_data['comparison_rows']),
            "ansys_files_generated": len(ansys_files),
            "loadset1_name": comparison_data['metadata']['loadset1']['name'],
            "loadset2_name": comparison_data['metadata']['loadset2']['name']
        }
        
        # Prepare outputs
        outputs = {
            "report": report_content,
            "summary": summary
        }
        
        logger.info("Report generation completed successfully")
        
        # Save outputs
        save_outputs(outputs)
        
        logger.info("Step 08 completed successfully")
        
    except Exception as e:
        logger.error(f"Step 08 failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
