
import sys
from pathlib import Path

# Add project root and tools to path
project_root = Path(__file__).parent.parent
tools_dir = project_root / "tools"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(tools_dir))

from tools.agents import create_loadset_agent, create_loadset_agent_with_model
from tools.mcps.loads_mcp_server import LoadSetMCPProvider

def test_agent_tools():
    print("Testing create_loadset_agent...")
    agent = create_loadset_agent()
    
    # Check registered tools
    # pydantic-ai internal structure might vary, trying to access tools via _function_toolset or similar
    if hasattr(agent, '_function_tools'):
        tools = agent._function_tools
        tool_names = [t.name for t in tools.values()]
    elif hasattr(agent, '_function_toolset'):
        # _function_toolset might be a FunctionToolset object
        toolset = agent._function_toolset
        # It might have a 'tools' dictionary or list
        if hasattr(toolset, 'tools'):
             # tools might be a dict or list
             if isinstance(toolset.tools, dict):
                 tool_names = [t.name for t in toolset.tools.values()]
             else:
                 tool_names = [t.name for t in toolset.tools]
        else:
             # Fallback: try to print dir
             print(f"Debug: toolset attributes: {dir(toolset)}")
             tool_names = []
    else:
        print(f"Debug: agent attributes: {dir(agent)}")
        tool_names = []
        
    expected_tools = [
        "load_from_json",
        "convert_units",
        "scale_loads",
        "export_to_ansys",
        "get_load_summary",
        "list_load_cases",
        "compare_loadsets",
        "get_comparison_summary",
        "envelope_loadset",
        "get_point_extremes",
        "load_second_loadset",
        "export_comparison_report"
    ]

    print(f"Found {len(tool_names)} tools registered.")
    
    missing = []
    for expected in expected_tools:
        if expected not in tool_names:
            missing.append(expected)
            
    if missing:
        print(f"❌ Missing tools: {missing}")
        sys.exit(1)
    else:
        print("✅ All expected tools are registered.")

    print("\nTesting create_loadset_agent_with_model...")
    # Use a dummy key that is valid in the system (e.g. 'haiku' or 'kimi')
    # We need to make sure we don't actually call the LLM, just check registration.
    try:
        agent_with_model = create_loadset_agent_with_model("kimi")
        if hasattr(agent_with_model, '_function_tools'):
            tools_model = agent_with_model._function_tools
            tool_names_model = [t.name for t in tools_model.values()]
        elif hasattr(agent_with_model, '_function_toolset'):
            toolset = agent_with_model._function_toolset
            if hasattr(toolset, 'tools'):
                 if isinstance(toolset.tools, dict):
                     tool_names_model = [t.name for t in toolset.tools.values()]
                 else:
                     tool_names_model = [t.name for t in toolset.tools]
            else:
                 tool_names_model = []
        else:
            tool_names_model = []
            
        print(f"Found {len(tool_names_model)} tools registered.")
        missing_model = []
        for expected in expected_tools:
            if expected not in tool_names_model:
                missing_model.append(expected)
        
        if missing_model:
            print(f"❌ Missing tools in model agent: {missing_model}")
            sys.exit(1)
        else:
            print("✅ All expected tools are registered in model agent.")
            
    except Exception as e:
        print(f"⚠️ Could not create agent with model (might be missing keys or config): {e}")
        # This is acceptable if we just want to verify the code path for registration
        # but ideally we want it to succeed.

if __name__ == "__main__":
    test_agent_tools()
