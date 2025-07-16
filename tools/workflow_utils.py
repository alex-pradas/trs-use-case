"""
Utilities for workflow data handling and step communication.

This module provides helper functions for loading, saving, and validating
data between workflow steps.
"""

import json
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, TypeVar, Type
import logging

from .loads import LoadSet

logger = logging.getLogger(__name__)

T = TypeVar('T')


class WorkflowDataError(Exception):
    """Raised when workflow data operations fail."""
    pass


class StepDataHandler:
    """
    Handles data loading and saving for workflow steps.
    
    Provides a standardized interface for steps to communicate with each other
    through files in the workflow directory structure.
    """
    
    def __init__(self, current_step_dir: Union[str, Path]):
        """
        Initialize the data handler.
        
        Args:
            current_step_dir: Path to the current step's directory
        """
        self.current_step_dir = Path(current_step_dir)
        self.workflow_dir = self.current_step_dir.parent
        self.input_dir = self.current_step_dir / "inputs"
        self.output_dir = self.current_step_dir / "outputs"
        
        # Ensure directories exist
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
    
    def load_from_step(self, step_name: str, filename: str, 
                      data_type: str = "auto") -> Any:
        """
        Load data from a previous step's output.
        
        Args:
            step_name: Name of the step to load from (e.g., "load_data")
            filename: Name of the file to load
            data_type: Type of data to load ("json", "pickle", "text", "auto")
            
        Returns:
            Loaded data
        """
        # Find the step directory
        step_dir = self._find_step_dir(step_name)
        if not step_dir:
            raise WorkflowDataError(f"Step '{step_name}' not found")
        
        file_path = step_dir / "outputs" / filename
        if not file_path.exists():
            raise WorkflowDataError(f"File '{filename}' not found in step '{step_name}' outputs")
        
        return self._load_file(file_path, data_type)
    
    def load_from_input(self, filename: str, data_type: str = "auto") -> Any:
        """
        Load data from the current step's input directory.
        
        Args:
            filename: Name of the file to load
            data_type: Type of data to load ("json", "pickle", "text", "auto")
            
        Returns:
            Loaded data
        """
        file_path = self.input_dir / filename
        if not file_path.exists():
            raise WorkflowDataError(f"Input file '{filename}' not found")
        
        return self._load_file(file_path, data_type)
    
    def save_to_output(self, data: Any, filename: str, data_type: str = "auto") -> None:
        """
        Save data to the current step's output directory.
        
        Args:
            data: Data to save
            filename: Name of the file to save to
            data_type: Type of data to save ("json", "pickle", "text", "auto")
        """
        file_path = self.output_dir / filename
        self._save_file(data, file_path, data_type)
    
    def load_loadset_from_step(self, step_name: str, filename: str = "loadset.json") -> LoadSet:
        """
        Load a LoadSet from a previous step's output.
        
        Args:
            step_name: Name of the step to load from
            filename: Name of the LoadSet file (default: "loadset.json")
            
        Returns:
            LoadSet instance
        """
        data = self.load_from_step(step_name, filename, "json")
        return LoadSet.from_dict(data)
    
    def save_loadset_to_output(self, loadset: LoadSet, filename: str = "loadset.json") -> None:
        """
        Save a LoadSet to the current step's output directory.
        
        Args:
            loadset: LoadSet instance to save
            filename: Name of the file to save to
        """
        self.save_to_output(loadset.to_dict(), filename, "json")
    
    def list_step_outputs(self, step_name: str) -> List[str]:
        """
        List all output files from a step.
        
        Args:
            step_name: Name of the step
            
        Returns:
            List of output filenames
        """
        step_dir = self._find_step_dir(step_name)
        if not step_dir:
            raise WorkflowDataError(f"Step '{step_name}' not found")
        
        output_dir = step_dir / "outputs"
        if not output_dir.exists():
            return []
        
        return [f.name for f in output_dir.iterdir() if f.is_file()]
    
    def list_current_inputs(self) -> List[str]:
        """
        List all input files for the current step.
        
        Returns:
            List of input filenames
        """
        return [f.name for f in self.input_dir.iterdir() if f.is_file()]
    
    def list_current_outputs(self) -> List[str]:
        """
        List all output files for the current step.
        
        Returns:
            List of output filenames
        """
        return [f.name for f in self.output_dir.iterdir() if f.is_file()]
    
    def validate_step_outputs(self, step_name: str, expected_files: List[str]) -> bool:
        """
        Validate that a step produced the expected output files.
        
        Args:
            step_name: Name of the step to validate
            expected_files: List of expected output filenames
            
        Returns:
            True if all expected files exist, False otherwise
        """
        try:
            actual_files = self.list_step_outputs(step_name)
            return all(f in actual_files for f in expected_files)
        except WorkflowDataError:
            return False
    
    def _find_step_dir(self, step_name: str) -> Optional[Path]:
        """Find the directory for a given step name."""
        for dir_path in self.workflow_dir.iterdir():
            if dir_path.is_dir() and dir_path.name.endswith(f"_{step_name}"):
                return dir_path
        return None
    
    def _load_file(self, file_path: Path, data_type: str) -> Any:
        """Load data from a file based on its type."""
        if data_type == "auto":
            data_type = self._detect_file_type(file_path)
        
        try:
            if data_type == "json":
                with open(file_path, 'r') as f:
                    return json.load(f)
            elif data_type == "pickle":
                with open(file_path, 'rb') as f:
                    return pickle.load(f)
            elif data_type == "text":
                with open(file_path, 'r') as f:
                    return f.read()
            else:
                raise WorkflowDataError(f"Unsupported data type: {data_type}")
        except Exception as e:
            raise WorkflowDataError(f"Failed to load {file_path}: {e}")
    
    def _save_file(self, data: Any, file_path: Path, data_type: str) -> None:
        """Save data to a file based on its type."""
        if data_type == "auto":
            data_type = self._detect_file_type(file_path)
        
        try:
            if data_type == "json":
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)
            elif data_type == "pickle":
                with open(file_path, 'wb') as f:
                    pickle.dump(data, f)
            elif data_type == "text":
                with open(file_path, 'w') as f:
                    f.write(str(data))
            else:
                raise WorkflowDataError(f"Unsupported data type: {data_type}")
        except Exception as e:
            raise WorkflowDataError(f"Failed to save {file_path}: {e}")
    
    def _detect_file_type(self, file_path: Path) -> str:
        """Detect file type based on extension."""
        suffix = file_path.suffix.lower()
        if suffix == '.json':
            return "json"
        elif suffix == '.pkl' or suffix == '.pickle':
            return "pickle"
        else:
            return "text"


def create_step_data_handler(current_step_dir: Union[str, Path]) -> StepDataHandler:
    """
    Create a StepDataHandler for the current step.
    
    Args:
        current_step_dir: Path to the current step's directory
        
    Returns:
        StepDataHandler instance
    """
    return StepDataHandler(current_step_dir)


def validate_workflow_structure(workflow_dir: Union[str, Path]) -> Dict[str, Any]:
    """
    Validate the structure of a workflow directory.
    
    Args:
        workflow_dir: Path to the workflow directory
        
    Returns:
        Dictionary containing validation results
    """
    workflow_dir = Path(workflow_dir)
    results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "steps": []
    }
    
    # Check for workflow.json
    if not (workflow_dir / "workflow.json").exists():
        results["errors"].append("workflow.json not found")
        results["valid"] = False
    
    # Check for README.md
    if not (workflow_dir / "README.md").exists():
        results["warnings"].append("README.md not found")
    
    # Check for run_workflow.py
    if not (workflow_dir / "run_workflow.py").exists():
        results["warnings"].append("run_workflow.py not found")
    
    # Check step directories
    step_dirs = sorted([d for d in workflow_dir.iterdir() 
                       if d.is_dir() and d.name[0].isdigit()])
    
    for step_dir in step_dirs:
        step_result = _validate_step_structure(step_dir)
        results["steps"].append(step_result)
        
        if not step_result["valid"]:
            results["valid"] = False
            results["errors"].extend([f"Step {step_dir.name}: {e}" 
                                    for e in step_result["errors"]])
    
    return results


def _validate_step_structure(step_dir: Path) -> Dict[str, Any]:
    """Validate the structure of a single step directory."""
    results = {
        "name": step_dir.name,
        "valid": True,
        "errors": [],
        "warnings": []
    }
    
    # Check for required files
    required_files = ["run.py", "README.md", "step.json"]
    for file in required_files:
        if not (step_dir / file).exists():
            results["errors"].append(f"{file} not found")
            results["valid"] = False
    
    # Check for required directories
    required_dirs = ["inputs", "outputs"]
    for dir_name in required_dirs:
        if not (step_dir / dir_name).exists():
            results["errors"].append(f"{dir_name} directory not found")
            results["valid"] = False
    
    return results


def copy_workflow_template(template_name: str, target_dir: Union[str, Path]) -> None:
    """
    Copy a workflow template to a target directory.
    
    Args:
        template_name: Name of the template to copy
        target_dir: Target directory for the workflow
    """
    # This would copy from a templates directory
    # For now, we'll create a simple example
    from .workflow_generator import WorkflowGenerator, create_loadset_workflow
    
    generator = WorkflowGenerator()
    workflow = create_loadset_workflow(template_name, f"Example {template_name} workflow")
    generator.generate_workflow(workflow, target_dir, overwrite=True)


def get_workflow_status(workflow_dir: Union[str, Path]) -> Dict[str, Any]:
    """
    Get the status of a workflow execution.
    
    Args:
        workflow_dir: Path to the workflow directory
        
    Returns:
        Dictionary containing workflow status
    """
    workflow_dir = Path(workflow_dir)
    status = {
        "workflow_dir": str(workflow_dir),
        "total_steps": 0,
        "completed_steps": 0,
        "failed_steps": 0,
        "step_status": []
    }
    
    # Find step directories
    step_dirs = sorted([d for d in workflow_dir.iterdir() 
                       if d.is_dir() and d.name[0].isdigit()])
    
    status["total_steps"] = len(step_dirs)
    
    for step_dir in step_dirs:
        step_status = {
            "name": step_dir.name,
            "has_outputs": len(list((step_dir / "outputs").glob("*"))) > 0,
            "run_py_exists": (step_dir / "run.py").exists()
        }
        
        if step_status["has_outputs"]:
            status["completed_steps"] += 1
        
        status["step_status"].append(step_status)
    
    return status