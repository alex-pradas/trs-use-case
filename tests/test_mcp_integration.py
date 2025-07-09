"""
MCP integration tests with Pydantic-AI agent.

This module tests the actual MCP protocol communication using a Pydantic-AI agent
that connects to the FastMCP server and calls tools.
"""

import pytest
import sys
import tempfile
import json
import os
from pathlib import Path

# Add tools directory to path
tools_dir = Path(__file__).parent.parent / "tools"
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from agent_client import create_test_agent_sync, run_agent_test
from mcp_server import reset_global_state


class TestMCPIntegrationWithAgent:
    """Test MCP server integration using Pydantic-AI agent."""
    
    def setup_method(self):
        """Set up test environment."""
        reset_global_state()
        
        # Create test LoadSet data
        self.test_data = {
            "name": "Integration Test LoadSet",
            "version": 1,
            "units": {
                "forces": "N",
                "moments": "Nm"
            },
            "load_cases": [
                {
                    "name": "Test Load Case",
                    "description": "Integration test case",
                    "point_loads": [
                        {
                            "name": "Point A",
                            "force_moment": {
                                "fx": 1000.0,
                                "fy": 2000.0,
                                "fz": 3000.0,
                                "mx": 100.0,
                                "my": 200.0,
                                "mz": 300.0
                            }
                        }
                    ]
                }
            ]
        }
    
    def teardown_method(self):
        """Clean up test environment."""
        reset_global_state()
    
    def test_agent_creation(self):
        """Test that the agent can be created and has tools registered."""
        agent = create_test_agent_sync()
        
        # Check that agent was created
        assert agent is not None
        assert agent.server is not None
        
        # The pydantic-ai agent is only created if OpenAI API key is available
        # But the MCP server should always be available
        
        # Check that tools are registered in the server
        tools = agent.server._tool_manager._tools
        assert "load_from_json" in tools
        assert "convert_units" in tools
        assert "scale_loads" in tools
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OpenAI API key not available"
    )
    def test_agent_tool_call_load_from_json(self):
        """Test agent calling load_from_json tool."""
        agent = create_test_agent_sync()
        
        # Create temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_data, f)
            temp_file = f.name
        
        try:
            # Test agent calling the tool
            result = run_agent_test(
                agent.test_tool_call("load_from_json", file_path=temp_file)
            )
            
            # Verify the result
            assert result["success"] is True
            assert "tool_result" in result
            
        finally:
            os.unlink(temp_file)
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OpenAI API key not available"
    )
    def test_agent_workflow(self):
        """Test complete workflow through agent."""
        agent = create_test_agent_sync()
        
        # Create temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_data, f)
            temp_file = f.name
        
        try:
            # Test complete workflow
            result = run_agent_test(
                agent.load_and_process_data(temp_file, "kN", 1.5)
            )
            
            # Verify the result
            assert result["success"] is True
            assert "agent_response" in result
            
        finally:
            os.unlink(temp_file)
    
    def test_direct_tool_access(self):
        """Test direct tool access without OpenAI API."""
        agent = create_test_agent_sync()
        
        # Create temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_data, f)
            temp_file = f.name
        
        try:
            # Test direct tool access via agent methods
            
            # Load JSON
            load_result = agent.call_tool_directly("load_from_json", file_path=temp_file)
            assert load_result["success"] is True
            assert load_result["tool_result"]["success"] is True
            assert load_result["tool_result"]["loadset_name"] == "Integration Test LoadSet"
            
            # Convert units
            convert_result = agent.call_tool_directly("convert_units", target_units="kN")
            assert convert_result["success"] is True
            assert convert_result["tool_result"]["success"] is True
            assert convert_result["tool_result"]["new_units"]["forces"] == "kN"
            
            # Scale loads
            scale_result = agent.call_tool_directly("scale_loads", factor=1.5)
            assert scale_result["success"] is True
            assert scale_result["tool_result"]["success"] is True
            assert scale_result["tool_result"]["scaling_factor"] == 1.5
            
            # Get summary
            summary_result = agent.call_tool_directly("get_load_summary")
            assert summary_result["success"] is True
            assert summary_result["tool_result"]["success"] is True
            assert summary_result["tool_result"]["name"] == "Integration Test LoadSet"
            
        finally:
            os.unlink(temp_file)
    
    def test_error_handling_through_agent(self):
        """Test error handling through the agent."""
        agent = create_test_agent_sync()
        
        # Test error when no LoadSet is loaded
        result = agent.call_tool_directly("convert_units", target_units="kN")
        assert result["success"] is True
        assert result["tool_result"]["success"] is False
        assert "No LoadSet loaded" in result["tool_result"]["error"]
    
    def test_tool_state_management(self):
        """Test that tool state is managed correctly."""
        agent = create_test_agent_sync()
        
        # Create temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_data, f)
            temp_file = f.name
        
        try:
            # Load data
            load_result = agent.call_tool_directly("load_from_json", file_path=temp_file)
            assert load_result["success"] is True
            assert load_result["tool_result"]["success"] is True
            
            # Verify state is maintained - get summary should work
            summary_result = agent.call_tool_directly("get_load_summary")
            assert summary_result["success"] is True
            assert summary_result["tool_result"]["success"] is True
            assert summary_result["tool_result"]["name"] == "Integration Test LoadSet"
            
            # Reset state and verify it's cleared
            reset_global_state()
            
            # Should fail now
            summary_result = agent.call_tool_directly("get_load_summary")
            assert summary_result["success"] is True
            assert summary_result["tool_result"]["success"] is False
            assert "No LoadSet loaded" in summary_result["tool_result"]["error"]
            
        finally:
            os.unlink(temp_file)
    
    def test_get_available_tools(self):
        """Test getting available tools from the MCP server."""
        agent = create_test_agent_sync()
        
        # Get available tools
        tools_result = agent.get_available_tools()
        assert tools_result["success"] is True
        assert "tools" in tools_result
        
        # Verify expected tools are present
        tools = tools_result["tools"]
        expected_tools = [
            "load_from_json",
            "convert_units",
            "scale_loads",
            "export_to_ansys",
            "get_load_summary",
            "list_load_cases"
        ]
        
        for tool_name in expected_tools:
            assert tool_name in tools
            assert "description" in tools[tool_name]