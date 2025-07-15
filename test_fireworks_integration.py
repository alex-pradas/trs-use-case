#!/usr/bin/env python3
"""
Test script for FIREWORKS AI integration with pydantic-ai.

This script tests basic connectivity, code generation, and integration
with existing tools to verify FIREWORKS AI works as an alternative to Anthropic.
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent / "tools"))

from fireworks_client import (
    FireworksConfig, 
    create_fireworks_agent, 
    create_code_generation_agent,
    get_code_generation_model
)

# Load environment variables
load_dotenv()


async def test_basic_connection():
    """Test basic FIREWORKS connection and simple text generation."""
    print("🔥 Testing basic FIREWORKS connection...")
    
    try:
        agent = create_fireworks_agent(
            system_prompt="You are a helpful assistant. Respond concisely and clearly."
        )
        
        result = await agent.run("Hello! Can you tell me what 2+2 equals?")
        print(f"✅ Basic connection successful!")
        print(f"📝 Response: {result.output}")
        return True
        
    except Exception as e:
        print(f"❌ Basic connection failed: {e}")
        return False


async def test_code_generation():
    """Test code generation capabilities with FIREWORKS."""
    print("\n🐍 Testing code generation capabilities...")
    
    try:
        agent = create_code_generation_agent()
        
        prompt = """
        Write a Python function that calculates the factorial of a number using recursion.
        Include proper type hints, docstring, and error handling for negative numbers.
        Also provide a simple test to demonstrate it works.
        """
        
        result = await agent.run(prompt)
        print(f"✅ Code generation successful!")
        print(f"📝 Generated code:\n{result.output}")
        return True
        
    except Exception as e:
        print(f"❌ Code generation failed: {e}")
        return False


async def test_loadset_knowledge():
    """Test if FIREWORKS can understand and work with LoadSet concepts."""
    print("\n📊 Testing LoadSet domain knowledge...")
    
    try:
        agent = create_fireworks_agent(
            system_prompt="""
            You are an aerospace engineering assistant with knowledge of structural loads.
            You understand LoadSet data structures, force/moment components (fx, fy, fz, mx, my, mz),
            unit conversions (N, kN, lbf, klbf), and ANSYS export formats.
            """
        )
        
        prompt = """
        Explain what a LoadSet is in aerospace structural analysis, and describe 
        the key components of a point load including force and moment components.
        Also explain why unit conversion is important when exporting to ANSYS.
        Keep your answer concise but technical.
        """
        
        result = await agent.run(prompt)
        print(f"✅ LoadSet knowledge test successful!")
        print(f"📝 Response: {result.output}")
        return True
        
    except Exception as e:
        print(f"❌ LoadSet knowledge test failed: {e}")
        return False


async def test_python_script_generation():
    """Test generating a complete Python script for LoadSet operations."""
    print("\n🛠️ Testing Python script generation for LoadSet operations...")
    
    try:
        agent = create_code_generation_agent()
        
        prompt = """
        Write a Python script that:
        1. Loads a LoadSet from a JSON file
        2. Converts the units from N to kN
        3. Scales all loads by a factor of 1.5
        4. Prints a summary of the processed data
        
        Assume the LoadSet class has methods:
        - LoadSet.read_json(file_path) 
        - loadset.convert_to(units)
        - loadset.factor(scale_factor)
        - Properties: name, units.forces, units.moments, load_cases
        
        Include proper imports and error handling.
        """
        
        result = await agent.run(prompt)
        print(f"✅ Python script generation successful!")
        print(f"📝 Generated script:\n{result.output}")
        return True
        
    except Exception as e:
        print(f"❌ Python script generation failed: {e}")
        return False


async def test_model_comparison():
    """Test different FIREWORKS models and compare responses."""
    print("\n⚖️ Testing different FIREWORKS models...")
    
    models_to_test = [
        ("Llama 3.3 70B", FireworksConfig.LLAMA_3_3_70B_INSTRUCT),
        ("Llama 3.1 70B", FireworksConfig.LLAMA_3_1_70B_INSTRUCT),
        ("Llama 3 70B", FireworksConfig.LLAMA_3_70B_INSTRUCT),
    ]
    
    prompt = "Write a Python function to calculate the Fibonacci sequence up to n terms."
    
    results = {}
    for model_name, model_id in models_to_test:
        try:
            agent = create_fireworks_agent(
                system_prompt="You are a Python programming expert. Write clean, efficient code.",
                model_name=model_id
            )
            
            result = await agent.run(prompt)
            results[model_name] = {"success": True, "length": len(result.output)}
            print(f"✅ {model_name}: {len(result.output)} characters")
            
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


async def main():
    """Run all FIREWORKS integration tests."""
    print("🔥 FIREWORKS AI Integration Test Suite")
    print("=" * 50)
    
    # Check configuration first
    if not FireworksConfig.is_configured():
        print("❌ FIREWORKS_API_KEY not found in environment")
        print("   Please add FIREWORKS_API_KEY to your .env file")
        return False
    
    print(f"✅ FIREWORKS_API_KEY configured")
    print(f"🎯 Default model: {FireworksConfig.DEFAULT_CODE_MODEL}")
    
    # Run all tests
    tests = [
        ("Basic Connection", test_basic_connection),
        ("Code Generation", test_code_generation),
        ("LoadSet Knowledge", test_loadset_knowledge), 
        ("Script Generation", test_python_script_generation),
        ("Model Comparison", test_model_comparison),
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = await test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*50}")
    print("🏁 Test Summary")
    print("=" * 50)
    
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! FIREWORKS integration is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)