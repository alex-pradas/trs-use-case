# Demo Examples

This directory contains demonstration examples of different approaches to using the LoadSet processing system.

## Files

### `loads_agent.py`
**Simple Agent Demo** - Demonstrates the direct pydantic-ai agent approach using MCPServerStdio.

This example shows:
- Direct agent creation with `pydantic_ai.Agent`
- MCPServerStdio connection to loads MCP server
- Simple prompt-based processing
- Logfire instrumentation
- Basic result handling

**Usage:**
```bash
uv run python demo/loads_agent.py
```

**When to use this approach:**
- Simple scripts and one-off processing
- Learning how pydantic-ai agents work
- Quick prototyping
- When you don't need dependency injection

**Alternative approach:** See `tools/agents.py` for the production architecture using dependency injection and structured responses.

## Architecture Notes

The demo shows the **direct approach** to pydantic-ai agents, while the production code in `tools/agents.py` uses the **dependency injection approach**. Both are valid patterns according to Pydantic-AI documentation:

- **Direct approach** (this demo): Simple, straightforward for basic use cases
- **Dependency injection** (production): Better for complex applications with multiple servers and structured responses

Choose the approach that best fits your use case complexity and requirements.