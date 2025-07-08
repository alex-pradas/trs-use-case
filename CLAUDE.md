# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Development Environment
- **Package management**: Use `uv` for all Python package management
- **Install dependencies**: `uv sync`
- **Add dependencies**: `uv add <package>` or `uv add --dev <package>` for dev dependencies

### Testing
- **Run all tests**: `uv run pytest`
- **Run specific test file**: `uv run pytest tests/test_loadset_enhanced.py -v`
- **Run specific test class**: `uv run pytest tests/test_loadset_enhanced.py::TestLoadSetReadJson -v`
- **Run specific test method**: `uv run pytest tests/test_loadset_enhanced.py::TestLoadSetConvertTo::test_convert_to_kN -v`
- **Run with coverage**: `uv run pytest --cov=tools --cov-report=html`

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

2. **Data Flow**: Load JSON → Transform (convert units/scale) → Export ANSYS files

### Key Features
- **Unit conversion**: Supports N, kN, lbf, klbf for forces; Nm, kNm, lbf-ft for moments
- **Scaling**: Factor-based scaling of all load values
- **ANSYS export**: Generates F-command format files for each load case
- **Immutable operations**: All transform methods return new instances

### Test Structure
Tests are organized into focused classes in `tests/test_loadset_enhanced.py`:
- `TestLoadSetReadJson`: JSON loading and validation
- `TestLoadSetConvertTo`: Unit conversion testing
- `TestLoadSetFactor`: Load scaling functionality
- `TestLoadSetToAnsys`: ANSYS export validation

### Data Sources
- **`solution/loads/new_loads`**: Updated JSON load data files
- **`solution/loads/old_loads`**: Original load data files

## Configuration Notes

- **Python version**: Requires Python ≥3.13
- **Test configuration**: Defined in `pyproject.toml` with verbose output, colored results, and short tracebacks
- **VS Code integration**: Configured with proper Python interpreter and test discovery settings