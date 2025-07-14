"""
Agent client for Python script generation and execution via MCP server.

This module provides a Pydantic-AI agent that can generate Python scripts
from natural language instructions and execute them via the script execution MCP server.
"""

import os
import asyncio
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ScriptGenerationAgent:
    """
    A Pydantic-AI agent that generates Python scripts and executes them via MCP server.
    
    This agent can:
    - Generate Python scripts from natural language instructions
    - Execute scripts via the script execution MCP server
    - Download and save output files to local filesystem
    - Handle LoadSet-specific workflows
    """
    
    def __init__(self, mcp_server, output_directory: Optional[Path] = None):
        """
        Initialize the script generation agent.
        
        Args:
            mcp_server: The script execution MCP server instance
            output_directory: Local directory to save downloaded files
        """
        self.mcp_server = mcp_server
        self.output_directory = output_directory or Path.cwd() / "agent_outputs"
        self.output_directory.mkdir(parents=True, exist_ok=True)
        self.agent = None
        
        # Only create pydantic-ai agent if Anthropic API key is available
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                from pydantic_ai import Agent
                
                self.agent = Agent(
                    "anthropic:claude-3-5-sonnet-latest",
                    system_prompt=self._get_system_prompt(),
                )
                
                # Register MCP tools with the agent
                self._register_tools()
                
            except ImportError:
                print("Warning: pydantic-ai not available. Agent functionality will be limited.")
                self.agent = None
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent."""
        return """
You are a Python script generation and execution assistant specialized in aerospace load data processing.

Available tools for script execution:
- execute_python_script: Execute complete Python scripts with file output capture
- list_output_files: List files created during script execution
- download_file: Download files from execution workspace as base64 or text
- upload_file: Upload files to execution workspace before script execution
- get_execution_result: Get detailed execution results (stdout, stderr, timing)
- reset_workspace: Clean up execution workspace
- get_workspace_info: Get information about current workspace

LoadSet Integration:
The execution environment has LoadSet classes pre-imported:
- LoadSet, LoadCase, PointLoad, ForceMoment, ForceUnit
- numpy as np, matplotlib.pyplot as plt (with Agg backend)
- All LoadSet functionality is available

Key LoadSet API reference:
- LoadSet.read_json(file_path) - Load from JSON file
- loadset.convert_to(target_units) - Convert units ("N", "kN", "lbf", "klbf")
- loadset.factor(scale_factor) - Scale all loads by factor
- loadset.compare_to(other_loadset) - Compare two LoadSets
- loadset.to_ansys(folder_path, name_stem) - Export ANSYS files
- loadset.to_dict() - Convert to dictionary for JSON export

Script Generation Guidelines:
1. Generate complete, self-contained Python scripts
2. Include proper error handling and logging
3. Create output files that can be transferred back
4. Use pathlib.Path for file operations
5. Print progress and results to stdout
6. Handle LoadSet operations efficiently

Workflow Pattern:
1. Generate Python script based on user requirements
2. Execute script using execute_python_script tool
3. Check execution results for errors
4. List output files created
5. Download important output files
6. Provide summary of results and files

Always execute the scripts you generate and handle any errors by debugging and regenerating the script.
"""
    
    def _register_tools(self):
        """Register MCP server tools with the Pydantic-AI agent."""
        
        @self.agent.tool_plain
        def execute_python_script(
            script_content: str, 
            script_name: str = "script.py",
            include_loadset_imports: bool = True,
            cleanup_workspace: bool = False
        ) -> dict:
            """Execute a Python script in an isolated workspace."""
            return self.call_tool_directly(
                "execute_python_script",
                script_content=script_content,
                script_name=script_name,
                include_loadset_imports=include_loadset_imports,
                cleanup_workspace=cleanup_workspace
            )["tool_result"]
        
        @self.agent.tool_plain
        def list_output_files() -> dict:
            """List all files in the current workspace."""
            return self.call_tool_directly("list_output_files")["tool_result"]
        
        @self.agent.tool_plain
        def download_file(file_path: str, encoding: str = "base64") -> dict:
            """Download a file from the workspace."""
            return self.call_tool_directly(
                "download_file", 
                file_path=file_path, 
                encoding=encoding
            )["tool_result"]
        
        @self.agent.tool_plain
        def upload_file(file_path: str, content: str, encoding: str = "base64") -> dict:
            """Upload a file to the workspace."""
            return self.call_tool_directly(
                "upload_file",
                file_path=file_path,
                content=content,
                encoding=encoding
            )["tool_result"]
        
        @self.agent.tool_plain
        def get_execution_result() -> dict:
            """Get the result of the last script execution."""
            return self.call_tool_directly("get_execution_result")["tool_result"]
        
        @self.agent.tool_plain
        def reset_workspace(cleanup_current: bool = True) -> dict:
            """Reset the workspace, optionally cleaning up the current one."""
            return self.call_tool_directly(
                "reset_workspace", 
                cleanup_current=cleanup_current
            )["tool_result"]
        
        @self.agent.tool_plain
        def get_workspace_info() -> dict:
            """Get information about the current workspace."""
            return self.call_tool_directly("get_workspace_info")["tool_result"]
    
    async def process_load_instruction(self, instruction: str) -> Dict[str, Any]:
        """
        Process a load data instruction by generating and executing a script.
        
        Args:
            instruction: Natural language instruction for load processing
            
        Returns:
            Dict containing the agent's response and execution results
        """
        if not self.agent:
            return {
                "success": False,
                "error": "Anthropic API key not available or pydantic-ai not installed"
            }
        
        try:
            # Reset workspace before starting
            self.call_tool_directly("reset_workspace", cleanup_current=True)
            
            # Process the instruction with the agent
            result = await self.agent.run(f"""
            Please process this load data instruction:
            
            {instruction}
            
            Generate and execute a complete Python script to fulfill this request.
            After execution, list the output files and download any important results.
            Provide a summary of what was accomplished and what files were created.
            """)
            
            # Download output files to local filesystem
            downloaded_files = await self._download_all_output_files()
            
            return {
                "success": True,
                "agent_response": result.output,
                "messages": [str(msg) for msg in result.all_messages()],
                "downloaded_files": downloaded_files,
                "output_directory": str(self.output_directory)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_loadset_processing_script(
        self, 
        input_file: str,
        operations: List[str],
        output_format: str = "ansys"
    ) -> Dict[str, Any]:
        """
        Generate a specific script for LoadSet processing.
        
        Args:
            input_file: Path to input JSON file
            operations: List of operations to perform
            output_format: Output format ("ansys", "json", "comparison")
            
        Returns:
            Dict containing script generation results
        """
        if not self.agent:
            return {
                "success": False,
                "error": "Anthropic API key not available or pydantic-ai not installed"
            }
        
        operations_text = "\n".join([f"- {op}" for op in operations])
        
        try:
            result = await self.agent.run(f"""
            Generate a Python script for LoadSet processing with these specifications:
            
            Input file: {input_file}
            Operations to perform:
            {operations_text}
            Output format: {output_format}
            
            The script should:
            1. Load the LoadSet from the specified JSON file
            2. Perform all requested operations in sequence
            3. Generate appropriate output files
            4. Print progress and results
            5. Handle errors gracefully
            
            Execute the script and provide results.
            """)
            
            # Download output files
            downloaded_files = await self._download_all_output_files()
            
            return {
                "success": True,
                "script_result": result.output,
                "downloaded_files": downloaded_files
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _download_all_output_files(self) -> List[Dict[str, Any]]:
        """Download all output files from the workspace to local filesystem."""
        downloaded_files = []
        
        try:
            # List files in workspace
            files_result = self.call_tool_directly("list_output_files")
            if not files_result["success"]:
                return downloaded_files
            
            files = files_result["tool_result"]["files"]
            
            for file_info in files:
                if file_info["is_directory"]:
                    continue
                
                file_path = file_info["path"]
                
                # Determine encoding based on file extension
                path_obj = Path(file_path)
                if path_obj.suffix.lower() in [".txt", ".json", ".py", ".inp", ".csv"]:
                    encoding = "text"
                else:
                    encoding = "base64"
                
                # Download file
                download_result = self.call_tool_directly(
                    "download_file",
                    file_path=file_path,
                    encoding=encoding
                )
                
                if download_result["success"]:
                    file_data = download_result["tool_result"]
                    
                    # Save to local filesystem
                    local_path = self.output_directory / file_path
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    if encoding == "base64":
                        local_path.write_bytes(base64.b64decode(file_data["content"]))
                    else:
                        local_path.write_text(file_data["content"], encoding='utf-8')
                    
                    downloaded_files.append({
                        "workspace_path": file_path,
                        "local_path": str(local_path),
                        "size": file_data["size"],
                        "encoding": encoding,
                        "hash": file_data.get("file_hash", "")
                    })
        
        except Exception as e:
            print(f"Warning: Error downloading files: {e}")
        
        return downloaded_files
    
    def call_tool_directly(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Call an MCP tool directly without the AI agent.
        
        Args:
            tool_name: Name of the tool to call
            **kwargs: Tool arguments
            
        Returns:
            Dict containing the tool result
        """
        try:
            tools = self.mcp_server._tool_manager._tools
            if tool_name not in tools:
                return {"success": False, "error": f"Tool '{tool_name}' not found"}
            
            tool_fn = tools[tool_name].fn
            result = tool_fn(**kwargs)
            
            return {"success": True, "tool_result": result}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_available_tools(self) -> Dict[str, Any]:
        """Get list of available tools from the MCP server."""
        try:
            tools = self.mcp_server._tool_manager._tools
            tool_info = {}
            
            for tool_name, tool_data in tools.items():
                tool_info[tool_name] = {
                    "name": tool_name,
                    "description": tool_data.fn.__doc__ or "No description available"
                }
            
            return {"success": True, "tools": tool_info}
            
        except Exception as e:
            return {"success": False, "error": str(e)}


# Example usage functions
async def demo_load_processing():
    """Demonstrate load processing with the script generation agent."""
    from script_exec_mcp_server import create_mcp_server
    
    # Create MCP server
    server = create_mcp_server()
    
    # Create agent
    agent = ScriptGenerationAgent(server)
    
    if not agent.agent:
        print("❌ Anthropic API key not available - cannot run demo")
        return
    
    print("🚀 Script Generation Agent Demo")
    print("=" * 50)
    
    # Demo instruction
    instruction = """
    Load the aerospace load data from 'solution/loads/new_loads.json',
    convert it to kN units, scale by a factor of 1.5, and export to ANSYS format.
    Also create a summary JSON file with the processed load information.
    """
    
    print(f"📝 Instruction: {instruction}")
    print("\n🤖 Processing with AI agent...")
    
    # Process instruction
    result = await agent.process_load_instruction(instruction)
    
    if result["success"]:
        print("✅ Processing completed successfully!")
        print(f"\n🤖 Agent Response:\n{result['agent_response']}")
        print(f"\n📁 Output directory: {result['output_directory']}")
        print(f"📄 Downloaded files: {len(result['downloaded_files'])}")
        
        for file_info in result["downloaded_files"]:
            print(f"  - {file_info['local_path']} ({file_info['size']} bytes)")
    else:
        print(f"❌ Processing failed: {result['error']}")


if __name__ == "__main__":
    asyncio.run(demo_load_processing())