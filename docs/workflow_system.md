# LoadSet Workflow System

## Overview

The LoadSet Workflow System provides a structured approach to creating reproducible, traceable, and human-friendly processing pipelines for LoadSet data. The system breaks complex operations into discrete steps organized in numbered subfolders, enabling both automated execution and manual intervention.

## Key Features

- **Structured Organization**: Each workflow step is in its own folder with standardized inputs/outputs
- **Traceability**: Complete audit trail of data transformations
- **Human-Friendly**: Can be executed by humans without AI agents
- **Reproducible**: Re-runnable workflows with explicit dependencies
- **Modular**: Steps can be modified, skipped, or replaced independently

## Architecture

### Folder Structure

```
workflow_name/
├── workflow.json          # Workflow metadata
├── README.md             # Workflow documentation
├── run_workflow.py       # Main workflow runner
├── 01_step_name/
│   ├── run.py           # Step execution script
│   ├── README.md        # Step documentation
│   ├── step.json        # Step metadata
│   ├── inputs/          # Input files and data
│   └── outputs/         # Generated outputs
├── 02_next_step/
│   ├── run.py
│   ├── inputs/
│   └── outputs/
└── ...
```

### Data Flow

1. **Inputs**: Each step reads from its `inputs/` folder and previous steps' `outputs/`
2. **Processing**: Step logic is contained in `run.py` with proper error handling
3. **Outputs**: Results are saved to the step's `outputs/` folder
4. **Dependencies**: Steps can reference outputs from previous steps using relative paths

## Core Components

### WorkflowGenerator

Creates complete workflow directory structures with standardized templates.

```python
from tools.workflow_generator import WorkflowGenerator, create_loadset_workflow

# Create a generator
generator = WorkflowGenerator("./my_workflows")

# Create a LoadSet processing workflow
workflow = create_loadset_workflow("process_loads", "Process LoadSet data")
workflow_dir = generator.generate_workflow(workflow)
```

### StepDataHandler

Provides utilities for data communication between workflow steps.

```python
from tools.workflow_utils import StepDataHandler

# Initialize handler for current step
handler = StepDataHandler(Path(__file__).parent)

# Load data from previous step
data = handler.load_from_step("previous_step", "data.json")

# Load LoadSet specifically
loadset = handler.load_loadset_from_step("load_data", "loadset.json")

# Save outputs
handler.save_to_output(result, "result.json")
handler.save_loadset_to_output(processed_loadset)
```

### WorkflowStep and WorkflowDefinition

Define workflow structure programmatically.

```python
from tools.workflow_generator import WorkflowStep, WorkflowDefinition

step = WorkflowStep(
    name="convert_units",
    description="Convert LoadSet to target units",
    depends_on=["load_data"],
    inputs={"loadset": "../01_load_data/outputs/loadset.json"},
    outputs={"converted": "converted_loadset.json"},
    code_template="# Custom processing code here"
)

workflow = WorkflowDefinition(
    name="my_workflow",
    description="Custom workflow",
    steps=[step]
)
```

## Common Workflow Patterns

### 1. Basic LoadSet Processing

```python
steps = [
    create_simple_step(
        name="load_data",
        description="Load LoadSet from JSON",
        inputs={"file": "inputs/loadset.json"},
        outputs={"loadset": "loadset.json"}
    ),
    create_simple_step(
        name="process",
        description="Process the LoadSet",
        depends_on=["load_data"],
        inputs={"loadset": "../01_load_data/outputs/loadset.json"},
        outputs={"result": "processed.json"}
    )
]
```

### 2. LoadSet Comparison

```python
steps = [
    create_simple_step(
        name="load_loadsets",
        description="Load both LoadSets",
        inputs={
            "loadset1": "inputs/first.json",
            "loadset2": "inputs/second.json"
        },
        outputs={
            "loadset1": "first.json",
            "loadset2": "second.json"
        }
    ),
    create_simple_step(
        name="compare",
        description="Compare LoadSets",
        depends_on=["load_loadsets"],
        inputs={
            "loadset1": "../01_load_loadsets/outputs/first.json",
            "loadset2": "../01_load_loadsets/outputs/second.json"
        },
        outputs={"comparison": "comparison.json"}
    )
]
```

### 3. Multi-Stage Processing

```python
# Load → Convert → Scale → Export pipeline
workflow = create_loadset_workflow("full_process", "Complete LoadSet processing")
```

## Step Implementation Guidelines

### Standard run.py Template

Each `run.py` file follows this pattern:

```python
#!/usr/bin/env python3
"""
Step Description Here
"""

import json
import sys
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.loads import LoadSet
from tools.workflow_utils import StepDataHandler

def main():
    """Main execution function."""
    handler = StepDataHandler(Path(__file__).parent)
    
    try:
        # Load inputs
        inputs = {}
        # ... load data using handler
        
        # Process
        # ... your processing logic here
        
        # Save outputs
        # ... save results using handler
        
        logger.info("Step completed successfully")
        
    except Exception as e:
        logger.error(f"Step failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### Error Handling

- Always use try/catch blocks in step execution
- Log informative messages at each stage
- Exit with non-zero code on failure
- Validate inputs before processing
- Check outputs after processing

### Data Validation

```python
def validate_inputs(handler: StepDataHandler) -> bool:
    """Validate inputs for this step."""
    required_files = ["data.json"]
    
    for file in required_files:
        if not handler.input_dir.joinpath(file).exists():
            logger.error(f"Required input file missing: {file}")
            return False
    
    return True
```

## Execution Methods

### 1. Complete Workflow

```bash
cd workflow_directory
python run_workflow.py
```

### 2. Partial Execution

```bash
# Run from step 3 onwards
python run_workflow.py --from-step 3

# Run up to step 5
python run_workflow.py --to-step 5

# Run only step 4
python run_workflow.py --step 4
```

### 3. Individual Steps

```bash
cd workflow_directory/03_process_data
python run.py
```

### 4. Manual Execution

Each step can be run manually by:
1. Ensuring inputs are in the `inputs/` folder
2. Running `python run.py`
3. Checking outputs in the `outputs/` folder

## Validation and Status

### Workflow Validation

```python
from tools.workflow_utils import validate_workflow_structure

validation = validate_workflow_structure("./my_workflow")
if validation["valid"]:
    print("Workflow structure is valid")
else:
    print("Issues found:", validation["errors"])
```

### Execution Status

```python
from tools.workflow_utils import get_workflow_status

status = get_workflow_status("./my_workflow")
print(f"Completed: {status['completed_steps']}/{status['total_steps']}")
```

## Example Workflows

### Create Example Workflows

```bash
cd tools
python create_example_workflow.py --type both --output-dir ../example_workflows
```

This creates:
- `comprehensive_loadset_processing/`: Full LoadSet processing pipeline
- `loadset_comparison/`: LoadSet comparison and visualization

### Run Example Workflow

```bash
cd example_workflows/comprehensive_loadset_processing
python run_workflow.py
```

## Best Practices

### 1. Naming Conventions

- **Workflows**: Use descriptive names with underscores (`loadset_processing`)
- **Steps**: Use verb phrases (`load_data`, `convert_units`, `generate_report`)
- **Files**: Use lowercase with underscores (`loadset.json`, `comparison_results.json`)

### 2. Input/Output Management

- **Inputs**: Place all external inputs in step `inputs/` folders
- **Intermediate Data**: Use JSON for LoadSet data, text for simple values
- **Large Files**: Consider using relative paths and symbolic links
- **Documentation**: Include sample input files with workflows

### 3. Error Recovery

- **Validation**: Validate inputs before processing
- **Logging**: Provide detailed progress logging
- **Cleanup**: Clean up partial outputs on failure
- **Idempotency**: Make steps re-runnable without side effects

### 4. Documentation

- **Step README**: Explain what each step does and its requirements
- **Workflow README**: Provide overview and usage instructions
- **Comments**: Include inline comments in complex processing logic
- **Examples**: Provide sample inputs and expected outputs

## Integration with Agents

### Agent-Generated Workflows

Agents can use the workflow system to:

1. **Parse User Requests**: Break complex requests into workflow steps
2. **Generate Code**: Create appropriate `run.py` files for each step
3. **Handle Dependencies**: Set up proper input/output relationships
4. **Create Documentation**: Generate README files and comments

### Example Agent Integration

```python
# Agent receives user request:
# "Load data from file.json, convert to kN, scale by 1.5, and export to ANSYS"

def create_workflow_from_request(request: str) -> WorkflowDefinition:
    # Parse request and identify steps
    steps = [
        create_loadset_step("load", "Load data from JSON"),
        create_conversion_step("convert", "Convert to kN"),
        create_scaling_step("scale", "Scale by 1.5"),
        create_export_step("export", "Export to ANSYS")
    ]
    
    return WorkflowDefinition("user_request", request, steps)
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure PROJECT_ROOT is correctly added to Python path
2. **File Not Found**: Check input file paths and dependencies
3. **Permission Errors**: Verify write permissions in output directories
4. **JSON Errors**: Validate JSON syntax in data files

### Debugging Steps

1. **Check Logs**: Review step logs for error details
2. **Validate Structure**: Use workflow validation functions
3. **Test Individual Steps**: Run problematic steps in isolation
4. **Verify Inputs**: Ensure all required input files exist and are valid

### Recovery Strategies

1. **Restart from Step**: Use `--from-step` to resume from specific step
2. **Fix Inputs**: Correct input files and re-run failed step
3. **Manual Intervention**: Manually create missing outputs and continue
4. **Step Modification**: Edit step code for specific issues

## Future Enhancements

### Planned Features

- **Parallel Execution**: Run independent steps in parallel
- **Conditional Steps**: Steps that execute based on conditions
- **Loop Constructs**: Repeat steps with different parameters
- **Web Interface**: Visual workflow builder and monitor
- **Version Control**: Track workflow and step version changes

### Extension Points

- **Custom Step Types**: Define reusable step templates
- **Plugin System**: Add custom processing capabilities
- **Remote Execution**: Run steps on different machines
- **Database Integration**: Store workflow metadata in database
- **API Interface**: RESTful API for workflow management

## Conclusion

The LoadSet Workflow System provides a robust foundation for creating maintainable, traceable, and human-friendly data processing pipelines. By following the established patterns and best practices, users can create workflows that are both powerful and accessible, supporting both automated execution and manual intervention as needed.