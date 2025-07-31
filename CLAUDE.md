# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

This project uses a **simplified dual architecture** for LoadSet processing:

### **For Pydantic AI Agents** (Primary Usage)
- **Direct Provider Access**: Agents use `LoadSetMCPProvider` directly via dependency injection
- **No MCP Overhead**: Direct method calls for maximum performance
- **Location**: `tools/agents.py` contains `create_loadset_agent()`
- **Usage**: `provider = LoadSetMCPProvider()` → `agent.run_sync(prompt, deps=provider)`

### **For External MCP Clients** (External Access)
- **FastMCP Server**: Available via `tools/mcps/loads_mcp_server.py` for external MCP protocol access
- **Usage**: Run `python -m tools.mcps.start_servers` for external clients

### **Deprecated Components** (Removed)
- ❌ `MCPServerProvider` wrapper - Use `LoadSetMCPProvider` directly
- ❌ `create_python_agent` and `create_script_agent` - Use alternative approaches
- ❌ `tools/dependencies.py` and `tools/response_models.py` - No longer needed

## Data Files Location

LoadSet data files are located in `use_case_definition/data/loads/`:
- `03_A_new_loads.json` - New loads data set A (Newton units)
- `03_B_new_loads.json` - New loads data set B (lbf units)  
- `03_old_loads.json` - Original loads data (Newton units)

## External Resources and Guidance

- **FastMCP Information**: If you need to know about FastMCP, fetch the info from https://gofastmcp.com/llms-full.txt
- **Pydantic AI Information**: If you need to know about pydantic-ai, fetch the information from https://ai.pydantic.dev/llms-full.txt

## Development Guidelines

### **Agent Development**
- Use `create_loadset_agent()` for LoadSet processing tasks
- Pass `LoadSetMCPProvider()` instance as `deps` parameter
- Tools return raw dict responses (no response model wrappers needed)

### **Testing**
- Core functionality: `tests/tools/test_loadset_core.py` and `tests/mcps/test_mcp_server.py`
- Agent functionality: `tests/test_agents.py`
- Run tests: `python -m pytest tests/tools tests/mcps tests/test_agents.py -v`

### **MCP Server Development**
- Core logic in `LoadSetMCPProvider` class methods
- FastMCP server for external access automatically registers all provider methods
- State management handled within provider instances

## Commit Guidelines

- Do not say on commits that it has been generated with Claude Code or Co-Authored.