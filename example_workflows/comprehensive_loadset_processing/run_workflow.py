#!/usr/bin/env python3
"""
Workflow Runner: comprehensive_loadset_processing

Comprehensive LoadSet processing workflow with conversion, scaling, comparison, and export
"""

import argparse
import subprocess
import sys
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to Python path
PROJECT_ROOT = Path("/Users/alex/repos/trs-use-case")
sys.path.insert(0, str(PROJECT_ROOT))

WORKFLOW_DIR = Path(__file__).parent
TOTAL_STEPS = 8


def run_step(step_num: int) -> bool:
    """Run a single workflow step."""
    step_dirs = sorted([d for d in WORKFLOW_DIR.iterdir() 
                       if d.is_dir() and d.name.startswith(f"{step_num:02d}_")])
    
    if not step_dirs:
        logger.error(f"Step {step_num:02d} not found")
        return False
    
    step_dir = step_dirs[0]
    run_py = step_dir / "run.py"
    
    if not run_py.exists():
        logger.error(f"run.py not found in {step_dir}")
        return False
    
    logger.info(f"Running step {step_num:02d}: {step_dir.name}")
    
    try:
        result = subprocess.run(
            [sys.executable, str(run_py)],
            cwd=step_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info(f"Step {step_num:02d} completed successfully")
            if result.stdout:
                logger.info(f"Output: {result.stdout}")
            return True
        else:
            logger.error(f"Step {step_num:02d} failed with return code {result.returncode}")
            if result.stderr:
                logger.error(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to run step {step_num:02d}: {e}")
        return False


def main():
    """Main workflow execution."""
    parser = argparse.ArgumentParser(description="Run comprehensive_loadset_processing workflow")
    parser.add_argument("--from-step", type=int, default=1, 
                       help="Start from this step number")
    parser.add_argument("--to-step", type=int, default=TOTAL_STEPS,
                       help="End at this step number")
    parser.add_argument("--step", type=int, help="Run only this step")
    
    args = parser.parse_args()
    
    if args.step:
        success = run_step(args.step)
        sys.exit(0 if success else 1)
    
    logger.info(f"Running workflow: comprehensive_loadset_processing")
    logger.info(f"Steps {args.from_step} to {args.to_step}")
    
    for step_num in range(args.from_step, args.to_step + 1):
        if not run_step(step_num):
            logger.error(f"Workflow failed at step {step_num}")
            sys.exit(1)
    
    logger.info("Workflow completed successfully")


if __name__ == "__main__":
    main()
