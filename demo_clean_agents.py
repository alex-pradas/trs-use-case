#!/usr/bin/env python3
"""
Demo of the new clean pydantic-ai agent architecture.

This script demonstrates how simple and elegant the new agent API is:
- Single environment variable controls model choice
- Global agents with zero boilerplate 
- Clean tool registration with decorators
- Provider-independent MCP integration
"""

import asyncio
import sys
import os
from pathlib import Path
from pydantic_ai.settings import ModelSettings

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent / "tools"))

from agents import loadset_agent, python_agent, script_agent
from model_config import get_model_name, get_provider_name, validate_model_config


async def demo_loadset_agent():
    """Demonstrate LoadSet agent with clean pydantic-ai patterns."""
    print("🔧 LoadSet Agent Demo")
    print("-" * 30)
    
    # Simple agent usage - no custom classes needed!
    result = await loadset_agent.run(
        """
        Load the LoadSet from 'solution/loads/new_loads.json' and:
        1. Give me a summary of the data
        2. Convert units to kN
        3. Scale loads by factor 1.2
        4. Export to ANSYS format in folder 'demo_clean_output'
        """,
        model_settings=ModelSettings(temperature=0.1)  # Optional settings
    )
    
    print(f"✅ Result: {result.output}")
    return True


async def demo_python_agent():
    """Demonstrate Python execution agent."""
    print("\n🐍 Python Agent Demo")
    print("-" * 30)
    
    result = await python_agent.run(
        """
        Create a simple LoadSet processing example:
        1. Load the LoadSet from 'solution/loads/new_loads.json'
        2. Show the original units and total number of load cases
        3. Convert to klbf units and show a sample force value
        4. Calculate the scaling factor needed to double all forces
        """,
        model_settings=ModelSettings(temperature=0.2)
    )
    
    print(f"✅ Result: {result.output}")
    return True


async def demo_script_agent():
    """Demonstrate script generation and execution agent."""
    print("\n📜 Script Agent Demo")
    print("-" * 30)
    
    result = await script_agent.run(
        """
        Generate and execute a Python script that:
        1. Loads the LoadSet from 'solution/loads/new_loads.json'
        2. Analyzes the data and creates a summary report
        3. Converts units to different systems (N, kN, lbf)
        4. Saves the analysis results to a JSON file called 'analysis_report.json'
        
        The script should be complete and self-contained.
        """,
        model_settings=ModelSettings(temperature=0.3)
    )
    
    print(f"✅ Result: {result.output}")
    return True


async def demo_provider_switching():
    """Demonstrate how easy it is to switch providers."""
    print("\n🔄 Provider Switching Demo")
    print("-" * 30)
    
    current_model = get_model_name()
    provider = get_provider_name()
    
    print(f"Current model: {current_model}")
    print(f"Provider: {provider}")
    
    print("\n💡 To switch providers, just change the AI_MODEL environment variable:")
    print("   export AI_MODEL='anthropic:claude-3-5-sonnet-latest'")
    print("   export AI_MODEL='fireworks:accounts/fireworks/models/llama-v3p3-70b-instruct'")
    print("   export AI_MODEL='openai:gpt-4o'")
    print("\nNo code changes needed - the same agents work with any provider!")
    
    return True


async def main():
    """Run the clean agent demonstrations."""
    print("🚀 Clean Pydantic-AI Agent Architecture Demo")
    print("=" * 60)
    print("This demo shows the new simplified agent architecture:")
    print("• 90% less boilerplate code")
    print("• Single environment variable for model selection")
    print("• Provider-independent MCP integration")
    print("• Global agents following pydantic-ai best practices")
    print("=" * 60)
    
    # Validate configuration
    is_valid, error = validate_model_config()
    if not is_valid:
        print(f"❌ Configuration error: {error}")
        print("Please set the appropriate API key for your chosen model.")
        return False
    
    print(f"✅ Using model: {get_model_name()}")
    print(f"✅ Provider: {get_provider_name()}")
    
    # Run demos
    demos = [
        ("LoadSet Processing", demo_loadset_agent),
        ("Python Execution", demo_python_agent),
        ("Script Generation", demo_script_agent),
        ("Provider Switching", demo_provider_switching),
    ]
    
    results = {}
    for demo_name, demo_func in demos:
        print(f"\n{'='*20} {demo_name} {'='*20}")
        try:
            results[demo_name] = await demo_func()
        except Exception as e:
            print(f"❌ Demo '{demo_name}' failed: {e}")
            results[demo_name] = False
    
    # Summary
    print(f"\n{'='*60}")
    print("🏁 Demo Summary")
    print("=" * 60)
    
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    for demo_name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {status} {demo_name}")
    
    print(f"\n📊 Results: {passed}/{total} demos successful")
    
    if passed == total:
        print("🎉 All demos successful! Clean agent architecture is working perfectly.")
    else:
        print("⚠️  Some demos had issues. Check error messages above.")
    
    print("\n💪 Benefits of the new architecture:")
    print("   • Zero boilerplate - just use global agents directly")
    print("   • Provider agnostic - change AI_MODEL env var to switch")
    print("   • Follows pydantic-ai best practices exactly")
    print("   • MCP integration is clean and separate from LLM choice")
    print("   • Easy to extend with new tools and providers")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)