
import sys
import asyncio
from pathlib import Path

# Add project root and tools to path
project_root = Path(__file__).parent.parent
tools_dir = project_root / "tools"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(tools_dir))

from tools.agents import create_loadset_agent, create_loadset_agent_with_model, create_default_server

async def test_agent_tools():
    print("Testing create_loadset_agent with MCPServerStdio...")
    
    # Create server
    server = create_default_server()
    
    async with server:
        agent = create_loadset_agent(server=server)
        
        # Verify agent creation
        print("Agent created successfully.")
        
        # Debug agent attributes
        print(f"Agent attributes: {dir(agent)}")
        
        # Check for toolsets or similar
        if hasattr(agent, '_user_toolsets') and agent._user_toolsets:
             print(f"✅ Agent has {len(agent._user_toolsets)} toolset(s) configured (private attribute).")
        elif hasattr(agent, 'toolsets') and agent.toolsets:
            print(f"✅ Agent has {len(agent.toolsets)} toolset(s) configured.")
        else:
            print("❌ Agent has no toolsets configured.")
            sys.exit(1)

        # Try to list tools (if possible via pydantic-ai API, or just assume it works if server connects)
        # We can try a simple run if we had a valid input, but we don't want to consume tokens or rely on LLM here.
        # Just verifying the structure is enough for now given the constraints.
        
    print("\nTesting create_loadset_agent_with_model...")
    try:
        server2 = create_default_server()
        async with server2:
            agent_with_model = create_loadset_agent_with_model("kimi", server=server2)
            if hasattr(agent_with_model, '_user_toolsets') and agent_with_model._user_toolsets:
                print(f"✅ Model Agent has {len(agent_with_model._user_toolsets)} toolset(s) configured.")
            elif hasattr(agent_with_model, 'toolsets') and agent_with_model.toolsets:
                print(f"✅ Model Agent has {len(agent_with_model.toolsets)} toolset(s) configured.")
            else:
                print("❌ Model Agent has no toolsets configured.")
                sys.exit(1)
            
    except Exception as e:
        print(f"⚠️ Could not create agent with model (might be missing keys or config): {e}")

if __name__ == "__main__":
    asyncio.run(test_agent_tools())
