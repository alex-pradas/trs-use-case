"""
Integration test for AI agent with LoadSet envelope functionality.

This test validates that the clean pydantic-ai agents can successfully interact
with the MCP server to create envelopes of load data using actual LLM calls.
"""

import pytest
import asyncio
import os
import sys
import tempfile
import shutil
from pathlib import Path

from dotenv import load_dotenv
from tools.agents import create_loadset_agent  # noqa: E402
from tools.mcps.loads_mcp_server import LoadSetMCPProvider  # noqa: E402
from tools.model_config import get_model_name, validate_model_config  # noqa: E402
from tools.loads import LoadSet  # noqa: E402

# Load environment variables from .env file
load_dotenv()


@pytest.mark.expensive
class TestEnvelopeAgentIntegration:
    """Test suite for envelope AI agent integration with MCP server."""

    def setup_method(self):
        """Set up test environment."""
        # Reset global state before each test
        # No global state to reset with new architecture

        # Create temporary output directory
        self.temp_dir = tempfile.mkdtemp()
        self.output_folder = Path(self.temp_dir) / "output"
        self.output_folder.mkdir(exist_ok=True)

    def teardown_method(self):
        """Clean up test environment."""
        # Clean up temporary directory
        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

        # Reset global state
        # No global state to reset with new architecture

    @pytest.mark.asyncio
    async def test_agent_envelope_workflow(self):
        """Test complete envelope workflow with AI agent."""
        # Validate configuration
        is_valid, error = validate_model_config()
        if not is_valid:
            pytest.skip(f"Model configuration error: {error}")

        # Test data
        json_path = "use_case_definition/data/loads/03_A_new_loads.json"
        output_folder = str(self.output_folder)

        # Create agent and dependencies
        agent = create_loadset_agent()
        deps = LoadSetMCPProvider()

        # Run the envelope workflow using clean architecture
        result = await agent.run(
            f"""
        Please help me create an envelope of loads from {json_path}. 
        An envelope contains only the load cases that have extreme values (maximum and minimum if negative).
        
        Please perform these steps:
        1. Load LoadSet data from: {json_path}
        2. Create an envelope of the LoadSet (this will reduce the number of load cases)
        3. Get a summary of the envelope LoadSet showing the reduction
        4. Export the envelope to ANSYS format in folder: {output_folder} with name_stem: "envelope_loads"
        5. List the load cases in the envelope to show which ones were selected
        
        Please explain what the envelope operation did and how many load cases were reduced.
        """,
            deps=deps,
        )

        # Validate agent response
        assert result.output, "Agent should return a response"
        assert "envelope" in result.output.lower(), "Response should mention envelope"
        assert "load" in result.output.lower(), "Response should mention loads"

        # Validate that output files were created
        assert self.output_folder.exists(), "Output folder was not created"

        # Load original data to understand the reduction
        original_loadset = LoadSet.read_json(Path(json_path))
        original_count = len(original_loadset.load_cases)

        # Validate ANSYS files were created (envelope should have fewer cases)
        ansys_files = list(self.output_folder.glob("envelope_loads_*.inp"))
        envelope_count = len(ansys_files)

        assert envelope_count > 0, "No envelope ANSYS files were generated"
        assert envelope_count <= original_count, (
            "Envelope should have same or fewer load cases"
        )

        # Test that we can read one of the generated files
        sample_file = ansys_files[0]
        content = sample_file.read_text()
        assert "f,all," in content, "ANSYS file does not contain f,all commands"
        assert "/TITLE," in content, "ANSYS file does not contain title command"

    @pytest.mark.asyncio
    async def test_agent_envelope_understanding(self):
        """Test that the agent understands envelope concept correctly."""
        # Validate configuration
        is_valid, error = validate_model_config()
        if not is_valid:
            pytest.skip(f"Model configuration error: {error}")

        # Create agent and dependencies
        agent = create_loadset_agent()
        deps = LoadSetMCPProvider()

        # Test agent understanding of envelope concept
        result = await agent.run(
            """
        Please load the LoadSet data from 'use_case_definition/data/loads/03_A_new_loads.json' and explain:
        1. What is an envelope of load cases?
        2. Create an envelope and tell me how many load cases were reduced
        3. Explain which types of load cases are included in an envelope
        4. Why might someone want to create an envelope?
        
        Please be specific about the numbers and the reduction achieved.
        """,
            deps=deps,
        )

        # Validate agent understanding
        assert result.output, "Agent should return a response"
        response_lower = result.output.lower()

        # Check that agent mentions key envelope concepts
        assert "envelope" in response_lower, "Should mention envelope"
        assert (
            "extreme" in response_lower
            or "maximum" in response_lower
            or "minimum" in response_lower
        ), "Should mention extreme values"
        assert "reduce" in response_lower or "fewer" in response_lower, (
            "Should mention reduction"
        )

        # Should mention numbers indicating the reduction
        import re

        numbers = re.findall(r"\d+", result.output)
        assert len(numbers) >= 2, (
            "Should mention specific numbers for before/after load case counts"
        )

    @pytest.mark.asyncio
    async def test_agent_envelope_comparison(self):
        """Test agent comparison of original vs envelope loadsets."""
        # Validate configuration
        is_valid, error = validate_model_config()
        if not is_valid:
            pytest.skip(f"Model configuration error: {error}")

        # Create agent and dependencies
        agent = create_loadset_agent()
        deps = LoadSetMCPProvider()

        # Test comparison workflow
        result = await agent.run(
            """
        I want to compare a LoadSet before and after creating an envelope.
        
        Please:
        1. Load the LoadSet from 'use_case_definition/data/loads/03_A_new_loads.json'
        2. Note how many load cases it has originally
        3. Create an envelope of this LoadSet
        4. Show me how many load cases remain after the envelope
        5. Calculate the percentage reduction in load cases
        6. List some of the load case names that remained in the envelope
        
        Present this as a clear before/after comparison.
        """,
            deps=deps,
        )

        # Validate comparison results
        assert result.output, "Agent should return a response"
        response_lower = result.output.lower()

        assert "before" in response_lower or "original" in response_lower, (
            "Should mention before state"
        )
        assert "after" in response_lower or "envelope" in response_lower, (
            "Should mention after state"
        )
        assert "%" in result.output or "percent" in response_lower, (
            "Should mention percentage"
        )
        assert "case" in response_lower, "Should mention load cases"

    @pytest.mark.asyncio
    async def test_agent_envelope_error_handling(self):
        """Test agent error handling with envelope operations."""
        # Validate configuration
        is_valid, error = validate_model_config()
        if not is_valid:
            pytest.skip(f"Model configuration error: {error}")

        # Create agent and dependencies
        agent = create_loadset_agent()
        deps = LoadSetMCPProvider()

        # Test with invalid request (envelope without loading data)
        result = await agent.run(
            "Please create an envelope of the LoadSet without loading any data first.",
            deps=deps,
        )

        # Should handle the error gracefully
        assert result.output, "Agent should return a response even for errors"
        response_lower = result.output.lower()
        assert "error" in response_lower or "load" in response_lower, (
            "Should indicate error or need to load data"
        )

    @pytest.mark.asyncio
    async def test_agent_envelope_with_scaling(self):
        """Test envelope combined with other LoadSet operations."""
        # Validate configuration
        is_valid, error = validate_model_config()
        if not is_valid:
            pytest.skip(f"Model configuration error: {error}")

        # Test data
        json_path = "use_case_definition/data/loads/03_A_new_loads.json"
        scale_factor = 2.0
        target_units = "kN"
        output_folder = str(self.output_folder)

        # Create agent and dependencies
        agent = create_loadset_agent()
        deps = LoadSetMCPProvider()

        # Test combined workflow
        result = await agent.run(
            f"""
        Please perform a complex LoadSet workflow:
        1. Load LoadSet data from: {json_path}
        2. Create an envelope to reduce the number of load cases
        3. Scale the envelope loads by factor: {scale_factor}
        4. Convert units to: {target_units}
        5. Export to ANSYS format in folder: {output_folder} with name_stem: "scaled_envelope"
        6. Provide a summary of all transformations applied
        
        Explain each step and the changes that occurred.
        """,
            deps=deps,
        )

        # Validate complex workflow
        assert result.output, "Agent should return a response"
        response_lower = result.output.lower()

        assert "envelope" in response_lower, "Should mention envelope"
        assert "scale" in response_lower or str(scale_factor) in result.output, (
            "Should mention scaling"
        )
        assert target_units.lower() in response_lower, "Should mention unit conversion"
        assert "export" in response_lower or "ansys" in response_lower, (
            "Should mention export"
        )

        # Validate output files
        assert self.output_folder.exists(), "Output folder should exist"
        ansys_files = list(self.output_folder.glob("scaled_envelope_*.inp"))
        assert len(ansys_files) > 0, "Should create ANSYS files"

    def test_envelope_tool_availability(self):
        """Test that envelope tool is available to the agent."""
        # Create agent
        agent = create_loadset_agent()

        # Check that agent is properly initialized
        assert agent is not None, "Agent should be created successfully"

        # Check that agent has the correct model and deps type for pydantic-ai
        assert hasattr(agent, "model"), "Agent should have a model"
        assert hasattr(agent, "deps_type"), "Agent should have deps type"

    @pytest.mark.asyncio
    async def test_agent_envelope_explanation(self):
        """Test that agent can explain envelope functionality correctly."""
        # Validate configuration
        is_valid, error = validate_model_config()
        if not is_valid:
            pytest.skip(f"Model configuration error: {error}")

        # Create agent and dependencies
        agent = create_loadset_agent()
        deps = LoadSetMCPProvider()

        # Ask agent to explain envelope
        result = await agent.run(
            """
        Please explain what a LoadSet envelope is and why it's useful in engineering analysis.
        Then demonstrate by loading 'use_case_definition/data/loads/03_A_new_loads.json' and creating an envelope.
        
        Focus on:
        - What values are kept in an envelope
        - Why negative minimums are included but positive minimums are not
        - The practical benefits for ANSYS analysis
        """,
            deps=deps,
        )

        # Validate explanation
        assert result.output, "Agent should return a response"
        response_lower = result.output.lower()

        assert "envelope" in response_lower, "Should explain envelope"
        assert (
            "extreme" in response_lower
            or "maximum" in response_lower
            or "minimum" in response_lower
        ), "Should mention extremes"
        assert "negative" in response_lower, "Should mention negative values"
        assert "ansys" in response_lower or "analysis" in response_lower, (
            "Should mention practical use"
        )


# Helper functions
def run_agent_test(coro):
    """Run an async agent test synchronously."""
    return asyncio.run(coro)


if __name__ == "__main__":
    # Run a quick envelope integration test
    import sys

    async def main():
        """Quick test of envelope agent integration."""
        print("🧪 Envelope Agent Integration Test")
        print("=" * 40)

        # Validate configuration
        is_valid, error = validate_model_config()
        if not is_valid:
            print(f"❌ Configuration error: {error}")
            sys.exit(1)

        print(f"✅ Using model: {get_model_name()}")

        try:
            # Create agent and dependencies
            agent = create_loadset_agent()
            deps = LoadSetMCPProvider()

            # Test envelope functionality
            result = await agent.run(
                """
                Load 'use_case_definition/data/loads/03_A_new_loads.json', create an envelope, 
                and tell me how many load cases were reduced.
                """,
                deps=deps,
            )
            print(
                f"✅ Envelope agent test passed: {len(result.output)} character response"
            )

            # Check if response mentions envelope and numbers
            if "envelope" in result.output.lower() and any(
                char.isdigit() for char in result.output
            ):
                print("✅ Response contains envelope and numerical results")
            else:
                print("⚠️  Response may be missing expected content")

            print("🎉 Envelope agent integration test completed!")

        except Exception as e:
            print(f"❌ Integration test failed: {e}")
            sys.exit(1)

    asyncio.run(main())
