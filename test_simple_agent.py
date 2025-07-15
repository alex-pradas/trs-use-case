#!/usr/bin/env python3
"""
Simple test of the new clean agent architecture.
"""

import asyncio
import sys
from pathlib import Path

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent / "tools"))

from agents import loadset_agent
from model_config import get_model_name, validate_model_config


async def simple_test():
    """Test the basic loadset agent functionality."""
    print("🧪 Simple Agent Test")
    print("=" * 30)
    
    # Validate configuration
    is_valid, error = validate_model_config()
    if not is_valid:
        print(f"❌ Configuration error: {error}")
        return False
    
    print(f"✅ Using model: {get_model_name()}")
    
    # Simple test - just load a LoadSet
    try:
        result = await loadset_agent.run(
            "Load the LoadSet from 'solution/loads/new_loads.json' and give me a brief summary."
        )
        
        print(f"✅ Agent response: {result.output}")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(simple_test())
    print(f"Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
    sys.exit(0 if success else 1)