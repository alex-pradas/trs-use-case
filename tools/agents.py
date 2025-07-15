"""
Global pydantic-ai agents following best practices.

This module defines reusable agents with tools registered via decorators,
following the pydantic-ai documentation recommendations.
"""

from pydantic_ai import Agent
from tools.model_config import get_model_name
from tools.mcp_bridge import call_mcp_tool, setup_default_servers


# Set up MCP servers on module import
setup_default_servers()


# Global LoadSet processing agent
loadset_agent = Agent(
    get_model_name(),
    system_prompt="""
    You are an expert aerospace structural loads analyst with access to LoadSet processing tools.
    
    You can help with:
    - Loading structural load data from JSON files
    - Converting units between N, kN, lbf, klbf for forces and Nm, kNm, lbf-ft for moments
    - Scaling loads by factors for design analysis
    - Exporting data to ANSYS format files
    - Comparing different LoadSets
    - Generating visualization charts
    
    Always use the available tools to perform operations. Be precise with file paths and parameters.
    Provide clear explanations of what operations you're performing and their results.
    
    When working with LoadSets:
    - Units are critical - always specify and verify units
    - Load cases represent different structural loading conditions
    - Point loads have force (fx,fy,fz) and moment (mx,my,mz) components
    - ANSYS export creates one .inp file per load case
    """,
)


# Global Python execution agent  
python_agent = Agent(
    get_model_name(),
    system_prompt="""
    You are an expert Python programmer with access to a persistent Python execution environment.
    
    Key capabilities:
    - Execute Python code in a persistent IPython session
    - Variables and imports persist across executions
    - LoadSet classes are pre-imported and available
    - Generate and test code incrementally
    - Handle errors and debug issues
    
    Available tools allow you to:
    - Execute code and see results immediately
    - List variables in the current session
    - Get detailed information about specific variables
    - Reset the session if needed
    - Install packages using uv
    
    When solving problems:
    1. Break down complex tasks into steps
    2. Write and execute code incrementally  
    3. Test and validate results as you go
    4. Use variables to store intermediate results
    5. Build on previous executions
    
    Always execute code to demonstrate solutions and verify they work.
    """,
)


# Global script generation and execution agent
script_agent = Agent(
    get_model_name(), 
    system_prompt="""
    You are an expert Python script generator with access to script execution tools.
    
    You can help with:
    - Generating complete Python scripts from requirements
    - Executing scripts in isolated workspaces
    - Managing input/output files
    - Processing LoadSet data workflows
    - Creating data analysis and visualization scripts
    
    Key features:
    - Scripts run in isolated environments
    - Can upload files before execution
    - Can download generated files after execution
    - LoadSet functionality is available in scripts
    - Workspace cleanup after execution
    
    When generating scripts:
    1. Create complete, self-contained Python scripts
    2. Include proper error handling
    3. Add informative comments and docstrings
    4. Handle file I/O appropriately
    5. Generate meaningful output files
    
    Always test scripts by executing them and verify the results.
    """,
)


# Tool registration for LoadSet agent - using @tool_plain for stateless tools
@loadset_agent.tool_plain
def load_from_json(file_path: str) -> dict:
    """Load a LoadSet from a JSON file."""
    result = call_mcp_tool("loads", "load_from_json", file_path=file_path)
    if result["success"]:
        return result["result"]
    else:
        raise RuntimeError(f"Failed to load LoadSet: {result['error']}")


@loadset_agent.tool_plain
def convert_units(target_units: str) -> dict:
    """Convert the current LoadSet to different units (N, kN, lbf, klbf)."""
    result = call_mcp_tool("loads", "convert_units", target_units=target_units)
    if result["success"]:
        return result["result"]
    else:
        raise RuntimeError(f"Failed to convert units: {result['error']}")


@loadset_agent.tool_plain
def scale_loads(factor: float) -> dict:
    """Scale all loads in the current LoadSet by a factor."""
    result = call_mcp_tool("loads", "scale_loads", factor=factor)
    if result["success"]:
        return result["result"]
    else:
        raise RuntimeError(f"Failed to scale loads: {result['error']}")


@loadset_agent.tool_plain
def export_to_ansys(folder_path: str, name_stem: str) -> dict:
    """Export the current LoadSet to ANSYS format files."""
    result = call_mcp_tool("loads", "export_to_ansys", folder_path=folder_path, name_stem=name_stem)
    if result["success"]:
        return result["result"]
    else:
        raise RuntimeError(f"Failed to export to ANSYS: {result['error']}")


@loadset_agent.tool_plain
def get_load_summary() -> dict:
    """Get summary information about the current LoadSet."""
    result = call_mcp_tool("loads", "get_load_summary")
    if result["success"]:
        return result["result"]
    else:
        raise RuntimeError(f"Failed to get load summary: {result['error']}")


@loadset_agent.tool_plain
def list_load_cases() -> dict:
    """List all load cases in the current LoadSet."""
    result = call_mcp_tool("loads", "list_load_cases")
    if result["success"]:
        return result["result"]
    else:
        raise RuntimeError(f"Failed to list load cases: {result['error']}")


@loadset_agent.tool_plain
def load_second_loadset(file_path: str) -> dict:
    """Load a second LoadSet for comparison."""
    result = call_mcp_tool("loads", "load_second_loadset", file_path=file_path)
    if result["success"]:
        return result["result"]
    else:
        raise RuntimeError(f"Failed to load second LoadSet: {result['error']}")


@loadset_agent.tool_plain
def compare_loadsets() -> dict:
    """Compare two LoadSets with detailed analysis."""
    result = call_mcp_tool("loads", "compare_loadsets")
    if result["success"]:
        return result["result"]
    else:
        raise RuntimeError(f"Failed to compare LoadSets: {result['error']}")


@loadset_agent.tool_plain
def generate_comparison_charts(output_format: str = "base64", output_folder: str = "") -> dict:
    """Generate range bar charts for LoadSet comparison."""
    result = call_mcp_tool("loads", "generate_comparison_charts", output_format=output_format, output_folder=output_folder)
    if result["success"]:
        return result["result"]
    else:
        raise RuntimeError(f"Failed to generate charts: {result['error']}")


@loadset_agent.tool_plain
def export_comparison_json(output_path: str) -> dict:
    """Export comparison results to JSON file."""
    result = call_mcp_tool("loads", "export_comparison_json", output_path=output_path)
    if result["success"]:
        return result["result"]
    else:
        raise RuntimeError(f"Failed to export comparison JSON: {result['error']}")


@loadset_agent.tool_plain
def get_comparison_summary() -> dict:
    """Get high-level comparison statistics."""
    result = call_mcp_tool("loads", "get_comparison_summary")
    if result["success"]:
        return result["result"]
    else:
        raise RuntimeError(f"Failed to get comparison summary: {result['error']}")


# Tool registration for Python execution agent
@python_agent.tool_plain
def execute_code(code: str) -> dict:
    """Execute Python code in the persistent session."""
    result = call_mcp_tool("python", "execute_code", code=code)
    if result["success"]:
        return result["result"]
    else:
        raise RuntimeError(f"Failed to execute code: {result['error']}")


@python_agent.tool_plain
def list_variables() -> dict:
    """List all variables in the current session namespace."""
    result = call_mcp_tool("python", "list_variables")
    if result["success"]:
        return result["result"]
    else:
        raise RuntimeError(f"Failed to list variables: {result['error']}")


@python_agent.tool_plain
def get_variable(name: str) -> dict:
    """Get detailed information about a specific variable."""
    result = call_mcp_tool("python", "get_variable", name=name)
    if result["success"]:
        return result["result"]
    else:
        raise RuntimeError(f"Failed to get variable: {result['error']}")


@python_agent.tool_plain
def reset_session() -> dict:
    """Reset the Python session, clearing all variables and history."""
    result = call_mcp_tool("python", "reset_session")
    if result["success"]:
        return result["result"]
    else:
        raise RuntimeError(f"Failed to reset session: {result['error']}")


@python_agent.tool_plain
def install_package(package_name: str, dev: bool = False) -> dict:
    """Install a Python package using uv."""
    result = call_mcp_tool("python", "install_package", package_name=package_name, dev=dev)
    if result["success"]:
        return result["result"]
    else:
        raise RuntimeError(f"Failed to install package: {result['error']}")


@python_agent.tool_plain
def get_execution_history(limit: int = 10) -> dict:
    """Get recent execution history."""
    result = call_mcp_tool("python", "get_execution_history", limit=limit)
    if result["success"]:
        return result["result"]
    else:
        raise RuntimeError(f"Failed to get execution history: {result['error']}")


@python_agent.tool_plain
def configure_security(enable_security: bool = True, execution_timeout: int = 30) -> dict:
    """Configure security settings for code execution."""
    result = call_mcp_tool("python", "configure_security", enable_security=enable_security, execution_timeout=execution_timeout)
    if result["success"]:
        return result["result"]
    else:
        raise RuntimeError(f"Failed to configure security: {result['error']}")


# Tool registration for script generation agent
@script_agent.tool_plain
def execute_python_script(script_content: str, script_name: str = "generated_script.py") -> dict:
    """Execute a complete Python script in isolated workspace."""
    result = call_mcp_tool("script", "execute_python_script", script_content=script_content, script_name=script_name)
    if result["success"]:
        return result["result"]
    else:
        raise RuntimeError(f"Failed to execute script: {result['error']}")


@script_agent.tool_plain
def list_output_files() -> dict:
    """List all files created during script execution."""
    result = call_mcp_tool("script", "list_output_files")
    if result["success"]:
        return result["result"]
    else:
        raise RuntimeError(f"Failed to list output files: {result['error']}")


@script_agent.tool_plain
def download_file(file_path: str, output_format: str = "auto") -> dict:
    """Download files from workspace as base64 or text."""
    result = call_mcp_tool("script", "download_file", file_path=file_path, output_format=output_format)
    if result["success"]:
        return result["result"]
    else:
        raise RuntimeError(f"Failed to download file: {result['error']}")


@script_agent.tool_plain
def upload_file(file_path: str, content: str, content_type: str = "text") -> dict:
    """Upload files to workspace before script execution."""
    result = call_mcp_tool("script", "upload_file", file_path=file_path, content=content, content_type=content_type)
    if result["success"]:
        return result["result"]
    else:
        raise RuntimeError(f"Failed to upload file: {result['error']}")


@script_agent.tool_plain
def get_execution_result() -> dict:
    """Get detailed execution results (stdout, stderr, timing)."""
    result = call_mcp_tool("script", "get_execution_result")
    if result["success"]:
        return result["result"]
    else:
        raise RuntimeError(f"Failed to get execution result: {result['error']}")


@script_agent.tool_plain
def reset_workspace() -> dict:
    """Clean up execution workspace."""
    result = call_mcp_tool("script", "reset_workspace")
    if result["success"]:
        return result["result"]
    else:
        raise RuntimeError(f"Failed to reset workspace: {result['error']}")


@script_agent.tool_plain
def get_workspace_info() -> dict:
    """Get information about current workspace."""
    result = call_mcp_tool("script", "get_workspace_info")
    if result["success"]:
        return result["result"]
    else:
        raise RuntimeError(f"Failed to get workspace info: {result['error']}")


if __name__ == "__main__":
    print("🤖 Global Agents Initialized")
    print("=" * 30)
    
    from model_config import get_model_name, get_provider_name, validate_model_config
    
    print(f"Model: {get_model_name()}")
    print(f"Provider: {get_provider_name()}")
    
    is_valid, error = validate_model_config()
    if is_valid:
        print("✅ Model configuration is valid")
        
        print("\n📋 Available agents:")
        print(f"  - loadset_agent: LoadSet processing and analysis")
        print(f"  - python_agent: Python code execution") 
        print(f"  - script_agent: Script generation and execution")
        
        print("\n🔧 LoadSet agent tools:")
        for tool_name in ["load_from_json", "convert_units", "scale_loads", "export_to_ansys", "get_load_summary"]:
            print(f"  - {tool_name}")
            
        print("\n🐍 Python agent tools:")
        for tool_name in ["execute_code", "list_variables", "get_variable", "reset_session"]:
            print(f"  - {tool_name}")
            
        print("\n📜 Script agent tools:")
        for tool_name in ["execute_python_script", "list_output_files", "download_file", "upload_file"]:
            print(f"  - {tool_name}")
    else:
        print(f"❌ Model configuration error: {error}")
        print("Please set the appropriate API key for your chosen model.")