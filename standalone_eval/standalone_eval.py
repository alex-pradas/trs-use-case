#!/usr/bin/env python3
"""
Standalone evaluation script for LoadSet processing with local vLLM model.

This is a self-contained script that:
1. Connects to a local Qwen model server via vLLM (OpenAI-compatible endpoint)
2. Provides LoadSet MCP tools dynamically (no hardcoded tools)
3. Uses the comprehensive system prompt for aerospace structural analysis
4. Accepts user messages from external clients

Usage:
    python standalone_eval.py "Your message here"

Or run interactively:
    python standalone_eval.py

Requirements:
    - vLLM server running locally at http://localhost:8000
    - pydantic-ai package installed
    - loads package (from parent directory) accessible
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from loads import LoadSet, ForceUnit, LoadSetCompare
from os import PathLike


# ============================================================================
# LOADSET MCP PROVIDER (Embedded)
# ============================================================================

class LoadSetMCPProvider:
    """Provider class for LoadSet MCP operations with encapsulated state."""

    def __init__(self):
        self._current_loadset: Optional[LoadSet] = None
        self._comparison_loadset: Optional[LoadSet] = None
        self._current_comparison: Optional[LoadSetCompare] = None

    def reset_state(self):
        """Reset the LoadSet state."""
        self._current_loadset = None
        self._comparison_loadset = None
        self._current_comparison = None

    def load_from_json(self, file_path: PathLike) -> dict:
        """Load a LoadSet from a JSON file."""
        try:
            self._current_loadset = LoadSet.read_json(file_path)
            return {
                "success": True,
                "message": f"LoadSet loaded from {file_path}",
                "loadset_name": self._current_loadset.name,
                "loads_type": self._current_loadset.loads_type,
                "num_load_cases": len(self._current_loadset.load_cases),
                "units": {
                    "forces": self._current_loadset.units.forces,
                    "moments": self._current_loadset.units.moments,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def convert_units(self, target_units: ForceUnit) -> dict:
        """Convert the current LoadSet to different units."""
        if not self._current_loadset:
            return {"success": False, "error": "No LoadSet loaded"}

        try:
            self._current_loadset.convert_units(target_units)
            return {
                "success": True,
                "message": f"Units converted to {target_units}",
                "current_units": {
                    "forces": self._current_loadset.units.forces,
                    "moments": self._current_loadset.units.moments,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def scale_loads(self, factor: float) -> dict:
        """Scale all loads in the current LoadSet by a factor."""
        if not self._current_loadset:
            return {"success": False, "error": "No LoadSet loaded"}

        try:
            self._current_loadset.scale_loads(factor)
            return {
                "success": True,
                "message": f"Loads scaled by factor {factor}",
                "scale_factor": factor,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def export_to_ansys(
        self, folder_path: Optional[PathLike] = None, name_stem: Optional[str] = None
    ) -> dict:
        """Export the current LoadSet to ANSYS format files."""
        if not self._current_loadset:
            return {"success": False, "error": "No LoadSet loaded"}

        try:
            self._current_loadset.export_to_ansys(folder_path, name_stem)
            return {
                "success": True,
                "message": f"LoadSet exported to ANSYS format",
                "output_directory": str(folder_path) if folder_path else "default",
                "num_files": len(self._current_loadset.load_cases),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_load_summary(self) -> dict:
        """Get summary information about the current LoadSet."""
        if not self._current_loadset:
            return {"success": False, "error": "No LoadSet loaded"}

        try:
            summary = self._current_loadset.summary()
            return {"success": True, "summary": summary}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_load_cases(self) -> dict:
        """List all load cases in the current LoadSet."""
        if not self._current_loadset:
            return {"success": False, "error": "No LoadSet loaded"}

        try:
            cases = [lc.name for lc in self._current_loadset.load_cases]
            return {
                "success": True,
                "load_cases": cases,
                "count": len(cases),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def load_second_loadset(self, file_path: PathLike) -> dict:
        """Load a second LoadSet from a JSON file for comparison."""
        try:
            self._comparison_loadset = LoadSet.read_json(file_path)
            return {
                "success": True,
                "message": f"Second LoadSet loaded from {file_path}",
                "loadset_name": self._comparison_loadset.name,
                "num_load_cases": len(self._comparison_loadset.load_cases),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def compare_loadsets(self) -> dict:
        """Compare two LoadSets with detailed analysis."""
        if not self._current_loadset or not self._comparison_loadset:
            return {
                "success": False,
                "error": "Both LoadSets must be loaded before comparison",
            }

        try:
            self._current_comparison = LoadSetCompare(
                new_loads=self._current_loadset,
                old_loads=self._comparison_loadset,
            )
            return {
                "success": True,
                "message": "LoadSets compared successfully",
                "comparison_available": True,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_comparison_summary(self) -> dict:
        """Get a high-level summary of the current comparison."""
        if not self._current_comparison:
            return {"success": False, "error": "No comparison available"}

        try:
            summary = self._current_comparison.summary()
            return {"success": True, "summary": summary}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def envelope_loadset(self) -> dict:
        """Create an envelope LoadSet containing only load cases with extreme values."""
        if not self._current_loadset:
            return {"success": False, "error": "No LoadSet loaded"}

        try:
            envelope = self._current_loadset.envelope()
            original_count = len(self._current_loadset.load_cases)
            envelope_count = len(envelope.load_cases)

            # Update current loadset to envelope
            self._current_loadset = envelope

            return {
                "success": True,
                "message": "Envelope LoadSet created",
                "original_cases": original_count,
                "envelope_cases": envelope_count,
                "reduction_percentage": round(
                    (1 - envelope_count / original_count) * 100, 1
                ),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_point_extremes(self) -> dict:
        """Get extreme values (min/max) for each point and component."""
        if not self._current_loadset:
            return {"success": False, "error": "No LoadSet loaded"}

        try:
            extremes = self._current_loadset.get_point_extremes()
            return {"success": True, "extremes": extremes}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def generate_comparison_report(self, output_dir: PathLike) -> dict:
        """Export complete comparison report including JSON data and chart images."""
        if not self._current_comparison:
            return {"success": False, "error": "No comparison available"}

        try:
            self._current_comparison.generate_comparison_report(output_dir=output_dir)
            return {
                "success": True,
                "message": "Comparison report generated",
                "output_directory": str(output_dir),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ============================================================================
# VLLM MODEL CONFIGURATION
# ============================================================================

def create_vllm_model(
    model_name: str = "Qwen/Qwen3-30B-A3B-Thinking",
    base_url: str = "http://localhost:8000/v1",
    api_key: str = "EMPTY"
) -> OpenAIModel:
    """
    Create a vLLM-compatible model using OpenAI provider.

    Args:
        model_name: Name of the model served by vLLM
        base_url: URL of the vLLM server (default: http://localhost:8000/v1)
        api_key: API key (default: "EMPTY" for local vLLM)

    Returns:
        Configured OpenAIModel for use with pydantic-ai
    """
    provider = OpenAIProvider(
        base_url=base_url,
        api_key=api_key,
    )
    return OpenAIModel(model_name, provider=provider)


# ============================================================================
# SYSTEM PROMPT
# ============================================================================

SYSTEM_PROMPT = """\
You are a structural analysis expert specializing in processing loads for aerospace components.

Your task is to support the user to manipulate and prepare the loads for a FEM analysis in ANSYS.

## Loads Processing (General Context)

If no information about the loads exist, they should be assumed that they are limit loads and therefore be multiplied by a safety factor of 1.5 to obtain the ultimate loads. This is an important step: limit loads have been used for an ultimate analysis in the past because it was assumed that the loads were ultimate.
Paying attention to loads units is critical. Our FEM models uses SI units (N N/m). If loads are provided in other units, they must always be converted to N and Nm for forces and moments respectively. The conversion factor is 1 klb = 4448.22 N and 1 klb-ft = 1.35582 Nm.
It is standard practice to always check new loads and compare it with a pre-existing set of previous applicable loads delivered by the customer. If they exceed, we need to perform a new analysis. But if none of the loads exceed and the geometry and all other inputs are the same, a complete analysis is not needed, simply the loads comparison results and an statement instead.
If the new loads exceed in any direction, then the envelope of old and new files need to be performed and that will be the collection of load cases that will be evaluated in the FEM analysis. If no loads exceed, no new analysis is needed and the final report shall contain the load comparison results and a statement indicating that no further analysis is needed.
The loads needs to be translated from the customer format to an ANSYS format readable by ANSYS. Each load case is stored in an individual file and then read directly, one by one, into ANSYS in a load-solve-release loop iteration.
The complete load set shall be reduced by applying a envelope operation, typically done during the loads processing activities. This operation dowselects the load cases as it remove those that are not max or min in any force or moment direction. It is best to create only the ansys load files corresponding to the envelope of the load set, as this will reduce the number of load cases to be evaluated in the FEM analysis.

Care shall be taken to ensure that the coordinates provided by the customer match the coordinates used in the FEM model. If they do not match, the loads must be transformed to the FEM model coordinates.

## Specific instructions for Loads Processing

Based on this context, you will help process loads and perform structural analysis tasks according to the EP Static Analysis procedures.
You have access to the LoadSet MCP server functions.

Key Operations required:
1. Process loads from customer format and convert units IF REQUIRED to our internal convention of N and Nm.
2. Factor in safety margins (1.5 for ultimate loads) if appropriate
3. Envelope loadset to reduce the number of load cases
4. If old loads are provided by user, compare new loads with previous applicable loads.
5. Determine if detailed analysis is needed based on load exceedance (if old loads are provided)
    6a. If a new analysis is needed, create an envelope of the loadset and generate the ANSYS input files
    6b. If no exceedances, provide comparison results and no-analysis statement

DO NOT ASK QUESTIONS. USE THE PROVIDED TOOLS TO PROCESS LOADS AND GENERATE OUTPUTS.
"""


# ============================================================================
# AGENT CREATION WITH DYNAMIC TOOLS
# ============================================================================

def create_loadset_agent(
    model: Optional[OpenAIModel] = None,
    system_prompt: str = SYSTEM_PROMPT
) -> Agent[LoadSetMCPProvider, str]:
    """
    Create a LoadSet processing agent with vLLM model and dynamic tools.

    Args:
        model: OpenAIModel configured for vLLM (if None, uses default vLLM setup)
        system_prompt: System prompt for the agent

    Returns:
        Configured Agent with LoadSet processing tools
    """
    if model is None:
        model = create_vllm_model()

    agent = Agent(
        model,
        deps_type=LoadSetMCPProvider,
        system_prompt=system_prompt,
    )

    # Dynamically register tools from LoadSetMCPProvider
    @agent.tool
    def load_from_json(ctx: RunContext[LoadSetMCPProvider], file_path: str) -> dict:
        """Load a LoadSet from a JSON file."""
        return ctx.deps.load_from_json(Path(file_path))

    @agent.tool
    def convert_units(ctx: RunContext[LoadSetMCPProvider], target_units: ForceUnit) -> dict:
        """Convert the current LoadSet to different units (N, kN, lbf, klbf)."""
        return ctx.deps.convert_units(target_units)

    @agent.tool
    def scale_loads(ctx: RunContext[LoadSetMCPProvider], factor: float) -> dict:
        """Scale all loads in the current LoadSet by a factor."""
        return ctx.deps.scale_loads(factor)

    @agent.tool
    def export_to_ansys(
        ctx: RunContext[LoadSetMCPProvider],
        folder_path: Optional[str] = None,
        name_stem: Optional[str] = None
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

    @agent.tool
    def load_second_loadset(ctx: RunContext[LoadSetMCPProvider], file_path: str) -> dict:
        """Load a second LoadSet from a JSON file for comparison."""
        return ctx.deps.load_second_loadset(Path(file_path))

    @agent.tool
    def export_comparison_report(
        ctx: RunContext[LoadSetMCPProvider],
        output_dir: str,
        report_name: str = "comparison_report",
        image_format: str = "png",
        indent: int = 2,
    ) -> dict:
        """Export complete comparison report including JSON data and chart images."""
        return ctx.deps.generate_comparison_report(output_dir=Path(output_dir))

    return agent


# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def run_agent(user_message: str, vllm_url: str = "http://localhost:8000/v1"):
    """
    Run the LoadSet processing agent with a user message.

    Args:
        user_message: The user's request/message
        vllm_url: URL of the vLLM server
    """
    print(f"Connecting to vLLM server at: {vllm_url}")
    print(f"User message: {user_message}\n")

    # Create vLLM model
    model = create_vllm_model(base_url=vllm_url)

    # Create agent
    agent = create_loadset_agent(model=model)

    # Create provider
    provider = LoadSetMCPProvider()

    # Run agent
    print("Processing request...\n")
    result = await agent.run(user_message, deps=provider)

    print("=" * 80)
    print("AGENT RESPONSE")
    print("=" * 80)
    print(result.output)

    return result.output


def main():
    """Main entry point for standalone execution."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Standalone LoadSet processing agent with vLLM"
    )
    parser.add_argument(
        "message",
        nargs="?",
        help="User message (if not provided, will prompt interactively)"
    )
    parser.add_argument(
        "--vllm-url",
        default="http://localhost:8000/v1",
        help="vLLM server URL (default: http://localhost:8000/v1)"
    )

    args = parser.parse_args()

    if args.message:
        user_message = args.message
    else:
        print("=" * 80)
        print("STANDALONE LOADSET PROCESSING AGENT")
        print("=" * 80)
        print("\nEnter your message (or 'quit' to exit):")
        user_message = input("> ").strip()

        if user_message.lower() in ["quit", "exit", "q"]:
            print("Exiting...")
            return

    if not user_message:
        print("Error: No message provided")
        return

    # Run the agent
    asyncio.run(run_agent(user_message, args.vllm_url))


if __name__ == "__main__":
    main()
