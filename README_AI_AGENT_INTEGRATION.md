# AI Agent Integration with MCP Server

This document describes the AI agent integration test that validates an AI agent can successfully interact with the MCP server to process structural load data.

## Overview

The integration demonstrates how an AI agent powered by Anthropic's Claude model can:
1. Load structural load data from JSON files
2. Apply scaling transformations 
3. Convert units between different systems
4. Export processed data to ANSYS format files

## Implementation

### Files Created

1. **`tests/test_ai_agent_integration.py`** - Main test file with comprehensive test suite
2. **`demo_ai_agent.py`** - Standalone demo script showing the integration in action

### Key Features

- **Real AI Agent**: Uses Anthropic's Claude model via pydantic-ai (no mocking)
- **Environment Variables**: Loads API key from `.env` file using `python-dotenv`
- **Tool Registration**: Uses `@agent.tool_plain` decorator for context-free tools
- **Complete Workflow**: Implements the exact user scenario requested
- **File Validation**: Comprehensive validation of generated ANSYS files

## Test Suite

### `TestAnthropicAgentIntegration`

- **`test_anthropic_agent_full_workflow`**: Complete AI agent workflow test
- **`test_anthropic_agent_error_handling`**: Error handling validation
- **`test_direct_tool_calls`**: Direct MCP tool calls (fallback test)
- **`test_output_validation`**: ANSYS file validation
- **`test_get_available_tools`**: Tool discovery test

## Usage

### Running Tests

```bash
# Run all integration tests
uv run pytest tests/test_ai_agent_integration.py -v

# Run specific test
uv run pytest tests/test_ai_agent_integration.py::TestAnthropicAgentIntegration::test_anthropic_agent_full_workflow -v
```

### Running Demo

```bash
# Run the standalone demo
uv run python demo_ai_agent.py
```

## User Prompt Scenario

The exact user prompt tested:
```
"Please help me process the loads in solution/loads/new_loads.json. 
Factor by 1.5 and convert to klbs. Generate files for ansys in a subfolder called output."
```

### Expected Workflow

1. **Load Data**: Read JSON file with 25 load cases
2. **Scale Loads**: Apply 1.5x scaling factor to all forces and moments
3. **Convert Units**: Convert from N/Nm to klbf/lbf-ft
4. **Export Files**: Generate 25 ANSYS `.inp` files in `output/` folder

## Technical Details

### Dependencies

- `pydantic-ai` - AI agent framework
- `python-dotenv` - Environment variable loading
- `pytest-asyncio` - Async test support

### MCP Tools Used

- `load_from_json` - Load LoadSet from JSON file
- `scale_loads` - Scale loads by factor
- `convert_units` - Convert between unit systems
- `export_to_ansys` - Export to ANSYS format
- `get_load_summary` - Get LoadSet summary
- `list_load_cases` - List all load cases

### Tool Registration

Tools are registered using `@agent.tool_plain` decorator:

```python
@self.agent.tool_plain
def load_from_json(file_path: str) -> dict:
    """Load a LoadSet from a JSON file."""
    return self.call_tool_directly("load_from_json", file_path=file_path)["tool_result"]
```

## Validation

### File Validation

- **Count**: Validates 25 ANSYS files are generated
- **Extension**: Ensures `.inp` file extension
- **Content**: Verifies ANSYS command format (`f,all,fx,` etc.)
- **Units**: Confirms proper unit conversion (N → klbf)

### Numerical Verification

- **Scaling**: Validates 1.5x factor applied correctly
- **Unit Conversion**: Confirms N to klbf conversion (factor: 4448.222)
- **File Content**: Checks ANSYS command structure

## Environment Setup

### Required Environment Variables

```bash
# .env file
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### Dependencies Installation

```bash
uv add python-dotenv
uv add --dev pytest-asyncio
```

## Results

✅ **All tests pass**
- Complete AI agent workflow ✅
- Error handling ✅  
- Direct tool calls ✅
- Output validation ✅
- Tool discovery ✅

The integration successfully demonstrates that an AI agent can:
- Process natural language requests
- Execute complex multi-step workflows
- Interact with MCP server tools
- Generate validated engineering outputs

## Example Output

```
🤖 AI Agent Integration Demo
==================================================
📝 User prompt: Please help me process the loads in solution/loads/new_loads.json. 
Factor by 1.5 and convert to klbs. Generate files for ansys in a subfolder called output.

✅ SUCCESS!
🤖 Agent response: All operations completed successfully:
1. Loaded 25 load cases from JSON file
2. Scaled loads by factor 1.5
3. Converted units from N to klbf
4. Exported files to output folder

📊 Generated 25 ANSYS files:
  - new_loads_landing_017.inp
  - new_loads_landing_016.inp
  - ... and 23 more files
```

This integration provides a complete example of how AI agents can be used to automate complex engineering workflows through MCP server interfaces.