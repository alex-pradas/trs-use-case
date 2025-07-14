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
- **Run Python execution MCP tests**: `uv run pytest tests/test_python_exec_mcp_server.py -v`
- **Run Python execution agent integration tests**: `uv run pytest tests/test_python_exec_agent_integration.py -v`
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

This project includes **three FastMCP servers** that expose different capabilities as MCP tools for LLM agent access:

### MCP Server Commands
- **Start LoadSet MCP server**: `uv run python tools/mcp_server.py` (defaults to HTTP transport)
- **Start Python execution MCP server**: `uv run python tools/python_exec_mcp_server.py` (defaults to HTTP transport)
- **Start Script execution MCP server**: `uv run python tools/script_exec_mcp_server.py` (defaults to HTTP transport, port 8002)
- **Start with specific transport**: `uv run python tools/mcp_server.py http` or `uv run python tools/mcp_server.py stdio`
- **Test MCP integration**: `uv run pytest tests/test_anthropic_mcp_integration.py -v`
- **Test LoadSet MCP server**: `uv run pytest tests/test_mcp_server.py -v`
- **Test Python execution MCP server**: `uv run pytest tests/test_python_exec_mcp_server.py -v`
- **Test Python execution agent integration**: `uv run pytest tests/test_python_exec_agent_integration.py -v`
- **Test Script execution MCP server**: `uv run pytest tests/test_script_exec_mcp_server.py -v`
- **Test Script generation agent integration**: `uv run pytest tests/test_script_agent_integration.py -v`

### Available MCP Tools

#### LoadSet MCP Server (`tools/mcp_server.py`)
- **`load_from_json`**: Load LoadSet from JSON file path
- **`convert_units`**: Convert units between N, kN, lbf, klbf  
- **`scale_loads`**: Scale all loads by a factor
- **`export_to_ansys`**: Export to ANSYS format files
- **`get_load_summary`**: Get summary information about current LoadSet
- **`list_load_cases`**: List all load cases in current LoadSet
- **`load_second_loadset`**: Load second LoadSet for comparison
- **`compare_loadsets`**: Compare two LoadSets with detailed analysis
- **`generate_comparison_charts`**: Generate range bar charts as base64 or files
- **`export_comparison_json`**: Export comparison results to JSON
- **`get_comparison_summary`**: Get high-level comparison statistics

#### Python Execution MCP Server (`tools/python_exec_mcp_server.py`)
- **`execute_code`**: Execute Python code in persistent IPython session
- **`list_variables`**: List all variables in current session namespace
- **`get_variable`**: Get detailed information about specific variable
- **`reset_session`**: Clear all variables and reset execution environment
- **`install_package`**: Install Python packages using uv
- **`get_execution_history`**: Get recent code execution history
- **`configure_security`**: Configure security settings for code execution

#### Script Execution MCP Server (`tools/script_exec_mcp_server.py`)
- **`execute_python_script`**: Execute complete Python scripts in isolated workspace
- **`list_output_files`**: List all files created during script execution
- **`download_file`**: Download files from workspace as base64 or text
- **`upload_file`**: Upload files to workspace before script execution
- **`get_execution_result`**: Get detailed execution results (stdout, stderr, timing)
- **`reset_workspace`**: Clean up execution workspace
- **`get_workspace_info`**: Get information about current workspace

### MCP Architecture

#### LoadSet MCP Server
- **`tools/mcp_server.py`**: FastMCP server implementation with LoadSet tool definitions
- **`tools/agent_client.py`**: Pydantic-AI agent client for testing MCP integration
- **Class-based state management**: `LoadSetMCPProvider` encapsulates state across tool calls
- **HTTP transport**: Uses modern HTTP transport (default) with fallback to stdio
- **Error handling**: Comprehensive error responses for all MCP operations

#### Python Execution MCP Server
- **`tools/python_exec_mcp_server.py`**: FastMCP server with persistent IPython execution
- **IPython integration**: Uses IPython kernel for advanced Python execution capabilities
- **Persistent sessions**: Variables and imports persist across multiple code executions
- **Rich output capture**: Handles matplotlib plots, pandas DataFrames, numpy arrays
- **Security features**: Optional filtering of dangerous imports and operations
- **Package management**: Integrated with project's uv workflow

### Integration Testing
All three MCP servers are comprehensively tested:

#### LoadSet MCP Server Testing
- **Direct tool tests**: Unit tests for each LoadSet MCP tool
- **Agent integration tests**: Tests using Pydantic-AI agent (requires `ANTHROPIC_API_KEY`)
- **HTTP transport tests**: Verify HTTP transport functionality with real agents
- **State management tests**: Verify LoadSet state persistence across operations

#### Python Execution MCP Server Testing
- **Execution tests**: Test code execution with persistent sessions
- **Security tests**: Verify dangerous code filtering and safety features
- **Output capture tests**: Test matplotlib plot capture and rich data serialization
- **Session management tests**: Test variable persistence, reset, and history tracking
- **Integration tests**: Test LoadSet class availability and project integration
- **Agent integration tests**: Test AI agent's ability to autonomously generate and execute Python code
  - Agents can solve programming challenges (factorial, fibonacci calculations)
  - Agents demonstrate iterative development with persistent variables
  - Agents can perform data analysis with numpy and matplotlib
  - Agents handle errors and debug code autonomously
  - Agents can access and work with project-specific LoadSet functionality

#### Script Execution MCP Server Testing
- **Direct tool tests**: Unit tests for script execution, workspace management, file I/O
- **LoadSet integration tests**: Test LoadSet classes availability and functionality in scripts
- **File transfer tests**: Test upload/download of files with base64 and text encoding
- **Workspace management tests**: Test isolated workspace creation and cleanup
- **Agent integration tests**: Test AI agent's ability to generate and execute complete scripts
  - Agent generates Python scripts from natural language instructions
  - Agent handles LoadSet processing workflows (load, convert, scale, export)
  - Agent performs unit conversion analysis across multiple unit systems
  - Agent executes LoadSet comparison workflows with real aerospace data
  - Agent exports to ANSYS format and manages output files
  - Agent downloads and saves output files to local filesystem
  - Agent handles errors and debugging of generated scripts

## Configuration Notes

- **Python version**: Requires Python ≥3.13
- **Test configuration**: Defined in `pyproject.toml` with verbose output, colored results, and short tracebacks
- **Visual tests**: Marked with `@pytest.mark.visuals` and skipped by default (use `pytest -m visuals` to run)
- **VS Code integration**: Configured with proper Python interpreter and test discovery settings
- **Dependencies**: Uses `matplotlib>=3.8.0` and `numpy>=1.24.0` for visualization, `fastmcp>=2.0.0` and `pydantic-ai>=0.3.6` for MCP, `ipython>=9.4.0` for Python execution server
- **Visualization output**: Range charts saved to `tests/visual_range_charts/` when visual tests are run