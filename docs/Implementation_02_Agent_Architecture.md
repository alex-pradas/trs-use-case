# Implementation 2: Pydantic AI Agent Architecture with Dependency Injection

## Overview

This implementation uses **Pydantic AI agents with dependency injection** for LoadSet processing operations. The architecture separates concerns between agent creation, business logic (LoadSetMCPProvider), and runtime execution.

## Architecture Pattern

### Core Components

```python
# 1. Business Logic Provider (Stateful)
provider = LoadSetMCPProvider()  # Maintains state: _current_loadset, _comparison_loadset

# 2. Agent Creation (Stateless)
agent = create_loadset_agent(system_prompt=system_prompt)

# 3. Runtime Injection
result = agent.run_sync(USER_PROMPT, deps=provider)
```

### Key Design Decisions

1. **Dependency Injection Pattern**: Provider passed at runtime via `deps` parameter
2. **RunContext[T] Typing**: Tools receive `ctx: RunContext[LoadSetMCPProvider]` for type safety
3. **Stateful Provider**: `LoadSetMCPProvider` maintains workflow state between tool calls
4. **Tool Registration**: Tools defined as agent methods using `@agent.tool` decorator

## Advantages

### 🎯 **State Isolation**
- Each workflow gets a fresh `LoadSetMCPProvider` instance
- No shared state between concurrent operations
- Safe for multi-user/multi-threaded environments

```python
# Each execution has isolated state
workflow1 = agent.run_sync(prompt1, deps=LoadSetMCPProvider())  # Independent
workflow2 = agent.run_sync(prompt2, deps=LoadSetMCPProvider())  # Independent
```

### 🧪 **Testing Excellence**
- Easy to inject mock providers for unit tests
- Full control over provider state and behavior
- Type-safe mocking with proper interfaces

```python
# Testing example
mock_provider = MockLoadSetMCPProvider()
mock_provider.load_from_json.return_value = test_data
result = agent.run_sync(test_prompt, deps=mock_provider)
```

### 🔧 **Runtime Flexibility**
- Can swap different provider implementations
- Different configurations per execution
- Dynamic provider selection based on context

### 🛡️ **Type Safety**
- `RunContext[LoadSetMCPProvider]` provides full type checking
- IDE autocomplete for `ctx.deps.method_name()`
- Compile-time error detection

### ⚡ **Memory Efficiency**
- Providers only exist during execution
- No persistent state in agent objects
- Efficient resource cleanup

### 🏗️ **Clean Architecture**
- Clear separation of concerns
- Agent = orchestration, Provider = business logic
- Follows dependency inversion principle

## Disadvantages

### 📝 **Boilerplate Complexity**
- Two-step creation process (agent + provider)
- Must remember to pass `deps` parameter
- More complex than direct tool embedding

### 🧠 **Learning Curve**
- Understanding `RunContext[T]` pattern
- Grasping dependency injection concepts
- More advanced Python patterns required

### 🔗 **Runtime Coupling**
- Agent and provider must be coordinated at runtime
- Potential runtime errors if `deps` forgotten
- Less self-contained than embedded tools

## Alternative Approaches Considered

### Direct Tool Embedding
```python
# Rejected approach
def create_agent_with_embedded_tools():
    provider = LoadSetMCPProvider()  # Shared state - problematic
    agent = Agent(tools=[
        Tool(provider.load_from_json, name="load_from_json"),
        # ...
    ])
    return agent
```

**Why Rejected:**
- Shared state between all agent invocations
- Difficult to test with mocks
- Memory inefficient (provider lives forever)
- Concurrency issues in multi-user scenarios

### ToolSet Factory Pattern
```python
# Considered but unnecessary complexity
def create_agent_with_toolset():
    def tool_factory():
        provider = LoadSetMCPProvider()
        return [Tool(provider.method, name="method") for method in provider_methods]
    return Agent(tools=tool_factory)
```

**Why Not Chosen:**
- Adds complexity without clear benefits
- Still requires understanding of factory patterns
- Current dependency injection is cleaner

## Why This Architecture Was Chosen

### 1. **Stateful Workflow Requirements**
LoadSet processing requires maintaining state across multiple tool calls:
- `_current_loadset`: Currently loaded dataset
- `_comparison_loadset`: Second dataset for comparisons
- `_current_comparison`: Comparison results

Each workflow needs isolated state to prevent data contamination.

### 2. **Production-Grade Requirements**
- **Testability**: Critical for aerospace applications
- **Concurrency**: Must support multiple simultaneous users
- **Maintainability**: Clear separation of concerns
- **Extensibility**: Easy to add new provider implementations

### 3. **Type Safety Critical**
Aerospace applications require compile-time error detection:
```python
# Type-safe access to provider methods
def load_from_resource(ctx: RunContext[LoadSetMCPProvider], resource_uri: str) -> dict:
    return ctx.deps.load_from_resource(resource_uri)  # IDE knows all methods
```

### 4. **Framework Alignment**
Pydantic AI's dependency injection is the recommended pattern for stateful operations, following FastAPI-style dependency injection that Python developers understand.

## Implementation Details

### Agent Creation
```python
def create_loadset_agent(system_prompt: str | None = None) -> Agent[LoadSetMCPProvider, str]:
    agent = Agent(
        get_model_name(),
        deps_type=LoadSetMCPProvider,  # Type specification
        system_prompt=system_prompt or default_prompt,
    )
    # Tools registered with @agent.tool decorator
```

### Tool Pattern
```python
@agent.tool
def tool_name(ctx: RunContext[LoadSetMCPProvider], params: type) -> dict:
    """Tool description for LLM."""
    return ctx.deps.provider_method(params)  # Direct method call
```

### Usage Pattern
```python
# Standard workflow
system_prompt = load_system_prompt()
agent = create_loadset_agent(system_prompt=system_prompt)
provider = LoadSetMCPProvider()
result = agent.run_sync(USER_PROMPT, deps=provider)
```

## Future Considerations

### Potential Enhancements
1. **Provider Interface**: Define abstract base class for multiple provider implementations
2. **Configuration Injection**: Pass configuration objects alongside providers
3. **Async Support**: Upgrade to async providers for better performance
4. **Provider Pooling**: Implement provider pooling for high-concurrency scenarios

### Migration Path
This architecture provides a clean foundation for future implementations:
- **Implementation 3**: Could add async support
- **Implementation 4**: Could implement provider interfaces
- **Implementation 5**: Could add advanced caching/pooling

## Conclusion

The dependency injection pattern provides the **optimal balance** of:
- **Simplicity**: Clean, understandable code structure
- **Flexibility**: Runtime provider swapping and testing
- **Safety**: Type checking and state isolation
- **Performance**: Efficient memory usage and cleanup

While it requires understanding dependency injection concepts, the benefits for a **production aerospace application** with **stateful workflows** make it the clear architectural choice.

This pattern positions the codebase for maintainable, testable, and scalable load processing operations while following Python ecosystem best practices established by FastAPI and Pydantic.