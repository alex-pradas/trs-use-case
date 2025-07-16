"""
Tests for the workflow generator and utilities.

This module tests the workflow generation system, including:
- WorkflowGenerator functionality
- StepDataHandler utilities
- Workflow validation
"""

import pytest
import tempfile
import json
import os
import shutil
from pathlib import Path

from tools.workflow_generator import (
    WorkflowGenerator,
    WorkflowDefinition,
    WorkflowStep,
    create_simple_step,
    create_loadset_workflow,
)

from tools.workflow_utils import (
    StepDataHandler,
    WorkflowDataError,
    validate_workflow_structure,
    get_workflow_status,
)

from tools.loads import LoadSet


# =============================================================================
# WORKFLOW GENERATOR TESTS
# =============================================================================

class TestWorkflowGenerator:
    """Test WorkflowGenerator functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.generator = WorkflowGenerator(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_create_simple_workflow(self):
        """Test creating a simple workflow."""
        steps = [
            create_simple_step(
                name="step_one",
                description="First step",
                inputs={"input_file": "inputs/data.json"},
                outputs={"output_file": "result.json"}
            ),
            create_simple_step(
                name="step_two",
                description="Second step",
                depends_on=["step_one"],
                inputs={"previous_result": "../01_step_one/outputs/result.json"},
                outputs={"final_result": "final.json"}
            )
        ]
        
        workflow = WorkflowDefinition(
            name="test_workflow",
            description="A test workflow",
            steps=steps
        )
        
        # Generate the workflow
        workflow_dir = self.generator.generate_workflow(workflow)
        
        # Verify directory structure
        assert workflow_dir.exists()
        assert (workflow_dir / "workflow.json").exists()
        assert (workflow_dir / "README.md").exists()
        assert (workflow_dir / "run_workflow.py").exists()
        
        # Verify step directories
        step1_dir = workflow_dir / "01_step_one"
        step2_dir = workflow_dir / "02_step_two"
        
        assert step1_dir.exists()
        assert step2_dir.exists()
        
        # Verify step structure
        for step_dir in [step1_dir, step2_dir]:
            assert (step_dir / "run.py").exists()
            assert (step_dir / "README.md").exists()
            assert (step_dir / "step.json").exists()
            assert (step_dir / "inputs").exists()
            assert (step_dir / "outputs").exists()
    
    def test_create_loadset_workflow(self):
        """Test creating a LoadSet processing workflow."""
        workflow = create_loadset_workflow(
            "loadset_processing",
            "Process LoadSet data through conversion and ANSYS export"
        )
        
        workflow_dir = self.generator.generate_workflow(workflow)
        
        # Verify LoadSet-specific workflow structure
        assert workflow_dir.exists()
        step_dirs = [d for d in workflow_dir.iterdir() if d.is_dir() and d.name[0].isdigit()]
        assert len(step_dirs) == 3  # Three steps
        
        # Check specific step directories
        load_step = workflow_dir / "01_load_data"
        convert_step = workflow_dir / "02_convert_units"
        ansys_step = workflow_dir / "03_generate_ansys"
        
        assert load_step.exists()
        assert convert_step.exists()
        assert ansys_step.exists()
        
        # Verify run.py files contain LoadSet-specific code
        load_run_py = (load_step / "run.py").read_text()
        assert "LoadSet" in load_run_py
        assert "read_json" in load_run_py
        
        convert_run_py = (convert_step / "run.py").read_text()
        assert "convert_to" in convert_run_py
        
        ansys_run_py = (ansys_step / "run.py").read_text()
        assert "to_ansys" in ansys_run_py
    
    def test_workflow_overwrite(self):
        """Test workflow overwrite functionality."""
        workflow = create_loadset_workflow("test", "Test workflow")
        
        # Create workflow first time
        workflow_dir = self.generator.generate_workflow(workflow)
        assert workflow_dir.exists()
        
        # Create again without overwrite - should fail
        with pytest.raises(FileExistsError):
            self.generator.generate_workflow(workflow)
        
        # Create again with overwrite - should succeed
        workflow_dir2 = self.generator.generate_workflow(workflow, overwrite=True)
        assert workflow_dir2.exists()
        assert workflow_dir == workflow_dir2


# =============================================================================
# STEP DATA HANDLER TESTS
# =============================================================================

class TestStepDataHandler:
    """Test StepDataHandler functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create a mock workflow structure
        self.workflow_dir = self.temp_dir / "test_workflow"
        self.step1_dir = self.workflow_dir / "01_load_data"
        self.step2_dir = self.workflow_dir / "02_process_data"
        
        # Create directory structure
        for step_dir in [self.step1_dir, self.step2_dir]:
            step_dir.mkdir(parents=True, exist_ok=True)
            (step_dir / "inputs").mkdir(exist_ok=True)
            (step_dir / "outputs").mkdir(exist_ok=True)
        
        self.handler = StepDataHandler(self.step2_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_save_and_load_json(self):
        """Test saving and loading JSON data."""
        test_data = {"test": "data", "number": 42}
        
        # Save to output
        self.handler.save_to_output(test_data, "test.json")
        
        # Verify file exists
        output_file = self.step2_dir / "outputs" / "test.json"
        assert output_file.exists()
        
        # Load from input (simulate next step)
        step3_dir = self.workflow_dir / "03_next_step"
        step3_dir.mkdir(parents=True, exist_ok=True)
        (step3_dir / "inputs").mkdir(exist_ok=True)
        (step3_dir / "outputs").mkdir(exist_ok=True)
        
        step3_handler = StepDataHandler(step3_dir)
        loaded_data = step3_handler.load_from_step("process_data", "test.json")
        
        assert loaded_data == test_data
    
    def test_loadset_operations(self):
        """Test LoadSet-specific operations."""
        # Create a sample LoadSet
        from tools.loads import LoadSet, LoadCase, PointLoad, ForceMoment, Units
        
        loadset = LoadSet(
            name="Test LoadSet",
            version=1,
            units=Units(forces="N", moments="Nm"),
            load_cases=[
                LoadCase(
                    name="Case 1",
                    point_loads=[
                        PointLoad(
                            name="Point A",
                            force_moment=ForceMoment(fx=100, fy=200, fz=300)
                        )
                    ]
                )
            ]
        )
        
        # Save LoadSet
        self.handler.save_loadset_to_output(loadset)
        
        # Verify file exists
        output_file = self.step2_dir / "outputs" / "loadset.json"
        assert output_file.exists()
        
        # Load LoadSet from previous step
        loaded_loadset = self.handler.load_loadset_from_step("process_data", "loadset.json")
        
        assert loaded_loadset.name == "Test LoadSet"
        assert len(loaded_loadset.load_cases) == 1
        assert loaded_loadset.load_cases[0].point_loads[0].force_moment.fx == 100
    
    def test_list_operations(self):
        """Test listing files operations."""
        # Create some test files
        (self.step1_dir / "outputs" / "file1.json").touch()
        (self.step1_dir / "outputs" / "file2.txt").touch()
        (self.step2_dir / "inputs" / "input1.json").touch()
        (self.step2_dir / "outputs" / "output1.json").touch()
        
        # Test listing step outputs
        step1_outputs = self.handler.list_step_outputs("load_data")
        assert "file1.json" in step1_outputs
        assert "file2.txt" in step1_outputs
        
        # Test listing current inputs and outputs
        current_inputs = self.handler.list_current_inputs()
        current_outputs = self.handler.list_current_outputs()
        
        assert "input1.json" in current_inputs
        assert "output1.json" in current_outputs
    
    def test_validation(self):
        """Test step output validation."""
        # Create expected files
        (self.step1_dir / "outputs" / "required1.json").touch()
        (self.step1_dir / "outputs" / "required2.txt").touch()
        
        # Test successful validation
        assert self.handler.validate_step_outputs("load_data", ["required1.json", "required2.txt"])
        
        # Test failed validation
        assert not self.handler.validate_step_outputs("load_data", ["missing.json"])
    
    def test_error_handling(self):
        """Test error handling."""
        # Test loading from non-existent step
        with pytest.raises(WorkflowDataError):
            self.handler.load_from_step("nonexistent", "file.json")
        
        # Test loading non-existent file
        with pytest.raises(WorkflowDataError):
            self.handler.load_from_step("load_data", "nonexistent.json")
        
        # Test loading from non-existent input
        with pytest.raises(WorkflowDataError):
            self.handler.load_from_input("nonexistent.json")


# =============================================================================
# WORKFLOW VALIDATION TESTS
# =============================================================================

class TestWorkflowValidation:
    """Test workflow validation functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.generator = WorkflowGenerator(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_valid_workflow_validation(self):
        """Test validation of a valid workflow."""
        workflow = create_loadset_workflow("test", "Test workflow")
        workflow_dir = self.generator.generate_workflow(workflow)
        
        validation_result = validate_workflow_structure(workflow_dir)
        
        assert validation_result["valid"] is True
        assert len(validation_result["errors"]) == 0
        assert len(validation_result["steps"]) == 3
        
        # Check individual step validation
        for step in validation_result["steps"]:
            assert step["valid"] is True
    
    def test_invalid_workflow_validation(self):
        """Test validation of an invalid workflow."""
        # Create incomplete workflow structure
        workflow_dir = self.temp_dir / "incomplete_workflow"
        workflow_dir.mkdir(exist_ok=True)
        
        # Missing workflow.json and other required files
        validation_result = validate_workflow_structure(workflow_dir)
        
        assert validation_result["valid"] is False
        assert "workflow.json not found" in validation_result["errors"]
    
    def test_workflow_status(self):
        """Test workflow status functionality."""
        workflow = create_loadset_workflow("test", "Test workflow")
        workflow_dir = self.generator.generate_workflow(workflow)
        
        # Initial status - no outputs
        status = get_workflow_status(workflow_dir)
        assert status["total_steps"] == 3
        assert status["completed_steps"] == 0
        
        # Create some outputs to simulate progress
        step1_dir = workflow_dir / "01_load_data"
        (step1_dir / "outputs" / "result.json").touch()
        
        # Updated status
        status = get_workflow_status(workflow_dir)
        assert status["completed_steps"] == 1


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestWorkflowIntegration:
    """Test end-to-end workflow functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.generator = WorkflowGenerator(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_loadset_workflow_execution_simulation(self):
        """Test simulating LoadSet workflow execution."""
        # Create LoadSet workflow
        workflow = create_loadset_workflow("integration_test", "Integration test workflow")
        workflow_dir = self.generator.generate_workflow(workflow)
        
        # Simulate step 1: Load data
        step1_dir = workflow_dir / "01_load_data"
        step1_handler = StepDataHandler(step1_dir)
        
        # Create sample LoadSet in step 1 inputs
        sample_loadset_data = {
            "name": "Test LoadSet",
            "version": 1,
            "units": {"forces": "N", "moments": "Nm"},
            "load_cases": [
                {
                    "name": "Case 1",
                    "point_loads": [
                        {
                            "name": "Point A",
                            "force_moment": {
                                "fx": 100.0,
                                "fy": 200.0,
                                "fz": 300.0,
                                "mx": 10.0,
                                "my": 20.0,
                                "mz": 30.0
                            }
                        }
                    ]
                }
            ]
        }
        
        # Save sample data as input
        with open(step1_dir / "inputs" / "loadset.json", "w") as f:
            json.dump(sample_loadset_data, f)
        
        # Simulate step 1 execution (save output)
        step1_handler.save_to_output(sample_loadset_data, "loadset.json")
        
        # Simulate step 2: Convert units
        step2_dir = workflow_dir / "02_convert_units"
        step2_handler = StepDataHandler(step2_dir)
        
        # Create target units input
        with open(step2_dir / "inputs" / "target_units.txt", "w") as f:
            f.write("kN")
        
        # Load from step 1 and simulate conversion
        loadset_data = step2_handler.load_from_step("load_data", "loadset.json")
        loadset = LoadSet.from_dict(loadset_data)
        converted_loadset = loadset.convert_to("kN")
        
        # Save converted result
        step2_handler.save_loadset_to_output(converted_loadset, "converted_loadset.json")
        
        # Verify conversion worked
        assert converted_loadset.units.forces == "kN"
        assert converted_loadset.load_cases[0].point_loads[0].force_moment.fx == 0.1  # 100 N = 0.1 kN
        
        # Check workflow status
        status = get_workflow_status(workflow_dir)
        assert status["completed_steps"] == 2  # Two steps have outputs now
        assert status["total_steps"] == 3
    
    def test_custom_workflow_creation(self):
        """Test creating a custom workflow."""
        steps = [
            WorkflowStep(
                name="analyze_data",
                description="Analyze LoadSet data for extremes",
                depends_on=[],
                inputs={"loadset": "inputs/loadset.json"},
                outputs={"analysis": "analysis.json"},
                code_template="""        # Load and analyze LoadSet
        loadset_data = inputs["loadset"]
        loadset = LoadSet.from_dict(loadset_data)
        
        # Get point extremes
        extremes = loadset.get_point_extremes()
        
        # Prepare outputs
        outputs = {
            "analysis": {
                "extremes": extremes,
                "num_points": len(extremes),
                "num_load_cases": len(loadset.load_cases)
            }
        }"""
            ),
            WorkflowStep(
                name="generate_report",
                description="Generate summary report",
                depends_on=["analyze_data"],
                inputs={"analysis": "../01_analyze_data/outputs/analysis.json"},
                outputs={"report": "report.txt"},
                code_template="""        # Load analysis results
        analysis = inputs["analysis"]
        
        # Generate report
        report_lines = [
            f"LoadSet Analysis Report",
            f"======================",
            f"Number of points: {analysis['num_points']}",
            f"Number of load cases: {analysis['num_load_cases']}",
            f"",
            f"Point extremes: {list(analysis['extremes'].keys())}"
        ]
        
        report_content = "\\n".join(report_lines)
        
        # Prepare outputs
        outputs = {
            "report": report_content
        }"""
            )
        ]
        
        workflow = WorkflowDefinition(
            name="custom_analysis",
            description="Custom LoadSet analysis workflow",
            steps=steps
        )
        
        workflow_dir = self.generator.generate_workflow(workflow)
        
        # Verify custom workflow structure
        assert workflow_dir.exists()
        assert (workflow_dir / "01_analyze_data").exists()
        assert (workflow_dir / "02_generate_report").exists()
        
        # Verify custom code is in run.py files
        analyze_run_py = (workflow_dir / "01_analyze_data" / "run.py").read_text()
        assert "get_point_extremes" in analyze_run_py
        
        report_run_py = (workflow_dir / "02_generate_report" / "run.py").read_text()
        assert "LoadSet Analysis Report" in report_run_py


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])