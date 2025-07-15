"""
Template scripts and utilities for LoadSet processing.

This module provides pre-built script templates for common LoadSet operations
that can be used by the script generation agent.
"""

from typing import Dict, List, Optional
from pathlib import Path


class LoadSetScriptTemplates:
    """Collection of script templates for LoadSet operations."""

    @staticmethod
    def basic_load_and_export(
        input_file: str,
        target_units: str = "kN",
        scale_factor: float = 1.0,
        output_format: str = "ansys",
        output_stem: str = "processed_loads",
    ) -> str:
        """
        Generate a basic load, convert, scale, and export script.

        Args:
            input_file: Path to input JSON file
            target_units: Target units for conversion
            scale_factor: Factor to scale loads by
            output_format: Output format ("ansys", "json")
            output_stem: Name stem for output files

        Returns:
            str: Complete Python script
        """
        return f'''
# LoadSet Processing Script: Load, Convert, Scale, Export
# Generated template for basic LoadSet operations

import json
from pathlib import Path

def main():
    """Main processing function."""
    print("🚀 Starting LoadSet processing...")
    
    # Configuration
    input_file = "{input_file}"
    target_units = "{target_units}"
    scale_factor = {scale_factor}
    output_format = "{output_format}"
    output_stem = "{output_stem}"
    
    try:
        # Step 1: Load LoadSet from JSON
        print(f"📂 Loading LoadSet from: {{input_file}}")
        loadset = LoadSet.read_json(input_file)
        print(f"✅ Loaded LoadSet: {{loadset.name}}")
        print(f"   Units: {{loadset.force_units}} / {{loadset.moment_units}}")
        print(f"   Load cases: {{len(loadset.load_cases)}}")
        
        # Step 2: Convert units if needed
        if target_units != str(loadset.force_units):
            print(f"🔄 Converting units to {{target_units}}")
            loadset = loadset.convert_to(target_units)
            print(f"✅ Units converted to: {{loadset.force_units}} / {{loadset.moment_units}}")
        
        # Step 3: Scale loads if factor != 1.0
        if scale_factor != 1.0:
            print(f"📊 Scaling loads by factor: {{scale_factor}}")
            loadset = loadset.factor(scale_factor)
            print("✅ Loads scaled successfully")
        
        # Step 4: Export based on format
        if output_format == "ansys":
            print(f"💾 Exporting to ANSYS format...")
            loadset.to_ansys(".", output_stem)
            print(f"✅ ANSYS files exported with stem: {{output_stem}}")
            
        elif output_format == "json":
            output_file = f"{{output_stem}}.json"
            print(f"💾 Exporting to JSON: {{output_file}}")
            Path(output_file).write_text(
                json.dumps(loadset.to_dict(), indent=2),
                encoding='utf-8'
            )
            print(f"✅ JSON exported to: {{output_file}}")
        
        # Step 5: Create summary
        summary = {{
            "input_file": input_file,
            "output_format": output_format,
            "target_units": target_units,
            "scale_factor": scale_factor,
            "load_cases_count": len(loadset.load_cases),
            "final_units": {{
                "force": str(loadset.force_units),
                "moment": str(loadset.moment_units)
            }},
            "processing_complete": True
        }}
        
        summary_file = f"{{output_stem}}_summary.json"
        Path(summary_file).write_text(json.dumps(summary, indent=2), encoding='utf-8')
        print(f"📋 Summary saved to: {{summary_file}}")
        
        print("🎉 Processing completed successfully!")
        return summary
        
    except Exception as e:
        error_msg = f"❌ Error during processing: {{str(e)}}"
        print(error_msg)
        
        # Save error log
        error_log = {{
            "error": str(e),
            "input_file": input_file,
            "processing_step": "unknown"
        }}
        Path("error_log.json").write_text(json.dumps(error_log, indent=2), encoding='utf-8')
        raise

if __name__ == "__main__":
    main()
'''

    @staticmethod
    def load_comparison_script(
        file1: str, file2: str, output_stem: str = "comparison"
    ) -> str:
        """
        Generate a script for comparing two LoadSets.

        Args:
            file1: Path to first LoadSet JSON file
            file2: Path to second LoadSet JSON file
            output_stem: Name stem for output files

        Returns:
            str: Complete Python script
        """
        return f'''
# LoadSet Comparison Script
# Compare two LoadSet files and generate analysis

import json
from pathlib import Path

def main():
    """Main comparison function."""
    print("🚀 Starting LoadSet comparison...")
    
    # Configuration
    file1 = "{file1}"
    file2 = "{file2}"
    output_stem = "{output_stem}"
    
    try:
        # Step 1: Load both LoadSets
        print(f"📂 Loading first LoadSet from: {{file1}}")
        loadset1 = LoadSet.read_json(file1)
        print(f"✅ Loaded: {{loadset1.name}} ({{len(loadset1.load_cases)}} cases)")
        
        print(f"📂 Loading second LoadSet from: {{file2}}")
        loadset2 = LoadSet.read_json(file2)
        print(f"✅ Loaded: {{loadset2.name}} ({{len(loadset2.load_cases)}} cases)")
        
        # Step 2: Perform comparison
        print("🔍 Performing LoadSet comparison...")
        comparison = loadset1.compare_to(loadset2)
        print(f"✅ Comparison completed: {{len(comparison.comparison_data)}} comparisons")
        
        # Step 3: Generate comparison statistics
        stats = {{
            "total_comparisons": len(comparison.comparison_data),
            "loadset1_cases": len(loadset1.load_cases),
            "loadset2_cases": len(loadset2.load_cases),
            "comparison_summary": {{
                "file1": file1,
                "file2": file2,
                "loadset1_name": loadset1.name,
                "loadset2_name": loadset2.name
            }}
        }}
        
        # Find max differences
        if comparison.comparison_data:
            max_diff = max(comparison.comparison_data, key=lambda x: abs(x.value_difference))
            stats["max_difference"] = {{
                "load_case": max_diff.load_case_name,
                "point": max_diff.point_name,
                "component": max_diff.component,
                "value1": max_diff.value1,
                "value2": max_diff.value2,
                "difference": max_diff.value_difference,
                "percent_diff": max_diff.percent_difference
            }}
        
        # Step 4: Export comparison results
        comparison_file = f"{{output_stem}}_data.json"
        print(f"💾 Exporting comparison data to: {{comparison_file}}")
        comparison.export_json(comparison_file)
        
        stats_file = f"{{output_stem}}_stats.json"
        print(f"📊 Exporting statistics to: {{stats_file}}")
        Path(stats_file).write_text(json.dumps(stats, indent=2), encoding='utf-8')
        
        # Step 5: Generate range charts if possible
        try:
            print("📈 Generating comparison charts...")
            charts_result = comparison.generate_range_charts(
                save_as_files=True,
                output_prefix=output_stem
            )
            if charts_result.get("success"):
                print(f"✅ Charts saved: {{charts_result.get('files_created', [])}}")
            else:
                print(f"⚠️ Chart generation failed: {{charts_result.get('error', 'Unknown error')}}")
        except Exception as chart_error:
            print(f"⚠️ Chart generation not available: {{str(chart_error)}}")
        
        print("🎉 Comparison completed successfully!")
        return stats
        
    except Exception as e:
        error_msg = f"❌ Error during comparison: {{str(e)}}"
        print(error_msg)
        
        # Save error log
        error_log = {{
            "error": str(e),
            "file1": file1,
            "file2": file2
        }}
        Path("comparison_error_log.json").write_text(json.dumps(error_log, indent=2), encoding='utf-8')
        raise

if __name__ == "__main__":
    main()
'''

    @staticmethod
    def unit_conversion_analysis(
        input_file: str,
        target_units_list: List[str],
        output_stem: str = "unit_analysis",
    ) -> str:
        """
        Generate a script for analyzing LoadSet in different units.

        Args:
            input_file: Path to input LoadSet JSON file
            target_units_list: List of units to convert to
            output_stem: Name stem for output files

        Returns:
            str: Complete Python script
        """
        units_str = ", ".join([f'"{u}"' for u in target_units_list])

        return f'''
# LoadSet Unit Conversion Analysis Script
# Analyze LoadSet data in multiple unit systems

import json
from pathlib import Path

def main():
    """Main analysis function."""
    print("🚀 Starting unit conversion analysis...")
    
    # Configuration
    input_file = "{input_file}"
    target_units = [{units_str}]
    output_stem = "{output_stem}"
    
    try:
        # Step 1: Load original LoadSet
        print(f"📂 Loading LoadSet from: {{input_file}}")
        original_loadset = LoadSet.read_json(input_file)
        print(f"✅ Loaded: {{original_loadset.name}}")
        print(f"   Original units: {{original_loadset.force_units}} / {{original_loadset.moment_units}}")
        
        # Step 2: Convert to each target unit system
        conversion_results = {{}}
        
        for target_unit in target_units:
            print(f"🔄 Converting to {{target_unit}} units...")
            converted_loadset = original_loadset.convert_to(target_unit)
            
            # Extract sample values for comparison
            sample_values = {{}}
            if converted_loadset.load_cases:
                first_case = converted_loadset.load_cases[0]
                if first_case.point_loads:
                    first_point = first_case.point_loads[0]
                    sample_values = {{
                        "fx": first_point.load.force.fx,
                        "fy": first_point.load.force.fy,
                        "fz": first_point.load.force.fz,
                        "mx": first_point.load.moment.mx,
                        "my": first_point.load.moment.my,
                        "mz": first_point.load.moment.mz
                    }}
            
            conversion_results[target_unit] = {{
                "force_units": str(converted_loadset.force_units),
                "moment_units": str(converted_loadset.moment_units),
                "sample_values": sample_values,
                "total_cases": len(converted_loadset.load_cases)
            }}
            
            # Export converted LoadSet
            output_file = f"{{output_stem}}_{{target_unit}}.json"
            Path(output_file).write_text(
                json.dumps(converted_loadset.to_dict(), indent=2),
                encoding='utf-8'
            )
            print(f"💾 Saved {{target_unit}} version to: {{output_file}}")
        
        # Step 3: Create analysis summary
        analysis = {{
            "input_file": input_file,
            "original_loadset_name": original_loadset.name,
            "original_units": {{
                "force": str(original_loadset.force_units),
                "moment": str(original_loadset.moment_units)
            }},
            "conversions": conversion_results,
            "analysis_complete": True
        }}
        
        analysis_file = f"{{output_stem}}_analysis.json"
        Path(analysis_file).write_text(json.dumps(analysis, indent=2), encoding='utf-8')
        print(f"📋 Analysis summary saved to: {{analysis_file}}")
        
        print("🎉 Unit conversion analysis completed!")
        return analysis
        
    except Exception as e:
        error_msg = f"❌ Error during analysis: {{str(e)}}"
        print(error_msg)
        
        # Save error log
        error_log = {{
            "error": str(e),
            "input_file": input_file,
            "target_units": target_units
        }}
        Path("unit_analysis_error_log.json").write_text(json.dumps(error_log, indent=2), encoding='utf-8')
        raise

if __name__ == "__main__":
    main()
'''

    @staticmethod
    def custom_script_template(
        operations: List[str],
        input_files: List[str],
        output_stem: str = "custom_processing",
    ) -> str:
        """
        Generate a custom script template based on operations list.

        Args:
            operations: List of operations to perform
            input_files: List of input files
            output_stem: Name stem for output files

        Returns:
            str: Complete Python script template
        """
        operations_code = "\\n".join([f"        # {op}" for op in operations])
        input_files_str = ", ".join([f'"{f}"' for f in input_files])

        return f'''
# Custom LoadSet Processing Script
# Template for custom operations on LoadSet data

import json
from pathlib import Path

def main():
    """Main processing function."""
    print("🚀 Starting custom LoadSet processing...")
    
    # Configuration
    input_files = [{input_files_str}]
    output_stem = "{output_stem}"
    
    # Operations to perform:
{operations_code}
    
    try:
        results = {{}}
        
        # Load input files
        loadsets = {{}}
        for i, input_file in enumerate(input_files):
            print(f"📂 Loading LoadSet from: {{input_file}}")
            loadsets[f"loadset_{{i+1}}"] = LoadSet.read_json(input_file)
            print(f"✅ Loaded: {{loadsets[f'loadset_{{i+1}}'].name}}")
        
        # TODO: Implement custom operations here
        # The operations list provides guidance on what to implement:
        {chr(10).join([f"        # - {op}" for op in operations])}
        
        # Example processing (customize based on operations):
        if loadsets:
            first_loadset = list(loadsets.values())[0]
            
            # Basic summary
            results["summary"] = {{
                "total_loadsets": len(loadsets),
                "first_loadset_cases": len(first_loadset.load_cases),
                "first_loadset_units": {{
                    "force": str(first_loadset.force_units),
                    "moment": str(first_loadset.moment_units)
                }}
            }}
        
        # Save results
        results_file = f"{{output_stem}}_results.json"
        Path(results_file).write_text(json.dumps(results, indent=2), encoding='utf-8')
        print(f"📋 Results saved to: {{results_file}}")
        
        print("🎉 Custom processing completed!")
        return results
        
    except Exception as e:
        error_msg = f"❌ Error during processing: {{str(e)}}"
        print(error_msg)
        
        # Save error log
        error_log = {{
            "error": str(e),
            "input_files": input_files,
            "operations": {operations}
        }}
        Path("custom_processing_error_log.json").write_text(json.dumps(error_log, indent=2), encoding='utf-8')
        raise

if __name__ == "__main__":
    main()
'''


def get_template_by_operation_type(operation_type: str, **kwargs) -> str:
    """
    Get a script template based on operation type.

    Args:
        operation_type: Type of operation ("basic", "comparison", "unit_analysis", "custom")
        **kwargs: Template-specific arguments

    Returns:
        str: Complete Python script
    """
    templates = LoadSetScriptTemplates()

    if operation_type == "basic":
        return templates.basic_load_and_export(**kwargs)
    elif operation_type == "comparison":
        return templates.load_comparison_script(**kwargs)
    elif operation_type == "unit_analysis":
        return templates.unit_conversion_analysis(**kwargs)
    elif operation_type == "custom":
        return templates.custom_script_template(**kwargs)
    else:
        raise ValueError(f"Unknown operation type: {operation_type}")


def analyze_instruction_for_template(instruction: str) -> Dict[str, any]:
    """
    Analyze an instruction and suggest a template type and parameters.

    Args:
        instruction: Natural language instruction

    Returns:
        Dict containing template suggestion
    """
    instruction_lower = instruction.lower()

    # Check for comparison keywords
    if any(
        word in instruction_lower
        for word in ["compare", "comparison", "versus", "vs", "difference"]
    ):
        return {
            "template_type": "comparison",
            "confidence": 0.8,
            "suggested_params": {"output_stem": "comparison"},
        }

    # Check for unit analysis keywords
    if any(
        word in instruction_lower
        for word in ["unit", "units", "convert", "conversion", "kn", "lbf", "klbf"]
    ):
        if "different" in instruction_lower or "multiple" in instruction_lower:
            return {
                "template_type": "unit_analysis",
                "confidence": 0.7,
                "suggested_params": {
                    "target_units_list": ["kN", "lbf", "klbf"],
                    "output_stem": "unit_analysis",
                },
            }

    # Check for basic processing keywords
    if any(
        word in instruction_lower
        for word in ["load", "scale", "export", "ansys", "factor"]
    ):
        return {
            "template_type": "basic",
            "confidence": 0.6,
            "suggested_params": {
                "target_units": "kN",
                "scale_factor": 1.0,
                "output_format": "ansys",
                "output_stem": "processed_loads",
            },
        }

    # Default to custom template
    return {
        "template_type": "custom",
        "confidence": 0.3,
        "suggested_params": {
            "operations": ["Process LoadSet data", "Generate output files"],
            "output_stem": "custom_processing",
        },
    }
