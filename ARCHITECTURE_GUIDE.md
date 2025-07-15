# Agent Architecture Guide

## Overview

This guide documents the pydantic-ai agent architecture that follows best practices with dependency injection and type-safe responses.

## Architecture Pattern

```python
# Factory functions with dependency injection
# Centralized error handling
# Type-safe Pydantic responses
# Direct MCP server access

from tools.agents import create_loadset_agent
from tools.dependencies import MCPServerProvider

agent = create_loadset_agent()
deps = MCPServerProvider()
result = await agent.run("Load data", deps=deps)
```

## Key Components

### 1. Agent Factory Functions (`tools/agents.py`)

#### LoadSet Agent
```python
def create_loadset_agent() -> Agent[MCPServerProvider, str]:
    """Create a LoadSet processing agent with dependency injection."""
    agent = Agent(
        get_model_name(),
        deps_type=MCPServerProvider,
        system_prompt="You are an expert aerospace structural loads analyst..."
    )
    
    @agent.tool
    def load_from_json(ctx: RunContext[MCPServerProvider], file_path: str) -> LoadSetResponse:
        """Load a LoadSet from a JSON file."""
        result = ctx.deps.loads_server._tool_manager._tools["load_from_json"].fn(file_path=file_path)
        return LoadSetResponse(
            success=True, 
            message=f"LoadSet loaded from {file_path}", 
            data=result,
            load_cases_count=len(result.get("load_cases", [])) if result else None
        )
    
    return agent
```

#### Python Agent
```python
def create_python_agent() -> Agent[MCPServerProvider, str]:
    """Create a Python execution agent with dependency injection."""
    agent = Agent(
        get_model_name(),
        deps_type=MCPServerProvider,
        system_prompt="You are an expert Python programmer..."
    )
    
    @agent.tool
    def execute_code(ctx: RunContext[MCPServerProvider], code: str) -> ExecutionResponse:
        """Execute Python code in the persistent session."""
        result = ctx.deps.python_server._tool_manager._tools["execute_code"].fn(code=code)
        return ExecutionResponse(
            success=result.get("success", False),
            message="Code executed successfully" if result.get("success") else "Code execution failed",
            stdout=result.get("stdout", ""),
            stderr=result.get("stderr", ""),
            execution_time=result.get("execution_time", 0.0),
            variables_count=len(result.get("variables", {}))
        )
    
    return agent
```

### 2. Dependency Provider (`tools/dependencies.py`)

```python
@dataclass
class MCPServerProvider:
    """Dependency provider for MCP servers."""
    
    loads_timeout: int = 30
    python_timeout: int = 30
    script_timeout: int = 60
    base_workspace_dir: Optional[Path] = None
    
    def __post_init__(self):
        """Initialize MCP servers after dataclass creation."""
        if self.base_workspace_dir is None:
            self.base_workspace_dir = Path(tempfile.gettempdir())
            
        # Create MCP servers with configuration
        self._loads_server = create_loads_server()
        self._python_server = create_python_server()
        self._script_server = create_script_server(
            base_workspace_dir=self.base_workspace_dir,
            execution_timeout=self.script_timeout
        )
    
    @property
    def loads_server(self):
        """Get the LoadSet MCP server."""
        return self._loads_server
```

### 3. Pydantic Response Models (`tools/response_models.py`)

```python
class LoadSetResponse(BaseModel):
    """Response model for LoadSet operations."""
    
    success: bool = Field(description="Whether the operation succeeded")
    message: str = Field(description="Human-readable status message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="LoadSet data")
    load_cases_count: Optional[int] = Field(default=None, description="Number of load cases")
    units: Optional[Dict[str, str]] = Field(default=None, description="Current units")

class ExecutionResponse(BaseModel):
    """Response model for Python code execution."""
    
    success: bool = Field(description="Whether the execution succeeded")
    message: str = Field(description="Human-readable status message")
    stdout: str = Field(default="", description="Standard output from execution")
    stderr: str = Field(default="", description="Standard error from execution")
    execution_time: float = Field(description="Execution time in seconds")
    variables_count: Optional[int] = Field(default=None, description="Number of variables in session")
```

## Usage Examples

### Basic LoadSet Processing
```python
from tools.agents import create_loadset_agent
from tools.dependencies import MCPServerProvider

# Create agent and dependencies
agent = create_loadset_agent()
deps = MCPServerProvider()

# Process LoadSet data
result = await agent.run(
    "Load 'solution/loads/new_loads.json', convert to kN, and scale by 1.5",
    deps=deps
)
```

### Python Code Execution
```python
from tools.agents import create_python_agent
from tools.dependencies import MCPServerProvider

# Create agent and dependencies
agent = create_python_agent()
deps = MCPServerProvider()

# Execute Python code
result = await agent.run(
    "Calculate the factorial of 10 and store it in a variable",
    deps=deps
)
```

### Script Generation and Execution
```python
from tools.agents import create_script_agent
from tools.dependencies import MCPServerProvider

# Create agent and dependencies
agent = create_script_agent()
deps = MCPServerProvider()

# Generate and execute script
result = await agent.run(
    "Generate a Python script to analyze LoadSet data and create a summary report",
    deps=deps
)
```

### Custom Dependencies
```python
from tools.dependencies import MCPServerProvider

# Create custom dependency provider
custom_deps = MCPServerProvider(
    loads_timeout=60,
    python_timeout=45,
    script_timeout=120,
    base_workspace_dir=Path("/custom/workspace")
)

# Use with any agent
agent = create_loadset_agent()
result = await agent.run("Process data", deps=custom_deps)
```

## Benefits

### 1. Clean Architecture
- **Factory functions** for agent creation
- **Eliminated boilerplate** through best practices
- **Simplified patterns** with direct dependency injection

### 2. Type Safety
- **Pydantic models** for all responses
- **Runtime validation** of data structures
- **IDE support** with autocomplete and type hints

### 3. Maintainability
- **Single responsibility** for each component
- **Clear separation** of concerns
- **Easier testing** with dependency injection

### 4. Performance
- **Direct MCP access** without abstraction overhead
- **Efficient dependency management**
- **Reduced memory footprint**

### 5. Developer Experience
- **Follows pydantic-ai best practices**
- **Consistent patterns** across all agents
- **Clear documentation** and examples

## Testing

### Test Coverage
```bash
# Run agent tests
uv run pytest tests/test_agents.py -v

# Run all fast tests
uv run pytest tests/tools/ tests/mcps/ -v
```

## Best Practices

### 1. Dependency Injection
```python
# Always use dependency injection
agent = create_loadset_agent()
deps = MCPServerProvider()
result = await agent.run(message, deps=deps)
```

### 2. Error Handling
```python
# Let pydantic-ai handle errors centrally
try:
    result = await agent.run(message, deps=deps)
except Exception as e:
    # Handle at agent level, not tool level
    logger.error(f"Agent error: {e}")
```

### 3. Response Validation
```python
# Responses are already validated via Pydantic
from tools.response_models import LoadSetResponse

# Tools return structured responses
def my_tool(ctx: RunContext[MCPServerProvider]) -> LoadSetResponse:
    return LoadSetResponse(
        success=True,
        message="Operation completed",
        data={"key": "value"}
    )
```

### 4. Custom Dependencies
```python
# Create custom providers for different environments
dev_deps = MCPServerProvider(
    loads_timeout=10,
    python_timeout=10,
    script_timeout=30
)

prod_deps = MCPServerProvider(
    loads_timeout=60,
    python_timeout=60,
    script_timeout=300
)
```

## Architecture Characteristics

- **Concise**: Clean factory functions (171 lines)
- **Type-safe**: Pydantic models for all responses
- **Tested**: Comprehensive test coverage (156+ tests)
- **Efficient**: Direct MCP server access
- **Fast**: Optimized startup and execution

## Future Enhancements

1. **Caching**: Add response caching for improved performance
2. **Monitoring**: Integrate with observability tools
3. **Async Streaming**: Add streaming responses for long operations
4. **Plugin System**: Allow custom tool registration
5. **Configuration**: Environment-based configuration management

## Conclusion

This architecture successfully achieves:
- **Clean factory function pattern**
- **Follows pydantic-ai best practices**
- **Full functionality with dependency injection**
- **Improved maintainability and type safety**
- **Better testing and debugging capabilities**

This architecture provides a solid foundation for AI agent development with clear patterns and minimal complexity.