"""
Tests for LoadSet agent architecture following pydantic-ai best practices.

These tests validate the simplified pydantic-ai agent architecture
with direct LoadSetMCPProvider usage.
"""

import pytest
from pydantic_ai import Agent

# Import agent factory function
from tools.agents import create_loadset_agent
from tools.mcps.loads_mcp_server import LoadSetMCPProvider


class TestLoadSetAgentArchitecture:
    """Test the simplified pydantic-ai LoadSet agent architecture."""

    def test_loadset_agent_factory_exists(self):
        """Test that LoadSet agent factory function exists."""
        # Factory function should create agent with direct provider dependency
        assert callable(create_loadset_agent)

    def test_loadset_provider_dependency(self):
        """Test that LoadSet MCP provider dependency exists."""
        # Should provide LoadSet operations as direct dependency
        provider = LoadSetMCPProvider()
        assert provider is not None
        assert hasattr(provider, "load_from_json")
        assert hasattr(provider, "convert_units")
        assert hasattr(provider, "scale_loads")
        assert hasattr(provider, "export_to_ansys")
        assert hasattr(provider, "compare_loadsets")

    def test_loadset_agent_creation(self):
        """Test LoadSet agent creation with direct provider."""
        # Agent should be created with LoadSetMCPProvider as dependency
        agent = create_loadset_agent()
        assert isinstance(agent, Agent)

        # Agent should have the correct dependency type
        assert agent._deps_type == LoadSetMCPProvider

    def test_loadset_agent_with_custom_prompt(self):
        """Test LoadSet agent creation with custom system prompt."""
        custom_prompt = "Custom system prompt for testing"
        agent = create_loadset_agent(system_prompt=custom_prompt)
        assert isinstance(agent, Agent)

    def test_simplified_architecture(self):
        """Test that the architecture is simplified with direct provider access."""
        agent = create_loadset_agent()

        # Agent should use LoadSetMCPProvider directly, not wrapped in MCPServerProvider
        assert agent._deps_type == LoadSetMCPProvider

        # This validates we eliminated the complex wrapper layer

    def test_agent_configuration_simplification(self):
        """Test that agent configuration is simplified."""
        # Should use dependency injection instead of complex setup
        agent = create_loadset_agent()

        # Agent should be properly configured with minimal setup
        assert agent.model is not None
        assert agent.system_prompt is not None


class TestLoadSetProviderIntegration:
    """Test LoadSetMCPProvider integration with the agent."""

    def test_provider_state_management(self):
        """Test that provider manages state correctly."""
        provider = LoadSetMCPProvider()

        # Should start with no current loadset
        assert provider._current_loadset is None
        assert provider._comparison_loadset is None
        assert provider._current_comparison is None

    def test_provider_reset_functionality(self):
        """Test that provider can reset state."""
        provider = LoadSetMCPProvider()

        # Reset should work without errors
        provider.reset_state()
        assert provider._current_loadset is None
        assert provider._comparison_loadset is None
        assert provider._current_comparison is None

    @pytest.mark.asyncio
    async def test_agent_provider_integration(self):
        """Test that agent works with provider (basic integration test)."""
        agent = create_loadset_agent()
        provider = LoadSetMCPProvider()

        # Should be able to create both without errors
        assert agent is not None
        assert provider is not None

        # This validates that the dependency types match
        assert agent._deps_type is type(provider)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
