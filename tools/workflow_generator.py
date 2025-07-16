"""
Workflow generator for creating standardized LoadSet processing pipelines.

This module provides functionality to generate structured workflow directories
with standardized folder layouts and run.py files that can be executed
sequentially or individually.
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import textwrap


@dataclass
class WorkflowStep:
    """Represents a single step in a workflow."""
    name: str
    description: str
    depends_on: List[str]
    inputs: Dict[str, str]
    outputs: Dict[str, str]
    code_template: str
    requirements: List[str] = None
    
    def __post_init__(self):
        if self.requirements is None:
            self.requirements = []


@dataclass
class WorkflowDefinition:
    """Represents a complete workflow definition."""
    name: str
    description: str
    steps: List[WorkflowStep]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {
                "created_at": datetime.now().isoformat(),
                "version": "1.0.0"
            }


class WorkflowGenerator:
    """
    Generates standardized workflow directories and files.
    
    This class creates a structured folder hierarchy with:
    - Individual step folders (01_step_name, 02_step_name, etc.)
    - Standard inputs/ and outputs/ folders for each step
    - run.py files with proper imports and error handling
    - Workflow metadata and documentation
    """
    
    def __init__(self, base_path: Union[str, Path] = None):
        """
        Initialize the workflow generator.
        
        Args:
            base_path: Base directory where workflows will be created.
                      Defaults to current directory.
        """
        self.base_path = Path(base_path or ".")
        self.project_root = self._find_project_root()
        
    def _find_project_root(self) -> Path:
        """Find the project root directory (contains pyproject.toml)."""
        current = Path(__file__).parent
        while current != current.parent:
            if (current / "pyproject.toml").exists():
                return current
            current = current.parent
        return Path(__file__).parent.parent  # Fallback
    
    def generate_workflow(self, workflow_def: WorkflowDefinition, 
                         output_dir: Optional[Union[str, Path]] = None,
                         overwrite: bool = False) -> Path:
        """
        Generate a complete workflow directory structure.
        
        Args:
            workflow_def: Workflow definition containing steps and metadata
            output_dir: Directory to create the workflow in
            overwrite: Whether to overwrite existing workflow directory
            
        Returns:
            Path to the created workflow directory
        """
        if output_dir is None:
            output_dir = self.base_path / workflow_def.name
        else:
            output_dir = Path(output_dir)
            
        # Create or clean workflow directory
        if output_dir.exists():
            if overwrite:
                shutil.rmtree(output_dir)
            else:
                raise FileExistsError(f"Workflow directory already exists: {output_dir}")
                
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate workflow metadata
        self._generate_workflow_metadata(workflow_def, output_dir)
        
        # Generate step directories
        for i, step in enumerate(workflow_def.steps, 1):
            step_dir = output_dir / f"{i:02d}_{step.name}"
            self._generate_step_directory(step, step_dir, i, len(workflow_def.steps))
            
        # Generate workflow runner
        self._generate_workflow_runner(workflow_def, output_dir)
        
        # Generate documentation
        self._generate_workflow_documentation(workflow_def, output_dir)
        
        return output_dir
    
    def _generate_workflow_metadata(self, workflow_def: WorkflowDefinition, 
                                   output_dir: Path) -> None:
        """Generate workflow metadata files."""
        metadata = {
            "workflow": asdict(workflow_def),
            "generated_at": datetime.now().isoformat(),
            "generator_version": "1.0.0"
        }
        
        with open(output_dir / "workflow.json", "w") as f:
            json.dump(metadata, f, indent=2)
    
    def _generate_step_directory(self, step: WorkflowStep, step_dir: Path, 
                               step_num: int, total_steps: int) -> None:
        """Generate a single step directory with all required files."""
        # Create directory structure
        step_dir.mkdir(parents=True, exist_ok=True)
        (step_dir / "inputs").mkdir(exist_ok=True)
        (step_dir / "outputs").mkdir(exist_ok=True)
        
        # Generate run.py file
        self._generate_run_py(step, step_dir, step_num, total_steps)
        
        # Generate step metadata
        self._generate_step_metadata(step, step_dir, step_num)
        
        # Generate README
        self._generate_step_readme(step, step_dir, step_num)
        
        # Generate requirements.txt if needed
        if step.requirements:
            with open(step_dir / "requirements.txt", "w") as f:
                for req in step.requirements:
                    f.write(f"{req}\n")
    
    def _generate_run_py(self, step: WorkflowStep, step_dir: Path, 
                        step_num: int, total_steps: int) -> None:
        """Generate the run.py file for a step."""
        template = self._get_run_py_template()
        
        code_content = step.code_template or "    # TODO: Implement step logic\n    pass"
        
        # Prepare template variables
        template_vars = {
            "step_name": step.name,
            "step_description": step.description,
            "step_num": step_num,
            "total_steps": total_steps,
            "project_root": str(self.project_root),
            "code_content": code_content,
            "inputs_mapping": self._format_inputs_mapping(step.inputs),
            "outputs_mapping": self._format_outputs_mapping(step.outputs),
            "dependencies": step.depends_on,
            "validation_code": self._generate_validation_code(step)
        }
        
        run_py_content = template.format(**template_vars)
        
        with open(step_dir / "run.py", "w") as f:
            f.write(run_py_content)
    
    def _generate_step_metadata(self, step: WorkflowStep, step_dir: Path, 
                              step_num: int) -> None:
        """Generate metadata for a step."""
        metadata = {
            "step": asdict(step),
            "step_number": step_num,
            "generated_at": datetime.now().isoformat()
        }
        
        with open(step_dir / "step.json", "w") as f:
            json.dump(metadata, f, indent=2)
    
    def _generate_step_readme(self, step: WorkflowStep, step_dir: Path, 
                            step_num: int) -> None:
        """Generate README for a step."""
        readme_content = f"""# Step {step_num:02d}: {step.name}

## Description
{step.description}

## Dependencies
{', '.join(step.depends_on) if step.depends_on else 'None'}

## Inputs
{self._format_inputs_docs(step.inputs)}

## Outputs
{self._format_outputs_docs(step.outputs)}

## Usage
```bash
python run.py
```

## Requirements
{chr(10).join(f"- {req}" for req in step.requirements) if step.requirements else 'None'}
"""
        
        with open(step_dir / "README.md", "w") as f:
            f.write(readme_content)
    
    def _generate_workflow_runner(self, workflow_def: WorkflowDefinition, 
                                 output_dir: Path) -> None:
        """Generate the main workflow runner script."""
        runner_template = self._get_runner_template()
        
        runner_content = runner_template.format(
            workflow_name=workflow_def.name,
            workflow_description=workflow_def.description,
            total_steps=len(workflow_def.steps),
            project_root=str(self.project_root)
        )
        
        with open(output_dir / "run_workflow.py", "w") as f:
            f.write(runner_content)
    
    def _generate_workflow_documentation(self, workflow_def: WorkflowDefinition, 
                                       output_dir: Path) -> None:
        """Generate workflow documentation."""
        doc_content = f"""# {workflow_def.name}

## Description
{workflow_def.description}

## Steps
{self._format_steps_docs(workflow_def.steps)}

## Usage

### Run entire workflow
```bash
python run_workflow.py
```

### Run from specific step
```bash
python run_workflow.py --from-step 03
```

### Run individual step
```bash
cd 01_step_name
python run.py
```

## Generated
- **Created at:** {workflow_def.metadata.get('created_at', 'Unknown')}
- **Version:** {workflow_def.metadata.get('version', 'Unknown')}
"""
        
        with open(output_dir / "README.md", "w") as f:
            f.write(doc_content)
    
    def _get_run_py_template(self) -> str:
        """Get the template for run.py files."""
        return '''#!/usr/bin/env python3
"""
Step {step_num:02d}: {step_name}

{step_description}
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
PROJECT_ROOT = Path("{project_root}")
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
    inputs = {{}}
    
    # Load input mappings
{inputs_mapping}
    
    return inputs


def validate_inputs(inputs: Dict[str, Any]) -> bool:
    """Validate input data."""
    try:
{validation_code}
        return True
    except Exception as e:
        logger.error(f"Input validation failed: {{e}}")
        return False


def save_outputs(outputs: Dict[str, Any]) -> None:
    """Save outputs from this step."""
{outputs_mapping}


def main() -> None:
    """Main execution function."""
    logger.info("Starting step {step_num:02d}: {step_name}")
    
    try:
        # Load inputs
        inputs = load_inputs()
        logger.info(f"Loaded inputs: {{list(inputs.keys())}}")
        
        # Validate inputs
        if not validate_inputs(inputs):
            logger.error("Input validation failed")
            sys.exit(1)
        
        # Main processing logic
{code_content}
        
        # Save outputs
        save_outputs(outputs)
        
        logger.info("Step {step_num:02d} completed successfully")
        
    except Exception as e:
        logger.error(f"Step {step_num:02d} failed: {{e}}")
        sys.exit(1)


if __name__ == "__main__":
    main()
'''
    
    def _get_runner_template(self) -> str:
        """Get the template for the workflow runner."""
        return '''#!/usr/bin/env python3
"""
Workflow Runner: {workflow_name}

{workflow_description}
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
PROJECT_ROOT = Path("{project_root}")
sys.path.insert(0, str(PROJECT_ROOT))

WORKFLOW_DIR = Path(__file__).parent
TOTAL_STEPS = {total_steps}


def run_step(step_num: int) -> bool:
    """Run a single workflow step."""
    step_dirs = sorted([d for d in WORKFLOW_DIR.iterdir() 
                       if d.is_dir() and d.name.startswith(f"{{step_num:02d}}_")])
    
    if not step_dirs:
        logger.error(f"Step {{step_num:02d}} not found")
        return False
    
    step_dir = step_dirs[0]
    run_py = step_dir / "run.py"
    
    if not run_py.exists():
        logger.error(f"run.py not found in {{step_dir}}")
        return False
    
    logger.info(f"Running step {{step_num:02d}}: {{step_dir.name}}")
    
    try:
        result = subprocess.run(
            [sys.executable, str(run_py)],
            cwd=step_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info(f"Step {{step_num:02d}} completed successfully")
            if result.stdout:
                logger.info(f"Output: {{result.stdout}}")
            return True
        else:
            logger.error(f"Step {{step_num:02d}} failed with return code {{result.returncode}}")
            if result.stderr:
                logger.error(f"Error: {{result.stderr}}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to run step {{step_num:02d}}: {{e}}")
        return False


def main():
    """Main workflow execution."""
    parser = argparse.ArgumentParser(description="Run {workflow_name} workflow")
    parser.add_argument("--from-step", type=int, default=1, 
                       help="Start from this step number")
    parser.add_argument("--to-step", type=int, default=TOTAL_STEPS,
                       help="End at this step number")
    parser.add_argument("--step", type=int, help="Run only this step")
    
    args = parser.parse_args()
    
    if args.step:
        success = run_step(args.step)
        sys.exit(0 if success else 1)
    
    logger.info(f"Running workflow: {workflow_name}")
    logger.info(f"Steps {{args.from_step}} to {{args.to_step}}")
    
    for step_num in range(args.from_step, args.to_step + 1):
        if not run_step(step_num):
            logger.error(f"Workflow failed at step {{step_num}}")
            sys.exit(1)
    
    logger.info("Workflow completed successfully")


if __name__ == "__main__":
    main()
'''
    
    def _format_inputs_mapping(self, inputs: Dict[str, str]) -> str:
        """Format input mapping code."""
        if not inputs:
            return "    # No inputs defined"
        
        lines = []
        for key, path in inputs.items():
            if path.endswith('.json'):
                lines.append(f'    # Load {key} from {path}')
                lines.append(f'    with open(Path("{path}"), "r") as f:')
                lines.append(f'        inputs["{key}"] = json.load(f)')
            else:
                lines.append(f'    # Load {key} from {path}')
                lines.append(f'    inputs["{key}"] = Path("{path}")')
        
        return '\n'.join(lines)
    
    def _format_outputs_mapping(self, outputs: Dict[str, str]) -> str:
        """Format output mapping code."""
        if not outputs:
            return "    # No outputs defined"
        
        lines = []
        for key, path in outputs.items():
            if path.endswith('.json'):
                lines.append(f'    # Save {key} to {path}')
                lines.append(f'    with open(OUTPUT_DIR / "{path}", "w") as f:')
                lines.append(f'        json.dump(outputs["{key}"], f, indent=2)')
            else:
                lines.append(f'    # Save {key} to {path}')
                lines.append(f'    # TODO: Implement saving for {key}')
        
        return '\n'.join(lines)
    
    def _generate_validation_code(self, step: WorkflowStep) -> str:
        """Generate validation code for step inputs."""
        lines = []
        for key, path in step.inputs.items():
            lines.append(f'        # Validate {key}')
            lines.append(f'        if "{key}" not in inputs:')
            lines.append(f'            raise ValueError("{key} not found in inputs")')
            
            if 'loadset' in key.lower():
                lines.append(f'        # Validate LoadSet structure')
                lines.append(f'        if isinstance(inputs["{key}"], dict):')
                lines.append(f'            if "load_cases" not in inputs["{key}"]:')
                lines.append(f'                raise ValueError("Invalid LoadSet: missing load_cases")')
        
        return '\n'.join(lines) if lines else "        # No validation needed"
    
    def _format_inputs_docs(self, inputs: Dict[str, str]) -> str:
        """Format inputs documentation."""
        if not inputs:
            return "None"
        
        lines = []
        for key, path in inputs.items():
            lines.append(f"- **{key}**: `{path}`")
        
        return '\n'.join(lines)
    
    def _format_outputs_docs(self, outputs: Dict[str, str]) -> str:
        """Format outputs documentation."""
        if not outputs:
            return "None"
        
        lines = []
        for key, path in outputs.items():
            lines.append(f"- **{key}**: `{path}`")
        
        return '\n'.join(lines)
    
    def _format_steps_docs(self, steps: List[WorkflowStep]) -> str:
        """Format steps documentation."""
        lines = []
        for i, step in enumerate(steps, 1):
            lines.append(f"{i:02d}. **{step.name}**: {step.description}")
            if step.depends_on:
                lines.append(f"    - Dependencies: {', '.join(step.depends_on)}")
        
        return '\n'.join(lines)


def create_simple_step(name: str, description: str, 
                      depends_on: List[str] = None,
                      inputs: Dict[str, str] = None,
                      outputs: Dict[str, str] = None,
                      code_template: str = None) -> WorkflowStep:
    """Helper function to create a simple workflow step."""
    return WorkflowStep(
        name=name,
        description=description,
        depends_on=depends_on or [],
        inputs=inputs or {},
        outputs=outputs or {},
        code_template=code_template or "    # TODO: Implement step logic\n    pass"
    )


def create_loadset_workflow(name: str, description: str) -> WorkflowDefinition:
    """Create a sample LoadSet processing workflow."""
    steps = [
        create_simple_step(
            name="load_data",
            description="Load LoadSet data from JSON file",
            inputs={"source_file": "inputs/loadset.json"},
            outputs={"loadset": "loadset.json"},
            code_template="""        # Load LoadSet from JSON file
        source_file = inputs["source_file"]
        loadset = LoadSet.read_json(source_file)
        
        # Prepare outputs
        outputs = {
            "loadset": loadset.to_dict()
        }"""
        ),
        create_simple_step(
            name="convert_units",
            description="Convert LoadSet to target units",
            depends_on=["load_data"],
            inputs={"loadset": "../01_load_data/outputs/loadset.json", "target_units": "inputs/target_units.txt"},
            outputs={"converted_loadset": "converted_loadset.json"},
            code_template="""        # Load LoadSet and target units
        loadset_data = inputs["loadset"]
        with open(inputs["target_units"], "r") as f:
            target_units = f.read().strip()
        
        # Convert LoadSet
        loadset = LoadSet.from_dict(loadset_data)
        converted_loadset = loadset.convert_to(target_units)
        
        # Prepare outputs
        outputs = {
            "converted_loadset": converted_loadset.to_dict()
        }"""
        ),
        create_simple_step(
            name="generate_ansys",
            description="Generate ANSYS input files",
            depends_on=["convert_units"],
            inputs={"loadset": "../02_convert_units/outputs/converted_loadset.json"},
            outputs={"ansys_files": "ansys_files/"},
            code_template="""        # Load converted LoadSet
        loadset_data = inputs["loadset"]
        loadset = LoadSet.from_dict(loadset_data)
        
        # Generate ANSYS files
        ansys_dir = OUTPUT_DIR / "ansys_files"
        ansys_dir.mkdir(exist_ok=True)
        loadset.to_ansys(ansys_dir, "loadset")
        
        # Prepare outputs
        outputs = {
            "ansys_files": str(ansys_dir)
        }"""
        )
    ]
    
    return WorkflowDefinition(
        name=name,
        description=description,
        steps=steps
    )