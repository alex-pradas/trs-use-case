#!/usr/bin/env python3
"""
Example script to create a complete LoadSet processing workflow.

This script demonstrates how to use the workflow generator to create
a structured pipeline for LoadSet processing tasks.
"""

import json
from pathlib import Path
import sys

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.workflow_generator import (
    WorkflowGenerator,
    WorkflowDefinition,
    create_simple_step,
)


def create_comprehensive_loadset_workflow() -> WorkflowDefinition:
    """
    Create a comprehensive LoadSet processing workflow.
    
    This workflow demonstrates:
    - Loading LoadSet data
    - Unit conversion
    - Scaling operations
    - Comparison with another LoadSet
    - Envelope generation
    - ANSYS export
    - Report generation
    """
    
    steps = [
        # Step 1: Load primary LoadSet
        create_simple_step(
            name="load_primary_loadset",
            description="Load the primary LoadSet from JSON file",
            inputs={"loadset_file": "inputs/primary_loadset.json"},
            outputs={"loadset": "primary_loadset.json"},
            code_template="""        # Load LoadSet from JSON file
        loadset_file = inputs["loadset_file"]
        
        logger.info(f"Loading LoadSet from: {loadset_file}")
        loadset = LoadSet.read_json(loadset_file)
        
        logger.info(f"Loaded LoadSet: {loadset.name}")
        logger.info(f"Number of load cases: {len(loadset.load_cases)}")
        logger.info(f"Units: {loadset.units.forces}, {loadset.units.moments}")
        
        # Prepare outputs
        outputs = {
            "loadset": loadset.to_dict()
        }
        
        logger.info("Primary LoadSet loaded successfully")"""
        ),
        
        # Step 2: Load comparison LoadSet
        create_simple_step(
            name="load_comparison_loadset",
            description="Load the comparison LoadSet from JSON file",
            inputs={"loadset_file": "inputs/comparison_loadset.json"},
            outputs={"loadset": "comparison_loadset.json"},
            code_template="""        # Load comparison LoadSet from JSON file
        loadset_file = inputs["loadset_file"]
        
        logger.info(f"Loading comparison LoadSet from: {loadset_file}")
        loadset = LoadSet.read_json(loadset_file)
        
        logger.info(f"Loaded comparison LoadSet: {loadset.name}")
        logger.info(f"Number of load cases: {len(loadset.load_cases)}")
        logger.info(f"Units: {loadset.units.forces}, {loadset.units.moments}")
        
        # Prepare outputs
        outputs = {
            "loadset": loadset.to_dict()
        }
        
        logger.info("Comparison LoadSet loaded successfully")"""
        ),
        
        # Step 3: Convert units
        create_simple_step(
            name="convert_units",
            description="Convert LoadSet to target units",
            depends_on=["load_primary_loadset"],
            inputs={
                "loadset": "../01_load_primary_loadset/outputs/primary_loadset.json",
                "target_units": "inputs/target_units.txt"
            },
            outputs={"converted_loadset": "converted_loadset.json"},
            code_template="""        # Load LoadSet and target units
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
        
        logger.info("Unit conversion completed successfully")"""
        ),
        
        # Step 4: Scale loads
        create_simple_step(
            name="scale_loads",
            description="Apply scaling factor to all loads",
            depends_on=["convert_units"],
            inputs={
                "loadset": "../03_convert_units/outputs/converted_loadset.json",
                "scale_factor": "inputs/scale_factor.txt"
            },
            outputs={"scaled_loadset": "scaled_loadset.json"},
            code_template="""        # Load LoadSet and scale factor
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
        
        logger.info("Load scaling completed successfully")"""
        ),
        
        # Step 5: Compare LoadSets
        create_simple_step(
            name="compare_loadsets",
            description="Compare the processed LoadSet with the comparison LoadSet",
            depends_on=["scale_loads", "load_comparison_loadset"],
            inputs={
                "primary_loadset": "../04_scale_loads/outputs/scaled_loadset.json",
                "comparison_loadset": "../02_load_comparison_loadset/outputs/comparison_loadset.json"
            },
            outputs={"comparison": "comparison.json"},
            code_template="""        # Load both LoadSets
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
        
        logger.info("LoadSet comparison completed successfully")"""
        ),
        
        # Step 6: Generate envelope
        create_simple_step(
            name="generate_envelope",
            description="Generate envelope LoadSet with extreme values",
            depends_on=["scale_loads"],
            inputs={"loadset": "../04_scale_loads/outputs/scaled_loadset.json"},
            outputs={"envelope_loadset": "envelope_loadset.json"},
            code_template="""        # Load LoadSet
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
        
        logger.info("Envelope generation completed successfully")"""
        ),
        
        # Step 7: Export to ANSYS
        create_simple_step(
            name="export_to_ansys",
            description="Export LoadSet to ANSYS input files",
            depends_on=["generate_envelope"],
            inputs={"loadset": "../06_generate_envelope/outputs/envelope_loadset.json"},
            outputs={"ansys_files": "ansys_files/"},
            code_template="""        # Load envelope LoadSet
        loadset_data = inputs["loadset"]
        loadset = LoadSet.from_dict(loadset_data)
        
        logger.info(f"Exporting LoadSet to ANSYS format: {loadset.name}")
        
        # Create ANSYS output directory
        ansys_dir = OUTPUT_DIR / "ansys_files"
        ansys_dir.mkdir(exist_ok=True)
        
        # Export to ANSYS
        loadset.to_ansys(ansys_dir, "envelope_loads")
        
        # List generated files
        ansys_files = list(ansys_dir.glob("*.inp"))
        logger.info(f"Generated {len(ansys_files)} ANSYS files")
        for file in ansys_files:
            logger.info(f"  - {file.name}")
        
        # Prepare outputs
        outputs = {
            "ansys_files": str(ansys_dir)
        }
        
        logger.info("ANSYS export completed successfully")"""
        ),
        
        # Step 8: Generate report
        create_simple_step(
            name="generate_report",
            description="Generate comprehensive processing report",
            depends_on=["compare_loadsets", "export_to_ansys"],
            inputs={
                "comparison": "../05_compare_loadsets/outputs/comparison.json",
                "ansys_files": "../07_export_to_ansys/outputs/ansys_files/"
            },
            outputs={"report": "processing_report.txt", "summary": "summary.json"},
            code_template="""        # Load comparison results
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
        
        report_content = "\\n".join(report_lines)
        
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
        
        logger.info("Report generation completed successfully")"""
        )
    ]
    
    return WorkflowDefinition(
        name="comprehensive_loadset_processing",
        description="Comprehensive LoadSet processing workflow with conversion, scaling, comparison, and export",
        steps=steps
    )


def create_comparison_workflow() -> WorkflowDefinition:
    """
    Create a workflow focused on LoadSet comparison and visualization.
    """
    
    steps = [
        create_simple_step(
            name="load_loadsets",
            description="Load both LoadSets for comparison",
            inputs={
                "loadset1_file": "inputs/loadset1.json",
                "loadset2_file": "inputs/loadset2.json"
            },
            outputs={
                "loadset1": "loadset1.json",
                "loadset2": "loadset2.json"
            },
            code_template="""        # Load both LoadSets
        loadset1 = LoadSet.read_json(inputs["loadset1_file"])
        loadset2 = LoadSet.read_json(inputs["loadset2_file"])
        
        logger.info(f"Loaded LoadSet 1: {loadset1.name} ({len(loadset1.load_cases)} cases)")
        logger.info(f"Loaded LoadSet 2: {loadset2.name} ({len(loadset2.load_cases)} cases)")
        
        # Prepare outputs
        outputs = {
            "loadset1": loadset1.to_dict(),
            "loadset2": loadset2.to_dict()
        }
        
        logger.info("LoadSets loaded successfully")"""
        ),
        
        create_simple_step(
            name="perform_comparison",
            description="Compare the two LoadSets",
            depends_on=["load_loadsets"],
            inputs={
                "loadset1": "../01_load_loadsets/outputs/loadset1.json",
                "loadset2": "../01_load_loadsets/outputs/loadset2.json"
            },
            outputs={"comparison": "comparison.json"},
            code_template="""        # Load LoadSets
        loadset1 = LoadSet.from_dict(inputs["loadset1"])
        loadset2 = LoadSet.from_dict(inputs["loadset2"])
        
        logger.info("Performing LoadSet comparison")
        
        # Perform comparison
        comparison = loadset1.compare_to(loadset2)
        
        logger.info(f"Comparison complete: {len(comparison.comparison_rows)} rows")
        
        # Calculate some statistics
        max_diff = max((row.abs_diff for row in comparison.comparison_rows), default=0)
        avg_diff = sum(row.abs_diff for row in comparison.comparison_rows) / len(comparison.comparison_rows) if comparison.comparison_rows else 0
        
        logger.info(f"Max absolute difference: {max_diff:.3f}")
        logger.info(f"Average absolute difference: {avg_diff:.3f}")
        
        # Prepare outputs
        outputs = {
            "comparison": comparison.to_dict()
        }
        
        logger.info("Comparison completed successfully")"""
        ),
        
        create_simple_step(
            name="generate_charts",
            description="Generate comparison charts",
            depends_on=["perform_comparison"],
            inputs={"comparison": "../02_perform_comparison/outputs/comparison.json"},
            outputs={"charts": "charts/"},
            code_template="""        # Load comparison data
        comparison_data = inputs["comparison"]
        
        logger.info("Generating comparison charts")
        
        # Recreate LoadSetCompare object
        from tools.loads import LoadSetCompare, ComparisonRow
        
        comparison_rows = [ComparisonRow(**row) for row in comparison_data["comparison_rows"]]
        comparison = LoadSetCompare(
            loadset1_metadata=comparison_data["metadata"]["loadset1"],
            loadset2_metadata=comparison_data["metadata"]["loadset2"],
            comparison_rows=comparison_rows
        )
        
        # Generate charts
        charts_dir = OUTPUT_DIR / "charts"
        charts_dir.mkdir(exist_ok=True)
        
        try:
            chart_files = comparison.generate_range_charts(
                output_dir=charts_dir,
                image_format="png",
                as_base64=False
            )
            
            logger.info(f"Generated {len(chart_files)} chart files:")
            for point, file_path in chart_files.items():
                logger.info(f"  - {point}: {Path(file_path).name}")
                
        except ImportError:
            logger.warning("matplotlib not available, skipping chart generation")
            chart_files = {}
        
        # Prepare outputs
        outputs = {
            "charts": str(charts_dir)
        }
        
        logger.info("Chart generation completed")"""
        )
    ]
    
    return WorkflowDefinition(
        name="loadset_comparison",
        description="Compare two LoadSets and generate visualization charts",
        steps=steps
    )


def main():
    """Main function to create example workflows."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Create example LoadSet workflows")
    parser.add_argument("--type", choices=["comprehensive", "comparison", "both"], 
                       default="both", help="Type of workflow to create")
    parser.add_argument("--output-dir", default="./example_workflows", 
                       help="Output directory for workflows")
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    generator = WorkflowGenerator(output_dir)
    
    if args.type in ["comprehensive", "both"]:
        print("Creating comprehensive LoadSet processing workflow...")
        comprehensive_workflow = create_comprehensive_loadset_workflow()
        comprehensive_dir = generator.generate_workflow(comprehensive_workflow, overwrite=True)
        print(f"✅ Comprehensive workflow created at: {comprehensive_dir}")
        
        # Create sample input files
        create_sample_inputs(comprehensive_dir)
    
    if args.type in ["comparison", "both"]:
        print("Creating LoadSet comparison workflow...")
        comparison_workflow = create_comparison_workflow()
        comparison_dir = generator.generate_workflow(comparison_workflow, overwrite=True)
        print(f"✅ Comparison workflow created at: {comparison_dir}")
        
        # Create sample input files
        create_comparison_inputs(comparison_dir)
    
    print("\n🎉 Example workflows created successfully!")
    print("\nTo run a workflow:")
    print("  cd <workflow_directory>")
    print("  python run_workflow.py")
    print("\nTo run individual steps:")
    print("  cd <workflow_directory>/<step_directory>")
    print("  python run.py")


def create_sample_inputs(workflow_dir: Path):
    """Create sample input files for the comprehensive workflow."""
    import datetime
    
    # Create sample LoadSet data
    sample_loadset = {
        "name": "Sample LoadSet",
        "version": 1,
        "description": "Sample LoadSet for workflow testing",
        "units": {"forces": "N", "moments": "Nm"},
        "load_cases": [
            {
                "name": "Case_1",
                "description": "First load case",
                "point_loads": [
                    {
                        "name": "Point_A",
                        "force_moment": {
                            "fx": 1000.0, "fy": 1500.0, "fz": 2000.0,
                            "mx": 100.0, "my": 150.0, "mz": 200.0
                        }
                    },
                    {
                        "name": "Point_B",
                        "force_moment": {
                            "fx": 800.0, "fy": 1200.0, "fz": 1600.0,
                            "mx": 80.0, "my": 120.0, "mz": 160.0
                        }
                    }
                ]
            },
            {
                "name": "Case_2",
                "description": "Second load case",
                "point_loads": [
                    {
                        "name": "Point_A",
                        "force_moment": {
                            "fx": 1200.0, "fy": 1800.0, "fz": 2400.0,
                            "mx": 120.0, "my": 180.0, "mz": 240.0
                        }
                    },
                    {
                        "name": "Point_B",
                        "force_moment": {
                            "fx": 900.0, "fy": 1350.0, "fz": 1800.0,
                            "mx": 90.0, "my": 135.0, "mz": 180.0
                        }
                    }
                ]
            }
        ]
    }
    
    comparison_loadset = {
        "name": "Comparison LoadSet",
        "version": 1,
        "description": "Comparison LoadSet for workflow testing",
        "units": {"forces": "N", "moments": "Nm"},
        "load_cases": [
            {
                "name": "Comp_Case_1",
                "description": "First comparison case",
                "point_loads": [
                    {
                        "name": "Point_A",
                        "force_moment": {
                            "fx": 1050.0, "fy": 1575.0, "fz": 2100.0,
                            "mx": 105.0, "my": 157.5, "mz": 210.0
                        }
                    },
                    {
                        "name": "Point_B",
                        "force_moment": {
                            "fx": 840.0, "fy": 1260.0, "fz": 1680.0,
                            "mx": 84.0, "my": 126.0, "mz": 168.0
                        }
                    }
                ]
            }
        ]
    }
    
    # Create input files for each step
    steps = [
        ("01_load_primary_loadset", {"primary_loadset.json": sample_loadset}),
        ("02_load_comparison_loadset", {"comparison_loadset.json": comparison_loadset}),
        ("03_convert_units", {"target_units.txt": "kN"}),
        ("04_scale_loads", {"scale_factor.txt": "1.5"}),
    ]
    
    for step_name, files in steps:
        step_dir = workflow_dir / step_name / "inputs"
        step_dir.mkdir(parents=True, exist_ok=True)
        
        for filename, content in files.items():
            if filename.endswith('.json'):
                with open(step_dir / filename, 'w') as f:
                    json.dump(content, f, indent=2)
            else:
                with open(step_dir / filename, 'w') as f:
                    f.write(str(content))


def create_comparison_inputs(workflow_dir: Path):
    """Create sample input files for the comparison workflow."""
    # Create two similar LoadSets with slight differences
    loadset1 = {
        "name": "LoadSet A",
        "version": 1,
        "units": {"forces": "N", "moments": "Nm"},
        "load_cases": [
            {
                "name": "Case_1",
                "point_loads": [
                    {
                        "name": "Point_A",
                        "force_moment": {"fx": 1000.0, "fy": 2000.0, "fz": 3000.0}
                    }
                ]
            }
        ]
    }
    
    loadset2 = {
        "name": "LoadSet B",
        "version": 1,
        "units": {"forces": "N", "moments": "Nm"},
        "load_cases": [
            {
                "name": "Case_1",
                "point_loads": [
                    {
                        "name": "Point_A",
                        "force_moment": {"fx": 1100.0, "fy": 2200.0, "fz": 3300.0}
                    }
                ]
            }
        ]
    }
    
    # Create input files
    inputs_dir = workflow_dir / "01_load_loadsets" / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    
    with open(inputs_dir / "loadset1.json", 'w') as f:
        json.dump(loadset1, f, indent=2)
    
    with open(inputs_dir / "loadset2.json", 'w') as f:
        json.dump(loadset2, f, indent=2)


if __name__ == "__main__":
    main()