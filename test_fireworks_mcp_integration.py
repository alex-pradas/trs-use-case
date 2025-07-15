#!/usr/bin/env python3
"""
Test script for FIREWORKS AI integration with LoadSet MCP server.

This script tests that FIREWORKS AI can successfully interact with
the LoadSet MCP server to perform aerospace load processing tasks.
"""

import asyncio
import sys
import tempfile
import shutil
from pathlib import Path
from dotenv import load_dotenv

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent / "tools"))

from fireworks_mcp_agent import FireworksMCPAgent, FireworksPythonExecutionAgent
from fireworks_client import FireworksConfig
from mcps.loads_mcp_server import create_mcp_server, reset_global_state
from mcps.python_exec_mcp_server import create_mcp_server as create_python_mcp_server
from loads import LoadSet

# Load environment variables
load_dotenv()


async def test_fireworks_loadset_mcp_basic():
    """Test basic FIREWORKS interaction with LoadSet MCP server."""
    print("🔥 Testing FIREWORKS with LoadSet MCP Server...")

    # Reset global state and create MCP server
    reset_global_state()
    server = create_mcp_server()

    # Create FIREWORKS agent
    agent = FireworksMCPAgent(server)

    if not agent.is_configured():
        print("❌ FIREWORKS agent not configured")
        return False

    try:
        # Test basic prompt
        result = await agent.process_user_prompt(
            "Load the LoadSet from 'solution/loads/new_loads.json' and give me a summary."
        )

        if result["success"]:
            print("✅ Basic LoadSet MCP interaction successful!")
            print(f"📝 Response: {result['agent_response'][:200]}...")
            print(f"🎯 Model used: {result['model_used']}")
            return True
        else:
            print(f"❌ Basic interaction failed: {result['error']}")
            return False

    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False


async def test_fireworks_loadset_workflow():
    """Test complete LoadSet workflow with FIREWORKS."""
    print("\n🛠️ Testing FIREWORKS LoadSet workflow...")

    # Reset global state and create MCP server
    reset_global_state()
    server = create_mcp_server()

    # Create FIREWORKS agent
    agent = FireworksMCPAgent(server)

    if not agent.is_configured():
        print("❌ FIREWORKS agent not configured")
        return False

    # Create temporary output directory
    with tempfile.TemporaryDirectory() as temp_dir:
        output_folder = Path(temp_dir) / "ansys_output"

        try:
            # Test complete workflow
            result = await agent.load_and_process_workflow(
                json_path="solution/loads/new_loads.json",
                target_units="klbf",
                scale_factor=1.5,
                output_folder=str(output_folder),
            )

            if result["success"]:
                print("✅ LoadSet workflow successful!")
                print(f"📝 Response: {result['agent_response'][:300]}...")

                # Check if ANSYS files were created
                if output_folder.exists():
                    ansys_files = list(output_folder.glob("*.inp"))
                    print(f"📁 Created {len(ansys_files)} ANSYS files")

                    if len(ansys_files) > 0:
                        # Check one file content
                        sample_file = ansys_files[0]
                        content = sample_file.read_text()
                        if "f,all," in content:
                            print("✅ ANSYS file format verified")
                        else:
                            print("⚠️  ANSYS file format may be incorrect")
                else:
                    print("⚠️  No output files found")

                return True
            else:
                print(f"❌ Workflow failed: {result['error']}")
                return False

        except Exception as e:
            print(f"❌ Workflow test failed with exception: {e}")
            return False


async def test_fireworks_python_execution():
    """Test FIREWORKS with Python execution MCP server."""
    print("\n🐍 Testing FIREWORKS with Python execution...")

    # Create Python execution MCP server
    python_server = create_python_mcp_server()

    # Create FIREWORKS Python agent
    agent = FireworksPythonExecutionAgent(python_server)

    if not agent.is_configured():
        print("❌ FIREWORKS Python agent not configured")
        return False

    try:
        # Test code generation and execution
        challenge = """
        Create a simple LoadSet processing example:
        1. Create a mock LoadSet with some sample data
        2. Show how to convert units and scale loads
        3. Display the results
        
        Use Python code and execute it to demonstrate.
        """

        result = await agent.solve_programming_challenge(challenge)

        if result["success"]:
            print("✅ Python execution with FIREWORKS successful!")
            print(f"📝 Response: {result['agent_response'][:300]}...")
            print(f"🔧 Tool calls made: {result['tool_calls_count']}")
            print(f"🎯 Model used: {result['model_used']}")
            return True
        else:
            print(f"❌ Python execution failed: {result['error']}")
            return False

    except Exception as e:
        print(f"❌ Python execution test failed with exception: {e}")
        return False


async def test_fireworks_model_comparison():
    """Test different FIREWORKS models with MCP integration."""
    print("\n⚖️ Testing different FIREWORKS models with MCP...")

    models_to_test = [
        ("Llama 3.3 70B", FireworksConfig.LLAMA_3_3_70B_INSTRUCT),
        ("Llama 3.1 70B", FireworksConfig.LLAMA_3_1_70B_INSTRUCT),
    ]

    prompt = "Load 'solution/loads/new_loads.json' and tell me how many load cases it contains."

    results = {}
    for model_name, model_id in models_to_test:
        # Reset global state and create MCP server
        reset_global_state()
        server = create_mcp_server()

        try:
            agent = FireworksMCPAgent(server, model_name=model_id)

            if agent.is_configured():
                result = await agent.process_user_prompt(prompt)

                if result["success"]:
                    response_length = len(result["agent_response"])
                    results[model_name] = {"success": True, "length": response_length}
                    print(f"✅ {model_name}: {response_length} characters")
                else:
                    results[model_name] = {"success": False, "error": result["error"]}
                    print(f"❌ {model_name}: {result['error']}")
            else:
                results[model_name] = {
                    "success": False,
                    "error": "Agent not configured",
                }
                print(f"❌ {model_name}: Agent not configured")

        except Exception as e:
            results[model_name] = {"success": False, "error": str(e)}
            print(f"❌ {model_name}: {e}")

    print(f"\n📊 Model comparison results:")
    for model, result in results.items():
        status = "✅" if result["success"] else "❌"
        if result["success"]:
            print(f"  {status} {model}: {result['length']} characters")
        else:
            print(f"  {status} {model}: {result['error']}")

    return any(r["success"] for r in results.values())


async def test_fireworks_vs_anthropic_comparison():
    """Compare FIREWORKS performance with existing Anthropic integration."""
    print("\n🥊 Testing FIREWORKS vs Anthropic (if available)...")

    # Test with FIREWORKS
    reset_global_state()
    server = create_mcp_server()
    fireworks_agent = FireworksMCPAgent(server)

    prompt = "Load 'solution/loads/new_loads.json' and convert units to kN. Give me a summary."

    fireworks_result = None
    anthropic_result = None

    # Test FIREWORKS
    if fireworks_agent.is_configured():
        try:
            fireworks_result = await fireworks_agent.process_user_prompt(prompt)
            if fireworks_result["success"]:
                print(
                    f"✅ FIREWORKS: {len(fireworks_result['agent_response'])} characters"
                )
            else:
                print(f"❌ FIREWORKS: {fireworks_result['error']}")
        except Exception as e:
            print(f"❌ FIREWORKS failed: {e}")

    # Test Anthropic (if available)
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            from tests.agents.test_ai_agent_integration import AnthropicMCPTestAgent

            reset_global_state()
            server = create_mcp_server()
            anthropic_agent = AnthropicMCPTestAgent(server)

            if anthropic_agent.agent:
                anthropic_result = await anthropic_agent.process_user_prompt(prompt)
                if anthropic_result["success"]:
                    print(
                        f"✅ Anthropic: {len(anthropic_result['agent_response'])} characters"
                    )
                else:
                    print(f"❌ Anthropic: {anthropic_result['error']}")
        except Exception as e:
            print(f"❌ Anthropic test failed: {e}")
    else:
        print("⚠️  Anthropic API key not available for comparison")

    # Compare results
    if fireworks_result and fireworks_result["success"]:
        print("🔥 FIREWORKS integration working successfully!")
        if anthropic_result and anthropic_result["success"]:
            print("📊 Both FIREWORKS and Anthropic working - you have options!")
        return True
    else:
        print("❌ FIREWORKS integration needs work")
        return False


async def main():
    """Run all FIREWORKS MCP integration tests."""
    print("🔥 FIREWORKS AI MCP Integration Test Suite")
    print("=" * 60)

    # Check configuration first
    if not FireworksConfig.is_configured():
        print("❌ FIREWORKS_API_KEY not found in environment")
        print("   Please add FIREWORKS_API_KEY to your .env file")
        return False

    print(f"✅ FIREWORKS_API_KEY configured")
    print(f"🎯 Default model: {FireworksConfig.DEFAULT_CODE_MODEL}")

    # Run all tests
    tests = [
        ("LoadSet MCP Basic", test_fireworks_loadset_mcp_basic),
        ("LoadSet Workflow", test_fireworks_loadset_workflow),
        ("Python Execution", test_fireworks_python_execution),
        ("Model Comparison", test_fireworks_model_comparison),
        ("FIREWORKS vs Anthropic", test_fireworks_vs_anthropic_comparison),
    ]

    results = {}
    for test_name, test_func in tests:
        print(f"\n{'=' * 20} {test_name} {'=' * 20}")
        try:
            results[test_name] = await test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False

    # Summary
    print(f"\n{'=' * 60}")
    print("🏁 Test Summary")
    print("=" * 60)

    passed = sum(1 for success in results.values() if success)
    total = len(results)

    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} {test_name}")

    print(f"\n📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! FIREWORKS MCP integration is working correctly.")
        print("🔥 FIREWORKS AI is ready as an alternative to Anthropic!")
        return True
    elif passed > 0:
        print("⚠️  Some tests passed. FIREWORKS integration is partially working.")
        return True
    else:
        print("❌ All tests failed. Check configuration and try again.")
        return False


if __name__ == "__main__":
    import os

    success = asyncio.run(main())
    sys.exit(0 if success else 1)
