# LoadSet Processing Tools

This project provides a load-transform-export pipeline for aerospace structural load data using Pydantic models and comprehensive testing.

## Features

- **Load**: Read LoadSet data from JSON files with validation
- **Transform**: Convert between units (N, kN, lbf, klbf) and scale by factors  
- **Export**: Generate ANSYS load files in F-command format
- **Compare**: Compare two LoadSets with detailed analysis and percentage differences
- **Visualize**: Generate range bar charts showing force and moment comparisons

## Installation

This project uses `uv` for dependency management. Make sure you have `uv` installed, then:

```bash
# Install dependencies
uv sync
```

## Usage

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
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run with output capture disabled (see print statements)
uv run pytest -v -s
```

### Run Specific Test Files

```bash
# Run only the enhanced LoadSet tests
uv run pytest tests/test_loadset_enhanced.py -v

# Run LoadSet comparison tests
uv run pytest tests/test_loadset_comparison.py -v

# Run range chart tests (excluding visual generation)
uv run pytest tests/test_range_charts.py -v

# Run only the original loads tests
uv run pytest tests/test_loads.py -v
```

### Run Specific Test Classes

```bash
# Test only the read_json functionality
uv run pytest tests/test_loadset_enhanced.py::TestLoadSetReadJson -v

# Test only unit conversion
uv run pytest tests/test_loadset_enhanced.py::TestLoadSetConvertTo -v

# Test only scaling functionality
uv run pytest tests/test_loadset_enhanced.py::TestLoadSetFactor -v

# Test only ANSYS export
uv run pytest tests/test_loadset_enhanced.py::TestLoadSetToAnsys -v

# Test LoadSet comparison functionality
uv run pytest tests/test_loadset_comparison.py::TestLoadSetComparison -v

# Test range chart generation
uv run pytest tests/test_range_charts.py::TestRangeChartGeneration -v
```

### Run Specific Test Methods

```bash
# Test a specific method
uv run pytest tests/test_loadset_enhanced.py::TestLoadSetConvertTo::test_convert_to_kN -v
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

The tests are organized into focused test classes across multiple files:

### Core LoadSet Tests (`test_loadset_enhanced.py`)
- **`TestLoadSetReadJson`**: Tests for loading JSON files with error handling
- **`TestLoadSetConvertTo`**: Tests for unit conversion between different systems
- **`TestLoadSetFactor`**: Tests for scaling load values by factors
- **`TestLoadSetToAnsys`**: Tests for ANSYS file export functionality

### Comparison Tests (`test_loadset_comparison.py`)
- **`TestComparisonRow`**: Tests for individual comparison row functionality
- **`TestLoadSetCompare`**: Tests for comparison result container and export
- **`TestLoadSetPointExtremes`**: Tests for min/max value extraction
- **`TestLoadSetComparison`**: Tests for LoadSet comparison functionality
- **`TestLoadSetComparisonWithRealData`**: Integration tests with real data

### Visualization Tests (`test_range_charts.py`)
- **`TestRangeChartGeneration`**: Tests for range chart generation functionality
- **`TestRangeChartsWithRealData`**: Tests with real data including visual generation

Each test class includes:
- Comprehensive edge case testing
- Error condition validation
- Real data validation using actual load files
- Method chaining verification

## Test Coverage

The test suite includes **55+ comprehensive tests** covering:

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
│   └── loads.py              # Main LoadSet implementation with comparison
├── tests/
│   ├── test_loads.py         # Original load file tests
│   ├── test_loadset_enhanced.py  # Enhanced LoadSet tests
│   ├── test_loadset_comparison.py  # LoadSet comparison tests
│   ├── test_range_charts.py  # Range chart visualization tests
│   └── visual_range_charts/  # Generated visual charts (created by tests)
├── solution/
│   └── loads/
│       ├── new_loads.json   # Updated JSON load data
│       └── old_loads.json   # Original load data
├── .vscode/
│   ├── settings.json         # VS Code workspace settings
│   └── launch.json           # Debug configurations
└── pyproject.toml           # Project and pytest configuration
```

## Development

This project follows Test-Driven Development (TDD) principles:

1. **Write failing tests** that define the expected behavior
2. **Implement minimal code** to make tests pass
3. **Refactor** while keeping tests green

All methods return new instances (immutable operations) and include comprehensive error handling and type safety.