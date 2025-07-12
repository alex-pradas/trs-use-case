# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Development Environment
- **Package management**: Use `uv` for all Python package management
- **Install dependencies**: `uv sync`
- **Add dependencies**: `uv add <package>` or `uv add --dev <package>` for dev dependencies
- **Always use uv to run python commands**: `uv run python`

### Testing
- **Run all tests**: `uv run pytest`
- **Run specific test file**: `uv run pytest tests/test_loadset_enhanced.py -v`
- **Run comparison tests**: `uv run pytest tests/test_loadset_comparison.py -v`
- **Run range chart tests**: `uv run pytest tests/test_range_charts.py -v`
- **Run specific test class**: `uv run pytest tests/test_loadset_enhanced.py::TestLoadSetReadJson -v`
- **Run specific test method**: `uv run pytest tests/test_loadset_enhanced.py::TestLoadSetConvertTo::test_convert_to_kN -v`
- **Run with coverage**: `uv run pytest --cov=tools --cov-report=html`
- **Generate visual charts**: `uv run pytest -m visuals -s`

### Verification
- **Verify setup**: `uv run python verify_setup.py`

## Architecture Overview

This is a **load-transform-export pipeline** for aerospace structural load data processing:

### Core Components
1. **`tools/loads.py`**: Main implementation containing Pydantic models:
   - `LoadSet`: Top-level container for load cases with units
   - `LoadCase`: Individual load case with point loads
   - `PointLoad`: Single point load with force/moment components
   - `ForceMoment`: Force (fx,fy,fz) and moment (mx,my,mz) values
   - `ComparisonRow`: Individual comparison result row
   - `LoadSetCompare`: Comparison results container with export functionality

2. **Data Flow**: Load JSON → Transform (convert units/scale) → Export ANSYS files → Compare LoadSets → Generate visualizations

### Key Features
- **Unit conversion**: Supports N, kN, lbf, klbf for forces; Nm, kNm, lbf-ft for moments
- **Scaling**: Factor-based scaling of all load values
- **ANSYS export**: Generates F-command format files for each load case
- **LoadSet comparison**: Compare two LoadSets with detailed min/max analysis
- **Range visualization**: Generate dual subplot bar charts (forces vs moments)
- **JSON export**: Export comparison results in structured JSON format
- **Immutable operations**: All transform methods return new instances

### Test Structure
Tests are organized into focused classes across multiple files:

#### Core LoadSet Tests (`tests/test_loadset_enhanced.py`):
- `TestLoadSetReadJson`: JSON loading and validation
- `TestLoadSetConvertTo`: Unit conversion testing
- `TestLoadSetFactor`: Load scaling functionality
- `TestLoadSetToAnsys`: ANSYS export validation

#### Comparison Tests (`tests/test_loadset_comparison.py`):
- `TestComparisonRow`: Individual comparison row functionality
- `TestLoadSetCompare`: Comparison result container and export
- `TestLoadSetPointExtremes`: Min/max value extraction
- `TestLoadSetComparison`: LoadSet comparison functionality
- `TestLoadSetComparisonWithRealData`: Integration tests with real data

#### Visualization Tests (`tests/test_range_charts.py`):
- `TestRangeChartGeneration`: Range chart generation functionality
- `TestRangeChartsWithRealData`: Tests with real data including visual generation (marked with `@pytest.mark.visuals`)

### Data Sources
- **`solution/loads/new_loads.json`**: Updated JSON load data files
- **`solution/loads/old_loads.json`**: Original load data files

## MCP Server Integration

This project includes a **FastMCP server** that exposes LoadSet operations as MCP tools for LLM agent access:

### MCP Server Commands
- **Start MCP server**: `uv run python tools/mcp_server.py`
- **Test MCP integration**: `uv run pytest tests/test_mcp_integration.py -v`
- **Test MCP server**: `uv run pytest tests/test_mcp_server.py -v`

### Available MCP Tools
- **`load_from_json`**: Load LoadSet from JSON file path
- **`convert_units`**: Convert units between N, kN, lbf, klbf  
- **`scale_loads`**: Scale all loads by a factor
- **`export_to_ansys`**: Export to ANSYS format files
- **`get_load_summary`**: Get summary information about current LoadSet
- **`list_load_cases`**: List all load cases in current LoadSet

### MCP Architecture
- **`tools/mcp_server.py`**: FastMCP server implementation with tool definitions
- **`tools/agent_client.py`**: Pydantic-AI agent client for testing MCP integration
- **Global state management**: Maintains current LoadSet across tool calls
- **Error handling**: Comprehensive error responses for all MCP operations

### Integration Testing
The MCP server is tested both directly and through a Pydantic-AI agent client:
- **Direct tool tests**: Unit tests for each MCP tool
- **Agent integration tests**: Tests using Pydantic-AI agent (requires `OPENAI_API_KEY`)
- **State management tests**: Verify LoadSet state persistence across operations

## Configuration Notes

- **Python version**: Requires Python ≥3.13
- **Test configuration**: Defined in `pyproject.toml` with verbose output, colored results, and short tracebacks
- **Visual tests**: Marked with `@pytest.mark.visuals` and skipped by default (use `pytest -m visuals` to run)
- **VS Code integration**: Configured with proper Python interpreter and test discovery settings
- **Dependencies**: Uses `matplotlib>=3.8.0` and `numpy>=1.24.0` for visualization, `fastmcp>=2.0.0` and `pydantic-ai>=0.3.6` for MCP
- **Visualization output**: Range charts saved to `tests/visual_range_charts/` when visual tests are run