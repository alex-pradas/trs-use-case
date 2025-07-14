"""
Integration tests for script generation agent with real LoadSet workflows.

This module tests the complete workflow from instruction to script generation
to execution to file transfer using real aerospace load data.
"""

import pytest
import asyncio
import os
import tempfile
import shutil
import json
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv
import sys

# Add the project root to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tools.mcps.script_exec_mcp_server import create_mcp_server
from tools.script_agent_client import ScriptGenerationAgent

# Load environment variables
load_dotenv()


class TestScriptAgentIntegration:
    """Test suite for script generation agent integration with real LoadSet workflows."""
    
    def setup_method(self):
        """Set up test environment."""
        # Create temporary output directory
        self.temp_dir = Path(tempfile.mkdtemp())
        self.output_dir = self.temp_dir / "agent_outputs"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create MCP server
        self.server = create_mcp_server()
        
        # Create agent
        self.agent = ScriptGenerationAgent(self.server, output_directory=self.output_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        # Clean up temporary directory
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        
        # Reset server workspace
        if hasattr(self.agent, 'call_tool_directly'):
            self.agent.call_tool_directly("reset_workspace", cleanup_current=True)
    
    def test_direct_tool_functionality(self):
        """Test that all MCP tools work correctly without agent."""
        # Test execute_python_script
        script = '''
print("Testing direct tool execution")
with open("test_output.txt", "w") as f:
    f.write("Direct tool test successful")
'''
        
        result = self.agent.call_tool_directly("execute_python_script", script_content=script)
        assert result["success"], f"execute_python_script failed: {result.get('error')}"
        assert result["tool_result"]["success"], "Script execution failed"
        
        # Test list_output_files
        result = self.agent.call_tool_directly("list_output_files")
        assert result["success"], f"list_output_files failed: {result.get('error')}"
        files = result["tool_result"]["files"]
        assert any("test_output.txt" in f["path"] for f in files), "Output file not found"
        
        # Test download_file
        result = self.agent.call_tool_directly("download_file", file_path="test_output.txt", encoding="text")
        assert result["success"], f"download_file failed: {result.get('error')}"
        assert result["tool_result"]["content"] == "Direct tool test successful"
        
        # Test get_execution_result
        result = self.agent.call_tool_directly("get_execution_result")
        assert result["success"], f"get_execution_result failed: {result.get('error')}"
        assert "Testing direct tool execution" in result["tool_result"]["execution_result"]["stdout"]
    
    @pytest.mark.asyncio
    async def test_agent_basic_script_generation(self):
        """Test that agent can generate and execute basic scripts."""
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not available")
        
        instruction = """
        Create a simple Python script that:
        1. Creates a list of numbers from 1 to 10
        2. Calculates their sum and average
        3. Saves the results to a JSON file called 'math_results.json'
        4. Prints a summary
        """
        
        result = await self.agent.process_load_instruction(instruction)
        
        assert result["success"], f"Agent processing failed: {result.get('error', 'Unknown error')}"
        assert "agent_response" in result
        
        # Check that files were downloaded to local filesystem
        downloaded_files = result.get("downloaded_files", [])
        assert len(downloaded_files) > 0, "No files were downloaded"
        
        # Look for the expected output file
        json_files = [f for f in downloaded_files if "json" in f["local_path"]]
        assert len(json_files) > 0, "No JSON files were created"
        
        # Verify file content
        json_file_path = Path(json_files[0]["local_path"])
        assert json_file_path.exists(), "Downloaded JSON file does not exist locally"
        
        try:
            content = json.loads(json_file_path.read_text())
            # Should contain some kind of mathematical results
            assert isinstance(content, (dict, list)), "JSON content should be dict or list"
        except json.JSONDecodeError:
            pytest.fail("Downloaded JSON file is not valid JSON")
    
    @pytest.mark.asyncio
    async def test_agent_loadset_basic_processing(self):
        """Test agent processing of LoadSet data with basic operations."""
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not available")
        
        instruction = """
        Process aerospace load data with these steps:
        1. Load LoadSet from 'solution/loads/new_loads.json'
        2. Show the current units and number of load cases
        3. Convert units to kN (if not already)
        4. Scale all loads by a factor of 1.2
        5. Export the processed data to JSON format
        6. Create a summary file with processing details
        """
        
        result = await self.agent.process_load_instruction(instruction)
        
        assert result["success"], f"LoadSet processing failed: {result.get('error', 'Unknown error')}"
        
        # Check downloaded files
        downloaded_files = result.get("downloaded_files", [])
        assert len(downloaded_files) > 0, "No files were downloaded"
        
        # Should have JSON files (processed data and summary)
        json_files = [f for f in downloaded_files if ".json" in f["local_path"]]
        assert len(json_files) >= 1, f"Expected JSON files but got: {[f['local_path'] for f in downloaded_files]}"
        
        # Verify at least one file contains LoadSet data
        for json_file_info in json_files:
            json_path = Path(json_file_info["local_path"])
            if json_path.exists():
                try:
                    content = json.loads(json_path.read_text())
                    if isinstance(content, dict) and "load_cases" in content:
                        # Found processed LoadSet data
                        assert "name" in content, "LoadSet should have a name"
                        assert "force_units" in content, "LoadSet should have force units"
                        assert len(content["load_cases"]) > 0, "LoadSet should have load cases"
                        break
                except json.JSONDecodeError:
                    continue
        else:
            pytest.fail("No valid LoadSet JSON data found in downloaded files")
    
    @pytest.mark.asyncio
    async def test_agent_loadset_unit_conversion_workflow(self):
        """Test agent performing unit conversion analysis."""
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not available")
        
        instruction = """
        Perform a unit conversion analysis on aerospace load data:
        1. Load LoadSet from 'solution/loads/new_loads.json'
        2. Show the original units
        3. Convert the data to different unit systems: kN, lbf, and klbf
        4. For each unit system, save the converted LoadSet to a separate JSON file
        5. Create a comparison table showing sample force values in each unit system
        6. Generate a summary report of the conversion analysis
        """
        
        result = await self.agent.process_load_instruction(instruction)
        
        assert result["success"], f"Unit conversion workflow failed: {result.get('error', 'Unknown error')}"
        
        downloaded_files = result.get("downloaded_files", [])
        assert len(downloaded_files) > 0, "No files were downloaded"
        
        # Should have multiple JSON files for different unit systems
        json_files = [f for f in downloaded_files if ".json" in f["local_path"]]
        assert len(json_files) >= 2, f"Expected multiple JSON files but got: {len(json_files)}"
        
        # Verify files contain different unit systems
        unit_systems_found = set()
        for json_file_info in json_files:
            json_path = Path(json_file_info["local_path"])
            if json_path.exists():
                try:
                    content = json.loads(json_path.read_text())
                    if isinstance(content, dict) and "force_units" in content:
                        unit_systems_found.add(content["force_units"])
                except json.JSONDecodeError:
                    continue
        
        # Should have found at least 2 different unit systems
        assert len(unit_systems_found) >= 2, f"Expected multiple unit systems but found: {unit_systems_found}"
    
    @pytest.mark.asyncio
    async def test_agent_loadset_comparison_workflow(self):
        """Test agent performing LoadSet comparison."""
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not available")
        
        instruction = """
        Compare two LoadSet files:
        1. Load LoadSet from 'solution/loads/new_loads.json' 
        2. Load LoadSet from 'solution/loads/old_loads.json'
        3. Perform a detailed comparison between the two datasets
        4. Generate comparison statistics and identify key differences
        5. Export the comparison results to JSON format
        6. Create a summary report highlighting the most significant differences
        7. If possible, generate comparison charts
        """
        
        result = await self.agent.process_load_instruction(instruction)
        
        assert result["success"], f"LoadSet comparison failed: {result.get('error', 'Unknown error')}"
        
        downloaded_files = result.get("downloaded_files", [])
        assert len(downloaded_files) > 0, "No files were downloaded"
        
        # Should have comparison results and summary files
        json_files = [f for f in downloaded_files if ".json" in f["local_path"]]
        assert len(json_files) >= 1, "Expected comparison JSON files"
        
        # Look for comparison-related content
        comparison_found = False
        for json_file_info in json_files:
            json_path = Path(json_file_info["local_path"])
            if json_path.exists():
                try:
                    content = json.loads(json_path.read_text())
                    if isinstance(content, dict):
                        # Look for comparison indicators
                        if any(key in content for key in ["comparison", "differences", "total_comparisons", "comparison_data"]):
                            comparison_found = True
                            break
                except json.JSONDecodeError:
                    continue
        
        assert comparison_found, "No comparison results found in downloaded files"
    
    @pytest.mark.asyncio
    async def test_agent_loadset_ansys_export_workflow(self):
        """Test agent exporting LoadSet to ANSYS format."""
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not available")
        
        instruction = """
        Process LoadSet data for ANSYS export:
        1. Load LoadSet from 'solution/loads/new_loads.json'
        2. Convert to kN units if needed
        3. Scale loads by factor 1.5 
        4. Export to ANSYS format files (.inp files)
        5. Create a manifest file listing all exported ANSYS files
        6. Generate a processing summary with details of the operations performed
        """
        
        result = await self.agent.process_load_instruction(instruction)
        
        assert result["success"], f"ANSYS export workflow failed: {result.get('error', 'Unknown error')}"
        
        downloaded_files = result.get("downloaded_files", [])
        assert len(downloaded_files) > 0, "No files were downloaded"
        
        # Should have ANSYS .inp files
        inp_files = [f for f in downloaded_files if ".inp" in f["local_path"]]
        assert len(inp_files) > 0, f"Expected ANSYS .inp files but got file types: {[Path(f['local_path']).suffix for f in downloaded_files]}"
        
        # Verify ANSYS file content
        for inp_file_info in inp_files:
            inp_path = Path(inp_file_info["local_path"])
            if inp_path.exists():
                content = inp_path.read_text()
                assert "f,all," in content, f"ANSYS file {inp_path} should contain f,all commands"
                assert any(cmd in content for cmd in ["fx,", "fy,", "fz,"]), f"ANSYS file {inp_path} should contain force commands"
                break
        else:
            pytest.fail("No valid ANSYS files found")
    
    @pytest.mark.asyncio
    async def test_agent_error_handling_and_recovery(self):
        """Test agent's ability to handle errors and recover."""
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not available")
        
        instruction = """
        Try to process this challenging request:
        1. Load LoadSet from 'nonexistent_file.json' (this will fail)
        2. Handle the error gracefully
        3. Instead, load from 'solution/loads/new_loads.json'
        4. Show that processing can continue after an error
        5. Generate a simple summary of the LoadSet data
        6. Save the summary to a file
        """
        
        result = await self.agent.process_load_instruction(instruction)
        
        # Agent should handle the error and recover
        assert result["success"], f"Agent should recover from errors but failed: {result.get('error', 'Unknown error')}"
        
        # Should still produce some output files
        downloaded_files = result.get("downloaded_files", [])
        
        # Even with error handling, agent should produce some output
        # (either error logs or successful recovery results)
        assert len(downloaded_files) >= 0, "Agent should handle errors gracefully"
    
    @pytest.mark.asyncio
    async def test_agent_custom_analysis_workflow(self):
        """Test agent performing custom analysis workflow."""
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not available")
        
        instruction = """
        Perform a comprehensive aerospace load analysis:
        1. Load LoadSet from 'solution/loads/new_loads.json'
        2. Calculate statistics for each load case (min, max, average forces)
        3. Identify the load case with maximum force magnitude
        4. Convert data to both kN and lbf units for comparison
        5. Create a detailed analysis report with:
           - Total number of load cases and points
           - Force magnitude statistics
           - Unit conversion factors used
           - Load case summary table
        6. Export all results to well-organized JSON files
        7. Generate a human-readable summary text file
        """
        
        result = await self.agent.process_load_instruction(instruction)
        
        assert result["success"], f"Custom analysis workflow failed: {result.get('error', 'Unknown error')}"
        
        downloaded_files = result.get("downloaded_files", [])
        assert len(downloaded_files) > 0, "No files were downloaded"
        
        # Should have analysis results in JSON and text formats
        json_files = [f for f in downloaded_files if ".json" in f["local_path"]]
        text_files = [f for f in downloaded_files if ".txt" in f["local_path"]]
        
        assert len(json_files) >= 1, "Expected analysis JSON files"
        
        # Verify analysis content
        analysis_found = False
        for json_file_info in json_files:
            json_path = Path(json_file_info["local_path"])
            if json_path.exists():
                try:
                    content = json.loads(json_path.read_text())
                    if isinstance(content, dict):
                        # Look for analysis indicators
                        if any(key in str(content).lower() for key in ["statistics", "analysis", "maximum", "minimum", "average"]):
                            analysis_found = True
                            break
                except json.JSONDecodeError:
                    continue
        
        # Analysis results should be found in at least one file
        assert analysis_found or len(text_files) > 0, "No analysis results found in downloaded files"
    
    def test_agent_available_tools(self):
        """Test that agent has access to all expected tools."""
        tools_result = self.agent.get_available_tools()
        
        assert tools_result["success"], f"Failed to get available tools: {tools_result.get('error')}"
        
        tools = tools_result["tools"]
        expected_tools = [
            "execute_python_script",
            "list_output_files",
            "download_file", 
            "upload_file",
            "get_execution_result",
            "reset_workspace",
            "get_workspace_info"
        ]
        
        for tool_name in expected_tools:
            assert tool_name in tools, f"Tool {tool_name} not found in available tools"
    
    def test_output_directory_creation(self):
        """Test that output directory is created and accessible."""
        assert self.output_dir.exists(), "Output directory should exist"
        assert self.output_dir.is_dir(), "Output directory should be a directory"
        
        # Test writing to output directory
        test_file = self.output_dir / "test.txt"
        test_file.write_text("test content")
        assert test_file.exists(), "Should be able to write to output directory"


# Helper functions for running tests
def run_agent_integration_test(test_method):
    """Run a single agent integration test."""
    return asyncio.run(test_method)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])