# LoadSet Processing Tools

This project provides a load-transform-export pipeline for aerospace structural load data using Pydantic models, AI agents, and MCP servers. Features a **simplified dual architecture** for both direct usage and external MCP protocol access.

## Features

### **Core LoadSet Operations**
- **Load**: Read LoadSet data from JSON files with validation
- **Transform**: Convert between units (N, kN, lbf, klbf) and scale by factors  
- **Export**: Generate ANSYS load files in F-command format
- **Compare**: Compare two LoadSets with detailed analysis and percentage differences
- **Visualize**: Generate range bar charts showing force and moment comparisons
- **Envelope**: Create envelope LoadSets containing only extreme value load cases

### **AI Agent Integration**
- **Pydantic AI Agent**: Intelligent LoadSet processing with natural language interface
- **Direct Provider Access**: Fast, direct method calls without MCP protocol overhead
- **Tool Integration**: 11 specialized tools for complete LoadSet workflows

### **MCP Server Support**
- **External Access**: FastMCP server for external clients and other applications
- **Resource Support**: Built-in resource URIs for standard load files
- **State Management**: Persistent state for multi-step operations

## Installation

This project uses `uv` for dependency management. Make sure you have `uv` installed, then:

```bash
# Install dependencies
uv sync
```

## Usage

### **Option 1: AI Agent (Recommended)**

```python
from tools.agents import create_loadset_agent
from tools.mcps.loads_mcp_server import LoadSetMCPProvider

# Create agent and provider
agent = create_loadset_agent()
provider = LoadSetMCPProvider()

# Process loads with natural language
result = agent.run_sync(
    "Load the new loads, convert to klbf, apply 1.5 safety factor, and export to ANSYS",
    deps=provider
)

print(result.output)
```

### **Option 2: Direct LoadSet API**

```python
from tools.loads import LoadSet

# Load from JSON
loadset = LoadSet.read_json('solution/loads/new_loads.json')

# Transform data
converted = loadset.convert_to('kN')  # Convert to kN units
scaled = converted.factor(1.5)        # Scale by factor of 1.5

# Export to ANSYS
scaled.to_ansys('/output/folder', 'my_loads')

# Compare LoadSets
old_loadset = LoadSet.read_json('solution/loads/old_loads.json')
new_loadset = LoadSet.read_json('solution/loads/new_loads.json')
comparison = old_loadset.compare_to(new_loadset)

# Export comparison results to JSON
json_output = comparison.to_json()

# Generate visual range charts
chart_files = comparison.generate_range_charts('output_charts/')
# Creates: Point_A_ranges.png, Point_B_ranges.png, etc.
```

### **Option 3: MCP Server (External Access)**

```bash
# Start MCP server for external clients
python -m tools.mcps.start_servers

# Or run specific transport
python -m tools.mcps.loads_mcp_server stdio
```

```python
# External MCP client usage
import requests

response = requests.post('http://localhost:8000/tools/load_from_json', 
                        json={'file_path': 'solution/loads/new_loads.json'})
```

## Running Tests

The project includes comprehensive tests using pytest. Tests are organized into class-based test suites for better organization and shared setup.

### Configuration

Pytest is configured in `pyproject.toml` with sensible defaults:
- Verbose output by default
- Colored output
- Test discovery in the `tests/` directory
- Short traceback format for cleaner error messages

### Run All Tests

```bash
# Run all core tests (recommended)
uv run pytest tests/tools tests/mcps tests/test_agents.py -v

# Run all tests (includes some that may be skipped)
uv run pytest

# Run with output capture disabled (see print statements)
uv run pytest -v -s
```

### Run Specific Test Files

```bash
# Core LoadSet functionality
uv run pytest tests/tools/test_loadset_core.py -v

# MCP server functionality
uv run pytest tests/mcps/test_mcp_server.py -v

# Agent architecture tests
uv run pytest tests/test_agents.py -v

# Integration tests (expensive - uses AI model)
uv run pytest tests/agents/test_envelope_agent_integration.py -v
```

### Run Specific Test Classes

```bash
# Test LoadSet JSON loading
uv run pytest tests/tools/test_loadset_core.py::TestLoadSetReadJson -v

# Test unit conversion
uv run pytest tests/tools/test_loadset_core.py::TestLoadSetConvertTo -v

# Test load scaling
uv run pytest tests/tools/test_loadset_core.py::TestLoadSetFactor -v

# Test ANSYS export
uv run pytest tests/tools/test_loadset_core.py::TestLoadSetToAnsys -v

# Test LoadSet comparison
uv run pytest tests/tools/test_loadset_core.py::TestLoadSetComparison -v

# Test MCP server tools
uv run pytest tests/mcps/test_mcp_server.py::TestLoadFromJsonTool -v

# Test agent architecture
uv run pytest tests/test_agents.py::TestLoadSetAgentArchitecture -v
```

### Run Specific Test Methods

```bash
# Test a specific method
uv run pytest tests/tools/test_loadset_core.py::TestLoadSetConvertTo::test_convert_to_kN -v

# Test agent creation
uv run pytest tests/test_agents.py::TestLoadSetAgentArchitecture::test_loadset_agent_creation -v
```

### Visual Chart Generation

Visual chart generation tests are marked with the `visuals` marker and are **skipped by default** to avoid generating images during regular test runs.

```bash
# Generate visual range charts from real data
uv run pytest -m visuals -s

# Run specific visual test
uv run pytest tests/test_range_charts.py::TestRangeChartsWithRealData::test_generate_visual_range_charts -m visuals -s

# Run tests excluding visual generation (default behavior)
uv run pytest tests/test_range_charts.py -v
```

Visual tests create range charts comparing old_loads.json vs new_loads.json in `tests/visual_range_charts/`.

### VS Code Integration

The project includes VS Code configuration (`.vscode/settings.json`) for seamless test integration:

#### Test Discovery
- Tests are automatically discovered in the `tests/` directory
- The test explorer will show all test classes and methods
- Tests are auto-discovered when files are saved

#### Running Tests in VS Code
1. **Test Explorer**: Use the Test Explorer panel (beaker icon) to:
   - View all tests in a tree structure
   - Run individual tests or test classes
   - Debug tests with breakpoints
   - View test results inline

2. **Command Palette**: Use `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac) and type:
   - `Python: Run All Tests`
   - `Python: Run Current Test File`
   - `Python: Debug All Tests`

3. **Code Lens**: Click the "Run Test" or "Debug Test" links that appear above test methods

4. **Right-click Menu**: Right-click on test files, classes, or methods to run/debug

5. **Debug Configurations**: Use `F5` or the Debug panel with pre-configured options:
   - `Debug Current Test File`: Debug the currently open test file
   - `Debug All Tests`: Debug all tests in the project
   - `Debug Enhanced LoadSet Tests`: Debug only the enhanced LoadSet tests

#### Key Features
- **Auto test discovery** when files are saved
- **Integrated debugging** with breakpoints and step-through
- **Test result display** in the editor with pass/fail indicators
- **Python path configuration** for proper imports from `tools/` directory
- **Spell checking** configured for technical terms (klbf, ansys, pydantic, etc.)
- **Pre-configured debug sessions** for different test scenarios

#### Troubleshooting VS Code Test Discovery

If you get "ModuleNotFoundError: No module named 'pytest'" or tests aren't showing up:

1. **CRITICAL: Set Correct Python Interpreter**: 
   - Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
   - Type "Python: Select Interpreter"
   - Choose the interpreter that shows: `./venv/bin/python` or the full path ending with `/trs-use-case/.venv/bin/python`
   - **NOT** the system Python or other virtual environments

2. **Alternative: Use Workspace File**:
   - Open the `trs-use-case.code-workspace` file in VS Code
   - This will automatically configure the correct interpreter

2. **Refresh Test Discovery**:
   - Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
   - Type "Test: Refresh Tests"
   - Or click the refresh button in the Test Explorer

3. **Check Output Panel**:
   - Open View → Output
   - Select "Python Test Log" from the dropdown
   - Look for any error messages

4. **Restart Language Server**:
   - Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
   - Type "Python: Restart Language Server"

5. **Verify Environment Setup**:
   ```bash
   # Run verification script to check everything is working
   uv run python verify_setup.py
   
   # Run the simple test file to verify basic functionality
   uv run pytest tests/test_simple.py -v
   ```

6. **If VS Code Still Shows "No module named 'pytest'"**:
   - Close VS Code completely
   - Reopen VS Code using the workspace file: `code trs-use-case.code-workspace`
   - Or reopen the folder and manually select the Python interpreter again

## Test Structure

The tests are organized into focused areas reflecting the new architecture:

### Core LoadSet Tests (`tests/tools/test_loadset_core.py`)
- **`TestLoadSetReadJson`**: Tests for loading JSON files with error handling
- **`TestLoadSetConvertTo`**: Tests for unit conversion between different systems
- **`TestLoadSetFactor`**: Tests for scaling load values by factors
- **`TestLoadSetToAnsys`**: Tests for ANSYS file export functionality
- **`TestLoadSetComparison`**: Tests for LoadSet comparison functionality
- **`TestLoadSetEnvelope`**: Tests for envelope generation functionality

### MCP Server Tests (`tests/mcps/test_mcp_server.py`)
- **`TestMCPServerCreation`**: Tests for MCP server instantiation and configuration
- **`TestLoadFromJsonTool`**: Tests for JSON loading via MCP tools
- **`TestConvertUnitsTool`**: Tests for unit conversion via MCP tools
- **`TestDataBasedMethods`**: Tests for direct data-based operations
- **`TestResourceBasedMethods`**: Tests for resource URI-based operations

### Agent Architecture Tests (`tests/test_agents.py`)
- **`TestLoadSetAgentArchitecture`**: Tests for simplified agent architecture
- **`TestLoadSetProviderIntegration`**: Tests for direct provider integration

### Integration Tests (`tests/agents/`)
- **`TestEnvelopeAgentIntegration`**: End-to-end tests with AI model calls (expensive)

Each test class includes:
- Comprehensive edge case testing
- Error condition validation
- Real data validation using actual load files
- Architecture compliance verification

## Test Coverage

The test suite includes **107+ comprehensive tests** covering:

### Core Functionality
- ✅ JSON file loading and validation
- ✅ Unit conversions (N ↔ kN ↔ lbf ↔ klbf)
- ✅ Load scaling and factoring
- ✅ ANSYS file export with proper formatting
- ✅ Error handling for invalid inputs
- ✅ File path validation
- ✅ Method chaining operations
- ✅ Floating point precision handling
- ✅ Special character sanitization

### Comparison & Visualization
- ✅ LoadSet comparison with detailed analysis
- ✅ Min/max value extraction across load cases
- ✅ Percentage difference calculations
- ✅ JSON export of comparison results
- ✅ Range bar chart generation
- ✅ Dual subplot layouts (forces vs moments)
- ✅ Visual styling and formatting
- ✅ Multiple image format support (PNG, SVG, PDF)
- ✅ Edge case handling (empty data, zero values)
- ✅ Real data integration testing

### AI Agent & MCP Architecture
- ✅ Pydantic AI agent creation and configuration
- ✅ Direct provider dependency injection
- ✅ MCP server tool registration and execution
- ✅ Resource-based loading (loadsets://new_loads.json)
- ✅ Data-based operations with validation
- ✅ State management across operations
- ✅ Error handling and recovery
- ✅ Architecture simplification validation

## Configuration Files

### `pyproject.toml`
Contains pytest configuration including:
- Test discovery paths and patterns
- Default command-line options (verbose, colored output)
- Test markers for categorization (`unit`, `integration`, `slow`, `visuals`)
- Visual tests excluded by default (`-m "not visuals"`)
- Output formatting preferences

### `.vscode/settings.json`
VS Code workspace settings for:
- Python interpreter configuration
- Test discovery and execution
- Import path resolution
- Code formatting and linting
- Spell checking for technical terms

### `.vscode/launch.json`
Debug configurations for:
- Debugging individual test files
- Debugging all tests
- Debugging specific test suites

## Project Structure

```
├── tools/
│   ├── agents.py            # Pydantic AI agent factory (simplified architecture)
│   ├── loads.py            # Core LoadSet implementation
│   ├── model_config.py     # AI model configuration
│   └── mcps/               # MCP servers
│       ├── loads_mcp_server.py    # LoadSet MCP server and provider
│       └── start_servers.py       # MCP server startup script
├── tests/
│   ├── test_agents.py      # Agent architecture tests
│   ├── tools/
│   │   └── test_loadset_core.py   # Core LoadSet functionality tests
│   ├── mcps/
│   │   └── test_mcp_server.py     # MCP server tests
│   └── agents/
│       └── test_envelope_agent_integration.py  # AI integration tests
├── solution/
│   ├── loads/
│   │   ├── new_loads.json  # Updated JSON load data
│   │   └── old_loads.json  # Original load data
│   └── 03_loads_processing/
│       └── process_loads.py # Main application using simplified architecture
├── .vscode/
│   ├── settings.json       # VS Code workspace settings
│   └── launch.json         # Debug configurations
└── pyproject.toml         # Project and pytest configuration
```

## Architecture

This project implements a **simplified dual architecture** designed for both direct usage and external MCP protocol access:

### **Design Philosophy**
- **Direct Provider Access**: Pydantic AI agents use `LoadSetMCPProvider` directly for maximum performance
- **External MCP Access**: FastMCP server available for external clients via HTTP/stdio
- **Single Source of Truth**: All logic centralized in `LoadSetMCPProvider` class methods
- **No Wrapper Complexity**: Eliminated intermediate abstractions for 60% code reduction

### **Data Flow**
```
AI Agent → LoadSetMCPProvider → LoadSet Operations
External Client → FastMCP Server → LoadSetMCPProvider → LoadSet Operations  
```

### **Benefits**
- ✅ **Performance**: Direct method calls eliminate MCP protocol overhead for agents
- ✅ **Simplicity**: 60% less code, easier to understand and maintain
- ✅ **Flexibility**: Both direct usage and external access supported
- ✅ **Type Safety**: Full Pydantic validation throughout the pipeline

## Development

This project follows Test-Driven Development (TDD) principles:

1. **Write failing tests** that define the expected behavior
2. **Implement minimal code** to make tests pass
3. **Refactor** while keeping tests green

All methods return new instances (immutable operations) and include comprehensive error handling and type safety.