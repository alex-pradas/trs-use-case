# comprehensive_loadset_processing

## Description
Comprehensive LoadSet processing workflow with conversion, scaling, comparison, and export

## Steps
01. **load_primary_loadset**: Load the primary LoadSet from JSON file
02. **load_comparison_loadset**: Load the comparison LoadSet from JSON file
03. **convert_units**: Convert LoadSet to target units
    - Dependencies: load_primary_loadset
04. **scale_loads**: Apply scaling factor to all loads
    - Dependencies: convert_units
05. **compare_loadsets**: Compare the processed LoadSet with the comparison LoadSet
    - Dependencies: scale_loads, load_comparison_loadset
06. **generate_envelope**: Generate envelope LoadSet with extreme values
    - Dependencies: scale_loads
07. **export_to_ansys**: Export LoadSet to ANSYS input files
    - Dependencies: generate_envelope
08. **generate_report**: Generate comprehensive processing report
    - Dependencies: compare_loadsets, export_to_ansys

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
- **Created at:** 2025-07-16T18:25:27.078510
- **Version:** 1.0.0
