#!/usr/bin/env python3
"""
Demo script showcasing FIREWORKS AI integration with LoadSet MCP server.

This script demonstrates how to use FIREWORKS AI as an alternative to Anthropic
for aerospace load data processing tasks.
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent / "tools"))

from fireworks_mcp_agent import FireworksMCPAgent
from fireworks_client import FireworksConfig, list_available_models
from mcps.loads_mcp_server import create_mcp_server, reset_global_state

# Load environment variables
load_dotenv()


async def demo_basic_loadset_operations():
    """Demonstrate basic LoadSet operations using FIREWORKS AI."""
    print("🔥 FIREWORKS AI LoadSet Demo")
    print("=" * 50)

    # Check configuration
    if not FireworksConfig.is_configured():
        print("❌ FIREWORKS_API_KEY not found in environment")
        print("   Please add FIREWORKS_API_KEY to your .env file")
        return False

    print(f"✅ Using model: {FireworksConfig.DEFAULT_CODE_MODEL}")

    # Create MCP server and agent
    reset_global_state()
    server = create_mcp_server()
    agent = FireworksMCPAgent(server)

    if not agent.is_configured():
        print("❌ Failed to create FIREWORKS agent")
        return False

    # Demo 1: Load and summarize data
    print("\n📊 Demo 1: Load and summarize aerospace load data")
    print("-" * 50)

    result = await agent.process_user_prompt("""
    Load the LoadSet from 'solution/loads/new_loads.json' and provide:
    1. A summary of the LoadSet (name, units, number of load cases)
    2. List the names of all load cases
    3. Tell me about the force and moment units used
    """)

    if result["success"]:
        print("✅ LoadSet loaded and analyzed successfully!")
        print(f"Response: {result['agent_response']}")
    else:
        print(f"❌ Failed: {result['error']}")
        return False

    # Demo 2: Unit conversion and scaling
    print("\n🔧 Demo 2: Convert units and scale loads")
    print("-" * 50)

    result = await agent.process_user_prompt("""
    Now please:
    1. Convert the LoadSet units from the current units to kN (kilonewtons)
    2. Scale all loads by a factor of 1.25
    3. Give me a summary of the transformed LoadSet
    """)

    if result["success"]:
        print("✅ LoadSet transformed successfully!")
        print(f"Response: {result['agent_response']}")
    else:
        print(f"❌ Failed: {result['error']}")
        return False

    # Demo 3: Export to ANSYS
    print("\n📁 Demo 3: Export to ANSYS format")
    print("-" * 50)

    result = await agent.process_user_prompt("""
    Export the current LoadSet to ANSYS format files:
    1. Create files in a folder called 'demo_output'
    2. Use 'fireworks_demo' as the name stem
    3. Tell me how many files were created and give examples of the content format
    """)

    if result["success"]:
        print("✅ ANSYS export successful!")
        print(f"Response: {result['agent_response']}")

        # Check if files were actually created
        output_dir = Path("demo_output")
        if output_dir.exists():
            ansys_files = list(output_dir.glob("*.inp"))
            print(f"📁 Verified: {len(ansys_files)} ANSYS files created")

            # Show content of first file
            if ansys_files:
                first_file = ansys_files[0]
                content = first_file.read_text()
                lines = content.split("\n")[:5]  # First 5 lines
                print(f"📄 Sample content from {first_file.name}:")
                for line in lines:
                    if line.strip():
                        print(f"   {line}")
        else:
            print("⚠️  No output directory found")
    else:
        print(f"❌ Failed: {result['error']}")
        return False

    return True


async def demo_model_comparison():
    """Compare different FIREWORKS models on the same task."""
    print("\n⚖️ Model Comparison Demo")
    print("=" * 50)

    task = "Load 'solution/loads/new_loads.json' and tell me how many load cases it contains."

    available_models = list_available_models()

    for model_key, model_info in available_models.items():
        print(f"\n🧠 Testing {model_info['description']}")
        print("-" * 30)

        # Create fresh server and agent for each model
        reset_global_state()
        server = create_mcp_server()
        agent = FireworksMCPAgent(server, model_name=model_info["name"])

        if agent.is_configured():
            try:
                result = await agent.process_user_prompt(task)

                if result["success"]:
                    print(f"✅ Response: {result['agent_response']}")
                    print(
                        f"📊 Response length: {len(result['agent_response'])} characters"
                    )
                else:
                    print(f"❌ Failed: {result['error']}")

            except Exception as e:
                print(f"❌ Exception: {e}")
        else:
            print("❌ Agent not configured")


async def demo_code_generation():
    """Demonstrate FIREWORKS code generation capabilities."""
    print("\n🐍 Code Generation Demo")
    print("=" * 50)

    # Create fresh server and agent
    reset_global_state()
    server = create_mcp_server()
    agent = FireworksMCPAgent(server)

    if not agent.is_configured():
        print("❌ Agent not configured")
        return False

    result = await agent.process_user_prompt("""
    I need you to help me understand the LoadSet workflow. Can you:
    
    1. Load the LoadSet from 'solution/loads/new_loads.json'
    2. Show me the basic structure and properties available
    3. Explain what each component represents in aerospace engineering terms
    4. Give me practical advice on when to use unit conversion vs scaling
    """)

    if result["success"]:
        print("✅ LoadSet analysis completed!")
        print(f"Response: {result['agent_response']}")
        return True
    else:
        print(f"❌ Failed: {result['error']}")
        return False


async def main():
    """Run the FIREWORKS AI demonstration."""
    print("🔥 FIREWORKS AI for Aerospace Load Processing")
    print("=" * 60)
    print("This demo showcases FIREWORKS AI as an alternative to Anthropic")
    print("for aerospace structural load data processing using MCP servers.")
    print("=" * 60)

    # Run all demos
    demos = [
        ("Basic LoadSet Operations", demo_basic_loadset_operations),
        ("Model Comparison", demo_model_comparison),
        ("Code Generation & Analysis", demo_code_generation),
    ]

    results = {}
    for demo_name, demo_func in demos:
        print(f"\n🎬 Running: {demo_name}")
        try:
            results[demo_name] = await demo_func()
        except Exception as e:
            print(f"❌ Demo '{demo_name}' failed with exception: {e}")
            results[demo_name] = False

    # Summary
    print(f"\n{'=' * 60}")
    print("🏁 Demo Summary")
    print("=" * 60)

    for demo_name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {status} {demo_name}")

    successful_demos = sum(1 for success in results.values() if success)
    total_demos = len(results)

    print(f"\n📊 Results: {successful_demos}/{total_demos} demos successful")

    if successful_demos == total_demos:
        print(
            "🎉 All demos successful! FIREWORKS AI is ready for aerospace load processing."
        )
    elif successful_demos > 0:
        print(
            "⚠️  Some demos successful. FIREWORKS integration is working but may need refinement."
        )
    else:
        print("❌ No demos successful. Check your FIREWORKS_API_KEY configuration.")

    print("\n🔥 FIREWORKS AI offers:")
    print("   • Fast inference with competitive quality")
    print("   • Cost-effective alternative to Anthropic")
    print("   • Drop-in replacement for existing workflows")
    print("   • Specialized models for coding and reasoning")


if __name__ == "__main__":
    asyncio.run(main())
