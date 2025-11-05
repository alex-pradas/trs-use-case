# Standalone LoadSet Processing Evaluation

This directory contains a self-contained evaluation script for LoadSet processing using a local Qwen model server via vLLM.

## Contents

- `standalone_eval.py` - Self-contained Python script with agent, tools, and vLLM integration
- `03_A_new_loads.json` - Sample loads data for testing

## Features

1. **vLLM Integration**: Connects to local Qwen model server via OpenAI-compatible endpoint
2. **Dynamic MCP Tools**: LoadSet processing tools registered dynamically (no hardcoded tools)
3. **Comprehensive System Prompt**: Includes aerospace structural analysis guidance
4. **Flexible Usage**: Command-line or interactive mode

## Prerequisites

### 1. Install Dependencies

```bash
pip install pydantic-ai
```

### 2. Start vLLM Server

Start your local Qwen model server using vLLM:

```bash
# Example: Starting vLLM with Qwen model
vllm serve Qwen/Qwen3-30B-A3B-Thinking \
    --host 0.0.0.0 \
    --port 8000 \
    --enable-auto-tool-choice \
    --tool-call-parser hermes
```

**Note**: Make sure your vLLM server is running on `http://localhost:8000` (default) or specify a custom URL using `--vllm-url`.

### 3. LoadSet Library

Ensure the `loads` package is available from the parent directory. The script automatically adds the parent directory to the Python path.

## Usage

### Command-Line Mode

Pass your message as a command-line argument:

```bash
python standalone_eval.py "I need to process some loads for ANSYS analysis. The file is 03_A_new_loads.json in the current directory. Output directory: ./output. I do not have any previous loads to compare against."
```

### Interactive Mode

Run without arguments to enter interactive mode:

```bash
python standalone_eval.py
```

Then enter your message when prompted.

### Custom vLLM URL

If your vLLM server is running on a different host/port:

```bash
python standalone_eval.py "Your message" --vllm-url http://192.168.1.100:8000/v1
```

## Example Use Case

This script is designed to handle a single use case: processing new loads without comparison.

**Sample User Message:**
```
I need to process some loads for ANSYS analysis.
The file is 03_A_new_loads.json in the current directory.
Output directory: ./output
I do not have any previous loads to compare against.
```

**Expected Workflow:**
1. Load the JSON file
2. Apply 1.5 safety factor (if loads are limit loads)
3. Create envelope to reduce load cases
4. Export to ANSYS format files

## Architecture

### Self-Contained Design

Everything needed is in a single file:

- **LoadSetMCPProvider**: Embedded MCP provider with stateful operations
- **vLLM Model Creation**: OpenAI-compatible provider setup
- **System Prompt**: Comprehensive aerospace analysis guidance
- **Agent Factory**: Dynamic tool registration from provider methods
- **Main Execution**: Async runner with CLI interface

### Dynamic Tool Registration

Tools are registered dynamically from `LoadSetMCPProvider` methods:
- `load_from_json` - Load LoadSet from JSON
- `convert_units` - Convert force/moment units
- `scale_loads` - Scale loads by factor
- `export_to_ansys` - Export to ANSYS format
- `get_load_summary` - Get LoadSet summary
- `list_load_cases` - List all load cases
- `envelope_loadset` - Create envelope of extremes
- `get_point_extremes` - Get min/max for each point
- `load_second_loadset` - Load second LoadSet for comparison
- `compare_loadsets` - Compare two LoadSets
- `get_comparison_summary` - Get comparison summary
- `export_comparison_report` - Generate comparison report

No hardcoded tools - all registered from provider at runtime.

## Configuration

### Model Settings

Default vLLM configuration in `create_vllm_model()`:
- Model name: `Qwen/Qwen3-30B-A3B-Thinking`
- Base URL: `http://localhost:8000/v1`
- API key: `EMPTY` (for local servers)

Modify these in the function call or by editing the defaults.

### System Prompt

The comprehensive system prompt is defined in the `SYSTEM_PROMPT` constant. It includes:
- Aerospace structural analysis context
- Load processing procedures
- Unit conversion guidelines
- Safety factor requirements
- Envelope operation instructions

## Testing

Test the script with the included sample data:

```bash
# Create output directory
mkdir -p output

# Run the agent
python standalone_eval.py "Process loads from 03_A_new_loads.json, scale by 1.5, create envelope, and export to ./output"
```

## Troubleshooting

### vLLM Connection Issues

If you see connection errors:
1. Verify vLLM server is running: `curl http://localhost:8000/v1/models`
2. Check the port and host are correct
3. Use `--vllm-url` to specify custom endpoint

### Import Errors

If you see "No module named 'loads'":
1. Ensure you're running from the `standalone_eval` directory
2. Verify the parent directory contains the `loads` package
3. Check Python path includes parent directory

### Tool Call Errors

If tools fail to execute:
1. Check file paths are correct (relative to execution directory)
2. Ensure output directories exist
3. Verify JSON file format matches LoadSet schema

## Notes

- This script is designed for **single use case** evaluation (Activity 03A style)
- The user message is left to the **external client** - no predefined messages
- All MCP tools are **dynamically registered** - no hardcoded function decorators
- The system prompt remains **comprehensive and unchanged** from the original implementation
