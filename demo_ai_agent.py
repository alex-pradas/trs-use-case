#!/usr/bin/env python3
"""
Demo script showing AI agent integration with MCP server.

This script demonstrates how an AI agent can process the exact user request:
"Please help me process the loads in solution/loads/new_loads.json.
Factor by 1.5 and convert to klbs. Generate files for ansys in a subfolder called output."
"""

import asyncio
import os
import tempfile
import shutil
from pathlib import Path
from dotenv import load_dotenv

from tests.test_ai_agent_integration import AnthropicMCPTestAgent
from tools.mcp_server import create_mcp_server, reset_global_state

# Load environment variables
load_dotenv()


async def main():
    """Run the AI agent demo with the exact user prompt."""
    print("🤖 AI Agent Integration Demo")
    print("=" * 50)

    # Setup
    reset_global_state()
    server = create_mcp_server()
    agent = AnthropicMCPTestAgent(server)

    # Create output folder
    output_folder = Path("output")
    output_folder.mkdir(exist_ok=True)

    try:
        # The exact user prompt
        user_prompt = """Please help me process the loads in solution/loads/new_loads.json. 
Factor by 1.5 and convert to klbs. Generate files for ansys in a subfolder called output."""

        print(f"📝 User prompt: {user_prompt}")
        print("\n🔄 Processing...")

        # Process the user request
        result = await agent.process_user_prompt(user_prompt)

        if result["success"]:
            print("\n✅ SUCCESS!")
            print(f"🤖 Agent response: {result['agent_response']}")

            # Show generated files
            ansys_files = list(output_folder.glob("*.inp"))
            print(f"\n📊 Generated {len(ansys_files)} ANSYS files:")
            for i, file in enumerate(ansys_files[:5]):  # Show first 5
                print(f"  - {file.name}")
            if len(ansys_files) > 5:
                print(f"  ... and {len(ansys_files) - 5} more files")

            # Show a sample of file content
            if ansys_files:
                sample_file = ansys_files[0]
                content = sample_file.read_text()
                print(f"\n📄 Sample content from {sample_file.name}:")
                print(content[:300] + "..." if len(content) > 300 else content)

        else:
            print(f"❌ FAILED: {result.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"❌ Demo failed: {e}")

    finally:
        # Cleanup
        if output_folder.exists():
            shutil.rmtree(output_folder)
        reset_global_state()

    print("\n🎉 Demo completed!")


if __name__ == "__main__":
    # Check if API key is available
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY not found in environment variables")
        print("Please set your Anthropic API key in the .env file")
        exit(1)

    asyncio.run(main())
