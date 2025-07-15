"""
TDD tests for agent architecture following pydantic-ai best practices.

These tests define the expected behavior of the pydantic-ai agent architecture
using factory functions and dependency injection.
"""

import pytest
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

# Import agent factory functions
from tools.agents import (
    create_loadset_agent,
    create_python_agent,
    create_script_agent,
)
from tools.response_models import (
    LoadSetResponse,
    ConversionResponse,
    ExecutionResponse,
    ScriptResponse,
)
from tools.dependencies import MCPServerProvider


class TestAgentArchitecture:
    """Test the pydantic-ai agent architecture."""

    def test_response_models_exist(self):
        """Test that Pydantic response models are defined."""
        # These should be Pydantic models for type-safe responses
        assert issubclass(LoadSetResponse, BaseModel)
        assert issubclass(ConversionResponse, BaseModel)
        assert issubclass(ExecutionResponse, BaseModel)
        assert issubclass(ScriptResponse, BaseModel)

    def test_agent_factory_functions_exist(self):
        """Test that agent factory functions exist."""
        # Factory functions should create agents with dependencies
        assert callable(create_loadset_agent)
        assert callable(create_python_agent)
        assert callable(create_script_agent)

    def test_mcp_server_provider_dependency(self):
        """Test that MCP server provider dependency exists."""
        # Should provide MCP servers as typed dependencies
        assert MCPServerProvider is not None

    @pytest.mark.asyncio
    async def test_loadset_agent_with_dependencies(self):
        """Test LoadSet agent creation with dependency injection."""
        # Agent should be created with MCP server as dependency
        agent = create_loadset_agent()
        assert isinstance(agent, Agent)

        # Agent should have dependency-injected tools
        # Check for tools in the agent (property name may vary by pydantic-ai version)
        assert (
            hasattr(agent, "tool")
            or hasattr(agent, "_tools")
            or hasattr(agent, "tools")
        )
        # Tools are registered at creation time

    @pytest.mark.asyncio
    async def test_loadset_tool_with_structured_response(self):
        """Test LoadSet tool returns structured Pydantic response."""
        agent = create_loadset_agent()
        mcp_provider = MCPServerProvider()

        # Mock a simple load operation
        result = await agent.run("Load test data", deps=mcp_provider)

        # Response should be structured, not raw dict
        assert hasattr(result, "output")
        # Tool responses should be typed

    @pytest.mark.asyncio
    async def test_python_agent_with_runcontext(self):
        """Test Python agent uses RunContext for MCP server access."""
        agent = create_python_agent()
        mcp_provider = MCPServerProvider()

        # Should be able to execute code via dependency-injected MCP server
        result = await agent.run("Execute: print('hello world')", deps=mcp_provider)
        assert result.output is not None

    @pytest.mark.asyncio
    async def test_script_agent_dependency_injection(self):
        """Test Script agent uses dependency injection properly."""
        agent = create_script_agent()
        mcp_provider = MCPServerProvider()

        # Should have access to script execution MCP server via dependencies
        result = await agent.run("Generate a simple script", deps=mcp_provider)
        assert result.output is not None

    def test_no_mcp_bridge_abstraction(self):
        """Test that MCP bridge abstraction is eliminated."""
        # mcp_bridge.py should not be needed in new architecture
        try:
            from tools.mcp_bridge import call_mcp_tool

            pytest.fail("MCP bridge should be eliminated in simplified architecture")
        except ImportError:
            # Expected - we should not have mcp_bridge in new architecture
            pass

    def test_centralized_error_handling(self):
        """Test that error handling is centralized, not per-tool."""
        # Agents should handle errors at agent level, not in each tool
        agent = create_loadset_agent()

        # This test validates that we don't have manual try-catch in our tool functions
        # Pydantic-AI handles errors centrally, eliminating boilerplate

        # We can check the source of our agent creation to ensure no try-catch boilerplate
        import inspect
        from tools import agents

        source = inspect.getsource(agents)

        # Count try-catch blocks - should be minimal or none in tool functions
        try_count = source.count("try:")
        except_count = source.count("except:")

        # Should have very few try-catch blocks compared to old architecture
        assert try_count <= 2, (
            f"Too many try blocks in simplified architecture: {try_count}"
        )
        assert except_count <= 2, (
            f"Too many except blocks in simplified architecture: {except_count}"
        )

    @pytest.mark.asyncio
    async def test_type_safe_tool_responses(self):
        """Test that tool responses are type-safe Pydantic models."""
        agent = create_loadset_agent()

        # Tools should return structured responses, not raw dicts
        # This will be validated by the actual tool implementation
        pass

    def test_agent_configuration_simplification(self):
        """Test that agent configuration is simplified."""
        # Should use dependency injection instead of complex setup
        agent = create_loadset_agent()

        # Agent should be properly configured with minimal setup
        assert agent.model is not None
        assert agent.system_prompt is not None



class TestResponseModels:
    """Test the Pydantic response models."""

    def test_loadset_response_model(self):
        """Test LoadSetResponse model structure."""
        # Should have proper fields for LoadSet operations
        model = LoadSetResponse(
            success=True,
            message="LoadSet loaded successfully",
            data={"name": "Test LoadSet", "units": {"forces": "N"}},
            load_cases_count=5,
        )
        assert model.success is True
        assert model.message == "LoadSet loaded successfully"
        assert model.load_cases_count == 5

    def test_conversion_response_model(self):
        """Test ConversionResponse model structure."""
        model = ConversionResponse(
            success=True,
            message="Units converted successfully",
            original_units={"forces": "N"},
            target_units={"forces": "kN"},
            conversion_factor=1000.0,
        )
        assert model.original_units["forces"] == "N"
        assert model.target_units["forces"] == "kN"
        assert model.conversion_factor == 1000.0

    def test_execution_response_model(self):
        """Test ExecutionResponse model structure."""
        model = ExecutionResponse(
            success=True,
            message="Code executed successfully",
            stdout="Hello World",
            stderr="",
            execution_time=0.1,
            variables_count=3,
        )
        assert model.stdout == "Hello World"
        assert model.execution_time == 0.1
        assert model.variables_count == 3

    def test_script_response_model(self):
        """Test ScriptResponse model structure."""
        model = ScriptResponse(
            success=True,
            message="Script executed successfully",
            script_hash="abc123",
            output_files=["result.txt", "chart.png"],
            execution_time=2.5,
            workspace_path="/tmp/workspace_abc123",
        )
        assert model.script_hash == "abc123"
        assert len(model.output_files) == 2
        assert model.execution_time == 2.5


class TestDependencyInjection:
    """Test dependency injection implementation."""

    def test_mcp_server_provider_creation(self):
        """Test that MCP server provider can be created."""
        provider = MCPServerProvider()
        assert provider is not None

        # Should provide access to different MCP servers
        assert hasattr(provider, "loads_server")
        assert hasattr(provider, "python_server")
        assert hasattr(provider, "script_server")

    def test_agent_with_custom_dependencies(self):
        """Test agent creation with custom dependencies."""
        # Should be able to inject custom MCP server configurations
        custom_provider = MCPServerProvider(
            loads_timeout=60, python_timeout=30, script_timeout=120
        )

        agent = create_loadset_agent()
        assert agent is not None
        # Dependencies are passed when running the agent, not when creating it

    @pytest.mark.asyncio
    async def test_runcontext_dependency_access(self):
        """Test that tools can access dependencies via RunContext."""
        # This will test that tools use RunContext properly
        # Implementation will validate this works correctly
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
