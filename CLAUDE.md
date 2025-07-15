# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Development Environment
- **Package management**: Use `uv` for all Python package management
- **Install dependencies**: `uv sync`
- **Add dependencies**: `uv add <package>` or `uv add --dev <package>` for dev dependencies
- **Always use uv to run python commands**: `uv run python`

### Testing
- **Run all tests (excluding expensive LLM tests)**: `uv run pytest`
- **Run expensive LLM/AI tests**: `uv run pytest -m expensive`
- **Run all tests including expensive ones**: `uv run pytest -m "not expensive or expensive"`
- **Generate visual charts**: `uv run pytest -m visuals -s`
- **Run with coverage**: `uv run pytest --cov=tools --cov-report=html`

#### Test Category Commands
- **Core implementation tests**: `uv run pytest tests/tools/ -v`
- **MCP server tests**: `uv run pytest tests/mcps/ -v`
- **Agent integration tests**: `uv run pytest tests/agents/ -v`

#### Specific Test Files
- **Core LoadSet tests**: `uv run pytest tests/tools/test_loadset_enhanced.py -v`
- **LoadSet comparison tests**: `uv run pytest tests/tools/test_loadset_comparison.py -v`
- **Range chart tests**: `uv run pytest tests/tools/test_range_charts.py -v`
- **LoadSet MCP server tests**: `uv run pytest tests/mcps/test_mcp_server.py -v`
- **Python execution MCP tests**: `uv run pytest tests/mcps/test_python_exec_mcp_server.py -v`
- **Script execution MCP tests**: `uv run pytest tests/mcps/test_script_exec_mcp_server.py -v`
- **Agent integration tests**: `uv run pytest tests/agents/test_ai_agent_integration.py -v`
- **Python execution agent tests**: `uv run pytest tests/agents/test_python_exec_agent_integration.py -v`
- **Script generation agent tests**: `uv run pytest tests/agents/test_script_agent_integration.py -v`
- **Simplified architecture TDD tests**: `uv run pytest tests/test_simplified_agents_tdd.py -v`

#### Specific Test Classes and Methods
- **Run specific test class**: `uv run pytest tests/tools/test_loadset_enhanced.py::TestLoadSetReadJson -v`
- **Run specific test method**: `uv run pytest tests/tools/test_loadset_enhanced.py::TestLoadSetConvertTo::test_convert_to_kN -v`

#### Test Categories
- **Core tests (57)**: Fast unit and integration tests for LoadSet functionality in `tests/tools/`
- **MCP tests (80)**: Mock MCP server tests for tool functionality in `tests/mcps/`
- **Agent tests (30)**: Expensive LLM/AI agent tests requiring API keys in `tests/agents/` - run explicitly with `-m expensive`
- **Visual tests (1)**: Chart generation tests in `tests/agents/` - run explicitly with `-m visuals`
- **Simplified architecture tests (19)**: TDD tests for new simplified agent architecture
- **Total fast tests (156)**: Core + MCP + TDD tests that run by default
- **Total tests (187)**: All tests including expensive and visual tests

### Verification
- **Verify setup**: `uv run python verify_setup.py`

## Simplified Agent Architecture (Recommended)

This project now uses a **simplified pydantic-ai architecture** that achieves a **57.2% code reduction** while following best practices and maintaining full functionality.

### Model Selection
Set a single environment variable to choose your AI model:
```bash
# Use Anthropic Claude (default)
export AI_MODEL="anthropic:claude-3-5-sonnet-latest"

# Use FIREWORKS AI
export AI_MODEL="fireworks:accounts/fireworks/models/llama-v3p3-70b-instruct"

# Use OpenAI
export AI_MODEL="openai:gpt-4o"

# Use Google Gemini
export AI_MODEL="google-gla:gemini-1.5-flash"
```

### Simple Agent Usage
```python
from tools.agents_v2 import create_loadset_agent, create_python_agent, create_script_agent
from tools.dependencies import MCPServerProvider

# Create agent and dependencies once
agent = create_loadset_agent()
deps = MCPServerProvider()

# LoadSet processing with dependency injection
result = await agent.run(
    "Load solution/loads/new_loads.json, convert to kN, scale by 1.5, export to ANSYS",
    deps=deps
)

# Python code execution
python_agent = create_python_agent()
result = await python_agent.run(
    "Load a LoadSet and calculate the maximum force component",
    deps=deps
)

# Script generation and execution
script_agent = create_script_agent()
result = await script_agent.run(
    "Generate a script to analyze LoadSet data and create a summary report",
    deps=deps
)
```

### Testing the Simplified Architecture
- **Test TDD implementation**: `uv run pytest tests/test_simplified_agents_tdd.py -v`
- **Compare architectures**: `uv run python test_simplified_vs_original.py`
- **All fast tests**: `uv run pytest tests/tools/ tests/mcps/ -v`

### Benefits
- **57.2% code reduction**: From 400+ lines to 171 lines
- **Type-safe responses**: Pydantic models instead of raw dictionaries
- **True dependency injection**: Using RunContext for MCP server access
- **Centralized error handling**: No manual try-catch in tools
- **Follows pydantic-ai best practices**: Direct patterns from documentation
- **Zero abstraction overhead**: Direct MCP server access

### Architecture Documentation
See `SIMPLIFIED_ARCHITECTURE_GUIDE.md` for comprehensive documentation, migration guide, and best practices.

## FIREWORKS AI Integration (Legacy)

This project supports FIREWORKS AI as an alternative to Anthropic Claude models using pydantic-ai.

### Configuration
1. **Get FIREWORKS API Key**: Sign up at [fireworks.ai](https://fireworks.ai) and get your API key
2. **Add to environment**: Add `FIREWORKS_API_KEY=your-key-here` to your `.env` file
3. **Verify configuration**: `uv run python tools/fireworks_client.py`

### Available Models
- **Llama 3.3 70B Instruct**: Latest model with improved coding capabilities (default)
- **Llama 3.1 70B Instruct**: Enhanced reasoning and long context support

### Testing FIREWORKS Integration
- **Basic integration test**: `uv run python test_fireworks_integration.py`
- **MCP server integration**: `uv run python test_fireworks_mcp_integration.py`

### Using FIREWORKS with MCP Agents
```python
from tools.fireworks_mcp_agent import FireworksMCPAgent
from tools.mcps.loads_mcp_server import create_mcp_server

# Create MCP server and FIREWORKS agent
server = create_mcp_server()
agent = FireworksMCPAgent(server)

# Process LoadSet operations
result = await agent.process_user_prompt(
    "Load 'solution/loads/new_loads.json' and convert to kN units"
)
```

### FIREWORKS vs Anthropic
- **Performance**: FIREWORKS offers faster inference with competitive quality
- **Cost**: Generally more cost-effective than Anthropic
- **Models**: Specialized in open-source models (Llama series)
- **Compatibility**: Drop-in replacement for Anthropic agents in most workflows

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
Tests are organized into three main categories for better organization and performance:

#### **Core Implementation Tests (`tests/tools/`)**
Fast unit and integration tests for core functionality (no LLM calls, no expensive operations):
- **`test_loadset_enhanced.py`**: Core LoadSet objects, JSON loading, unit conversion, scaling, ANSYS export
  - `TestLoadSetReadJson`: JSON loading and validation
  - `TestLoadSetConvertTo`: Unit conversion testing
  - `TestLoadSetFactor`: Load scaling functionality  
  - `TestLoadSetToAnsys`: ANSYS export validation
- **`test_loadset_comparison.py`**: LoadSet comparison algorithms and data structures
  - `TestComparisonRow`: Individual comparison row functionality
  - `TestLoadSetCompare`: Comparison result container and export
  - `TestLoadSetPointExtremes`: Min/max value extraction
  - `TestLoadSetComparison`: LoadSet comparison functionality
  - `TestLoadSetComparisonWithRealData`: Integration tests with real data
- **`test_range_charts.py`**: Chart generation logic (fast tests only)
  - `TestRangeChartGeneration`: Range chart generation functionality
  - `TestRangeChartsWithRealData`: Tests with real data (non-visual tests)

#### **MCP Server Tests (`tests/mcps/`)**
Tests that mock MCP servers and test their tool interactions (no real LLM agents):
- **`test_mcp_server.py`**: LoadSet MCP server tools testing
- **`test_mcp_server_comparison.py`**: Comparison-specific MCP tools
- **`test_python_exec_mcp_server.py`**: Python execution MCP server tools
- **`test_script_exec_mcp_server.py`**: Script execution MCP server tools

#### **Agent Integration Tests (`tests/agents/`)**
Expensive tests using real LLM calls and complete workflows (all `@pytest.mark.expensive`):
- **`test_ai_agent_integration.py`**: Basic agent integration with LoadSet MCP
- **`test_anthropic_mcp_integration.py`**: stdio transport agent tests  
- **`test_anthropic_mcp_http_integration.py`**: HTTP transport agent tests
- **`test_python_exec_agent_integration.py`**: Python execution agent workflows
- **`test_script_agent_integration.py`**: Script generation agent workflows
- **`test_range_charts_visual.py`**: Visual chart generation test (marked with `@pytest.mark.visuals`)

### Data Sources
- **`solution/loads/new_loads.json`**: Updated JSON load data files
- **`solution/loads/old_loads.json`**: Original load data files

## MCP Server Integration

This project includes **three FastMCP servers** that expose different capabilities as MCP tools for LLM agent access:

### MCP Server Commands

#### Unified Server Management (Recommended)
- **Start all MCP servers**: `uv run python tools/mcps/start_servers.py` (starts all servers on ports 8000-8002)
- **Start specific servers**: `uv run python tools/mcps/start_servers.py --only loads,python`
- **Start with stdio transport**: `uv run python tools/mcps/start_servers.py --transport stdio`
- **Get help**: `uv run python tools/mcps/start_servers.py --help`

#### Individual Server Management
- **Start LoadSet MCP server**: `uv run python tools/mcps/loads_mcp_server.py` (defaults to HTTP transport, port 8000)
- **Start Python execution MCP server**: `uv run python tools/mcps/python_exec_mcp_server.py` (defaults to HTTP transport, port 8001)
- **Start Script execution MCP server**: `uv run python tools/mcps/script_exec_mcp_server.py` (defaults to HTTP transport, port 8002)
- **Start with specific transport**: `uv run python tools/mcps/loads_mcp_server.py http` or `uv run python tools/mcps/loads_mcp_server.py stdio`

#### Server Configuration
- **LoadSet MCP Server (`loads`)**: Port 8000 - LoadSet operations and comparisons
- **Python Execution MCP Server (`python`)**: Port 8001 - Python code execution with persistent sessions  
- **Script Execution MCP Server (`script`)**: Port 8002 - Python script execution with workspace management

#### Testing Commands
- **Test MCP integration**: `uv run pytest tests/test_anthropic_mcp_integration.py -v`
- **Test LoadSet MCP server**: `uv run pytest tests/test_mcp_server.py -v`
- **Test Python execution MCP server**: `uv run pytest tests/test_python_exec_mcp_server.py -v`
- **Test Python execution agent integration**: `uv run pytest tests/test_python_exec_agent_integration.py -v`
- **Test Script execution MCP server**: `uv run pytest tests/test_script_exec_mcp_server.py -v`
- **Test Script generation agent integration**: `uv run pytest tests/test_script_agent_integration.py -v`

### Available MCP Tools

#### LoadSet MCP Server (`tools/mcps/loads_mcp_server.py`)
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

#### Python Execution MCP Server (`tools/mcps/python_exec_mcp_server.py`)
- **`execute_code`**: Execute Python code in persistent IPython session
- **`list_variables`**: List all variables in current session namespace
- **`get_variable`**: Get detailed information about specific variable
- **`reset_session`**: Clear all variables and reset execution environment
- **`install_package`**: Install Python packages using uv
- **`get_execution_history`**: Get recent code execution history
- **`configure_security`**: Configure security settings for code execution

#### Script Execution MCP Server (`tools/mcps/script_exec_mcp_server.py`)
- **`execute_python_script`**: Execute complete Python scripts in isolated workspace
- **`list_output_files`**: List all files created during script execution
- **`download_file`**: Download files from workspace as base64 or text
- **`upload_file`**: Upload files to workspace before script execution
- **`get_execution_result`**: Get detailed execution results (stdout, stderr, timing)
- **`reset_workspace`**: Clean up execution workspace
- **`get_workspace_info`**: Get information about current workspace

### MCP Architecture

#### LoadSet MCP Server
- **`tools/mcps/loads_mcp_server.py`**: FastMCP server implementation with LoadSet tool definitions
- **`tools/agent_client.py`**: Pydantic-AI agent client for testing MCP integration
- **Class-based state management**: `LoadSetMCPProvider` encapsulates state across tool calls
- **HTTP transport**: Uses modern HTTP transport (default) with fallback to stdio
- **Error handling**: Comprehensive error responses for all MCP operations

#### Python Execution MCP Server
- **`tools/mcps/python_exec_mcp_server.py`**: FastMCP server with persistent IPython execution
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