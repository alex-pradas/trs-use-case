"""
Simplified pydantic-ai agents following best practices.

This module implements the new simplified agent architecture using:
- Dependency injection for MCP servers
- RunContext for accessing dependencies in tools
- Structured Pydantic models for responses
- Centralized error handling via pydantic-ai
- Elimination of MCP bridge abstraction

Expected code reduction: 60% (from 400 to ~160 lines)
"""

from pydantic_ai import Agent, RunContext

from pathlib import Path
from loads import ForceUnit
from tools.model_config import get_model_name
from tools.mcps.loads_mcp_server import LoadSetMCPProvider
# No need for response models - using raw dict responses


def create_loadset_agent(
    system_prompt: str | None = None,
) -> Agent[LoadSetMCPProvider, str]:
    """Create a LoadSet processing agent using LoadSetMCPProvider directly."""
    default_prompt = "You are an expert aerospace structural loads analyst with access to LoadSet processing tools. Use available tools for operations and provide clear explanations."

    agent = Agent(
        get_model_name(),
        deps_type=LoadSetMCPProvider,
        system_prompt=system_prompt or default_prompt,
    )

    @agent.tool
    def load_from_json(
        ctx: RunContext[LoadSetMCPProvider], file_path: str
    ) -> dict:
        """Load a LoadSet from a JSON file."""
        return ctx.deps.load_from_json(Path(file_path))

    @agent.tool
    def load_from_resource(
        ctx: RunContext[LoadSetMCPProvider], resource_uri: str
    ) -> dict:
        """Load a LoadSet from a resource URI (e.g., 'loadsets://new_loads.json')."""
        return ctx.deps.load_from_resource(resource_uri)

    @agent.tool
    def convert_units(
        ctx: RunContext[LoadSetMCPProvider], target_units: ForceUnit
    ) -> dict:
        """Convert the current LoadSet to different units (N, kN, lbf, klbf)."""
        return ctx.deps.convert_units(target_units) 

    @agent.tool
    def scale_loads(
        ctx: RunContext[LoadSetMCPProvider], factor: float
    ) -> dict:
        """Scale all loads in the current LoadSet by a factor."""
        return ctx.deps.scale_loads(factor)

    @agent.tool
    def export_to_ansys(
        ctx: RunContext[LoadSetMCPProvider], folder_path: str | None = None, name_stem: str | None = None
    ) -> dict:
        """Export the current LoadSet to ANSYS format files. Both parameters are optional."""
        if folder_path is None:
            return ctx.deps.export_to_ansys(None, name_stem)
        else:
            return ctx.deps.export_to_ansys(Path(folder_path), name_stem)

    @agent.tool
    def get_load_summary(ctx: RunContext[LoadSetMCPProvider]) -> dict:
        """Get summary information about the current LoadSet."""
        return ctx.deps.get_load_summary()

    @agent.tool
    def list_load_cases(ctx: RunContext[LoadSetMCPProvider]) -> dict:
        """List all load cases in the current LoadSet."""
        return ctx.deps.list_load_cases()

    @agent.tool
    def load_second_loadset_from_resource(
        ctx: RunContext[LoadSetMCPProvider], resource_uri: str
    ) -> dict:
        """Load a second LoadSet from a resource URI for comparison."""
        return ctx.deps.load_second_loadset_from_resource(resource_uri)

    @agent.tool
    def compare_loadsets(ctx: RunContext[LoadSetMCPProvider]) -> dict:
        """Compare two LoadSets with detailed analysis. Requires loading two loadsets first."""
        return ctx.deps.compare_loadsets()

    @agent.tool
    def get_comparison_summary(ctx: RunContext[LoadSetMCPProvider]) -> dict:
        """Get a high-level summary of the current comparison."""
        return ctx.deps.get_comparison_summary()

    @agent.tool
    def envelope_loadset(ctx: RunContext[LoadSetMCPProvider]) -> dict:
        """Create an envelope LoadSet containing only load cases with extreme values."""
        return ctx.deps.envelope_loadset()

    @agent.tool
    def get_point_extremes(ctx: RunContext[LoadSetMCPProvider]) -> dict:
        """Get extreme values (min/max) for each point and component in the current LoadSet."""
        return ctx.deps.get_point_extremes()

    return agent


# DEPRECATED AGENTS REMOVED - Use alternative approaches for Python execution and script generation


__all__ = [
    "create_loadset_agent",
]
