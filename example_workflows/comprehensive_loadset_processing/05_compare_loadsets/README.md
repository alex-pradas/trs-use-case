# Step 05: compare_loadsets

## Description
Compare the processed LoadSet with the comparison LoadSet

## Dependencies
scale_loads, load_comparison_loadset

## Inputs
- **primary_loadset**: `../04_scale_loads/outputs/scaled_loadset.json`
- **comparison_loadset**: `../02_load_comparison_loadset/outputs/comparison_loadset.json`

## Outputs
- **comparison**: `comparison.json`

## Usage
```bash
python run.py
```

## Requirements
None
