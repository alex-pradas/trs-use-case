"""
Tests for the Script Execution MCP server.

This module tests the Python script execution functionality with workspace management
and file I/O capabilities.
"""

import pytest
import tempfile
import shutil
import json
import base64
from pathlib import Path
import sys
import time

# Add tools directory to path
tools_dir = Path(__file__).parent.parent / "tools"
sys.path.insert(0, str(tools_dir))

from script_exec_mcp_server import (
    ScriptExecutorMCPProvider,
    ExecutionResult,
    FileInfo,
    create_mcp_server
)


class TestExecutionResult:
    """Test the ExecutionResult dataclass."""
    
    def test_basic_result(self):
        """Test basic result creation and serialization."""
        result = ExecutionResult(
            success=True,
            exit_code=0,
            stdout="Hello World\n",
            stderr="",
            error="",
            execution_time=0.1,
            output_files=["output.txt"],
            workspace_path="/tmp/workspace",
            script_hash="abc123"
        )
        
        result_dict = result.to_dict()
        assert result_dict["success"] is True
        assert result_dict["exit_code"] == 0
        assert result_dict["stdout"] == "Hello World\n"
        assert result_dict["output_files"] == ["output.txt"]
        assert result_dict["script_hash"] == "abc123"


class TestFileInfo:
    """Test the FileInfo dataclass."""
    
    def test_file_info_creation(self):
        """Test FileInfo creation."""
        file_info = FileInfo(
            name="test.txt",
            path="output/test.txt",
            size=100,
            is_directory=False,
            modified_time=time.time(),
            file_hash="def456"
        )
        
        assert file_info.name == "test.txt"
        assert file_info.size == 100
        assert file_info.is_directory is False


class TestScriptExecutorMCPProvider:
    """Test the ScriptExecutorMCPProvider class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.provider = ScriptExecutorMCPProvider(
            base_workspace_dir=self.temp_dir,
            execution_timeout=30
        )
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test provider initialization."""
        assert self.provider.base_workspace_dir == self.temp_dir
        assert self.provider.execution_timeout == 30
        assert self.provider.current_workspace is None
        assert self.provider.last_execution is None
    
    def test_simple_script_execution(self):
        """Test simple script execution."""
        script = 'print("Hello from script!")'
        
        result = self.provider.execute_python_script(script)
        
        assert result["success"] is True
        execution_result = result["execution_result"]
        assert execution_result["success"] is True
        assert execution_result["exit_code"] == 0
        assert "Hello from script!" in execution_result["stdout"]
        assert self.provider.current_workspace is not None
    
    def test_script_with_file_output(self):
        """Test script that creates output files."""
        script = '''
with open("output.txt", "w") as f:
    f.write("This is test output")
    
with open("data.json", "w") as f:
    import json
    json.dump({"test": "data"}, f)
'''
        
        result = self.provider.execute_python_script(script)
        
        assert result["success"] is True
        execution_result = result["execution_result"]
        assert execution_result["success"] is True
        assert len(execution_result["output_files"]) >= 2
        assert any("output.txt" in f for f in execution_result["output_files"])
        assert any("data.json" in f for f in execution_result["output_files"])
    
    def test_script_with_error(self):
        """Test script that produces an error."""
        script = 'raise ValueError("Test error")'
        
        result = self.provider.execute_python_script(script)
        
        assert result["success"] is True  # Tool call succeeded
        execution_result = result["execution_result"]
        assert execution_result["success"] is False  # Script failed
        assert execution_result["exit_code"] != 0
        assert "ValueError" in execution_result["stderr"]
    
    def test_script_with_loadset_imports(self):
        """Test script with LoadSet imports enabled."""
        script = '''
print(f"LoadSet type: {type(LoadSet)}")
print(f"Available in namespace: {dir()}")
'''
        
        result = self.provider.execute_python_script(
            script, 
            include_loadset_imports=True
        )
        
        assert result["success"] is True
        execution_result = result["execution_result"]
        assert execution_result["success"] is True
        assert "LoadSet" in execution_result["stdout"]
    
    def test_script_without_loadset_imports(self):
        """Test script without LoadSet imports."""
        script = 'print("No imports added")'
        
        result = self.provider.execute_python_script(
            script, 
            include_loadset_imports=False
        )
        
        assert result["success"] is True
        execution_result = result["execution_result"]
        assert execution_result["success"] is True
        assert "No imports added" in execution_result["stdout"]
    
    def test_list_output_files(self):
        """Test listing output files."""
        # First execute a script that creates files
        script = '''
with open("file1.txt", "w") as f:
    f.write("content1")
    
import os
os.makedirs("subdir", exist_ok=True)
with open("subdir/file2.txt", "w") as f:
    f.write("content2")
'''
        
        self.provider.execute_python_script(script)
        result = self.provider.list_output_files()
        
        assert result["success"] is True
        assert "files" in result
        files = result["files"]
        
        # Should find at least the files we created
        file_paths = [f["path"] for f in files]
        assert any("file1.txt" in path for path in file_paths)
        assert any("subdir/file2.txt" in path or "subdir\\file2.txt" in path for path in file_paths)
    
    def test_download_file_text(self):
        """Test downloading a text file."""
        # Create a file first
        script = '''
with open("test.txt", "w") as f:
    f.write("Hello World\\nLine 2")
'''
        
        self.provider.execute_python_script(script)
        result = self.provider.download_file("test.txt", encoding="text")
        
        assert result["success"] is True
        assert result["content"] == "Hello World\\nLine 2"
        assert result["encoding"] == "text"
        assert result["size"] > 0
    
    def test_download_file_base64(self):
        """Test downloading a file as base64."""
        # Create a binary file
        script = '''
with open("test.bin", "wb") as f:
    f.write(b"\\x00\\x01\\x02\\x03")
'''
        
        self.provider.execute_python_script(script)
        result = self.provider.download_file("test.bin", encoding="base64")
        
        assert result["success"] is True
        assert result["encoding"] == "base64"
        
        # Decode and verify content
        decoded = base64.b64decode(result["content"])
        assert decoded == b"\\x00\\x01\\x02\\x03"
    
    def test_download_nonexistent_file(self):
        """Test downloading a file that doesn't exist."""
        # Ensure we have a workspace
        self.provider.execute_python_script('print("setup workspace")')
        
        result = self.provider.download_file("nonexistent.txt")
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()
    
    def test_upload_file_text(self):
        """Test uploading a text file."""
        content = "This is uploaded content\\nWith multiple lines"
        
        result = self.provider.upload_file("uploaded.txt", content, encoding="text")
        
        assert result["success"] is True
        assert result["file_path"] == "uploaded.txt"
        assert self.provider.current_workspace is not None
        
        # Verify the file was created
        file_path = self.provider.current_workspace / "uploaded.txt"
        assert file_path.exists()
        assert file_path.read_text() == content
    
    def test_upload_file_base64(self):
        """Test uploading a binary file as base64."""
        binary_data = b"\\x00\\x01\\x02\\x03"
        content = base64.b64encode(binary_data).decode()
        
        result = self.provider.upload_file("uploaded.bin", content, encoding="base64")
        
        assert result["success"] is True
        
        # Verify the file was created with correct content
        file_path = self.provider.current_workspace / "uploaded.bin"
        assert file_path.exists()
        assert file_path.read_bytes() == binary_data
    
    def test_upload_file_with_subdirectory(self):
        """Test uploading a file to a subdirectory."""
        content = "Content in subdirectory"
        
        result = self.provider.upload_file("subdir/nested.txt", content, encoding="text")
        
        assert result["success"] is True
        
        # Verify the file and directory were created
        file_path = self.provider.current_workspace / "subdir" / "nested.txt"
        assert file_path.exists()
        assert file_path.read_text() == content
    
    def test_get_execution_result(self):
        """Test getting execution result."""
        # First execute something
        script = 'print("Test execution")'
        self.provider.execute_python_script(script)
        
        result = self.provider.get_execution_result()
        
        assert result["success"] is True
        assert "execution_result" in result
        execution_result = result["execution_result"]
        assert execution_result["success"] is True
        assert "Test execution" in execution_result["stdout"]
    
    def test_get_execution_result_no_execution(self):
        """Test getting execution result when none exists."""
        result = self.provider.get_execution_result()
        
        assert result["success"] is False
        assert "No execution result" in result["error"]
    
    def test_reset_workspace(self):
        """Test resetting workspace."""
        # Create workspace and files
        script = 'open("test.txt", "w").write("test")'
        self.provider.execute_python_script(script)
        
        old_workspace = self.provider.current_workspace
        assert old_workspace is not None
        assert old_workspace.exists()
        
        # Reset workspace
        result = self.provider.reset_workspace(cleanup_current=True)
        
        assert result["success"] is True
        assert self.provider.current_workspace is None
        assert self.provider.last_execution is None
        # Workspace should be cleaned up
        assert not old_workspace.exists()
    
    def test_reset_workspace_no_cleanup(self):
        """Test resetting workspace without cleanup."""
        # Create workspace and files
        script = 'open("test.txt", "w").write("test")'
        self.provider.execute_python_script(script)
        
        old_workspace = self.provider.current_workspace
        
        # Reset without cleanup
        result = self.provider.reset_workspace(cleanup_current=False)
        
        assert result["success"] is True
        assert self.provider.current_workspace is None
        # Workspace should still exist
        assert old_workspace.exists()
    
    def test_get_workspace_info(self):
        """Test getting workspace information."""
        result = self.provider.get_workspace_info()
        
        assert result["success"] is True
        assert result["current_workspace"] is None
        assert str(self.temp_dir) in result["base_workspace_dir"]
        assert result["execution_timeout"] == 30
        assert result["has_last_execution"] is False
        
        # After executing something
        self.provider.execute_python_script('print("test")')
        result = self.provider.get_workspace_info()
        
        assert result["current_workspace"] is not None
        assert result["has_last_execution"] is True
    
    def test_script_hash_generation(self):
        """Test that script hashes are generated correctly."""
        script1 = 'print("hello")'
        script2 = 'print("world")'
        
        result1 = self.provider.execute_python_script(script1)
        result2 = self.provider.execute_python_script(script2)
        
        hash1 = result1["execution_result"]["script_hash"]
        hash2 = result2["execution_result"]["script_hash"]
        
        assert hash1 != hash2
        assert len(hash1) == 16  # We truncate to 16 chars
        assert len(hash2) == 16
    
    def test_execution_timeout(self):
        """Test script execution timeout."""
        # Use a very short timeout for this test
        provider = ScriptExecutorMCPProvider(
            base_workspace_dir=self.temp_dir,
            execution_timeout=1  # 1 second timeout
        )
        
        # Script that runs longer than timeout
        script = '''
import time
time.sleep(2)  # Sleep for 2 seconds
print("This should not print")
'''
        
        result = provider.execute_python_script(script)
        
        assert result["success"] is False
        assert "timed out" in result["error"].lower()
    
    def test_cleanup_workspace_on_execution(self):
        """Test cleanup workspace option during execution."""
        script = 'open("test.txt", "w").write("test")'
        
        result = self.provider.execute_python_script(script, cleanup_workspace=True)
        
        assert result["success"] is True
        # Workspace should be cleaned up
        assert self.provider.current_workspace is None


class TestMCPServerCreation:
    """Test MCP server creation."""
    
    def test_server_creation(self):
        """Test that the MCP server can be created."""
        server = create_mcp_server()
        
        assert server is not None
        # Verify tools are registered
        tools = server._tool_manager._tools
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
            assert tool_name in tools
    
    def test_server_with_custom_params(self):
        """Test server creation with custom parameters."""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            server = create_mcp_server(
                base_workspace_dir=temp_dir,
                execution_timeout=60
            )
            
            assert server is not None
            
            # Test that the provider was configured correctly
            # We can't easily access the provider instance, but we can test
            # that the server was created without errors
            
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)


class TestLoadSetIntegration:
    """Test integration with LoadSet functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.provider = ScriptExecutorMCPProvider(
            base_workspace_dir=self.temp_dir,
            execution_timeout=60
        )
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_loadset_imports_available(self):
        """Test that LoadSet imports are available in scripts."""
        script = '''
# Test that LoadSet classes are available
print(f"LoadSet: {LoadSet}")
print(f"LoadCase: {LoadCase}")
print(f"PointLoad: {PointLoad}")
print(f"ForceMoment: {ForceMoment}")

# Test numpy availability
print(f"numpy: {np}")
print(f"matplotlib: {plt}")
'''
        
        result = self.provider.execute_python_script(script, include_loadset_imports=True)
        
        assert result["success"] is True
        execution_result = result["execution_result"]
        assert execution_result["success"] is True
        
        stdout = execution_result["stdout"]
        assert "LoadSet:" in stdout
        assert "LoadCase:" in stdout
        assert "PointLoad:" in stdout
        assert "ForceMoment:" in stdout
        assert "numpy:" in stdout
        assert "matplotlib:" in stdout
    
    def test_simple_loadset_script(self):
        """Test a simple script that uses LoadSet functionality."""
        script = '''
# Create a simple LoadSet for testing
from pathlib import Path

# Create a minimal LoadSet JSON for testing
test_data = {
    "name": "Test LoadSet",
    "version": 1,
    "units": {
        "forces": "N",
        "moments": "Nm"
    },
    "description": "Test LoadSet for script execution",
    "load_cases": [
        {
            "name": "Test Case",
            "description": "Test load case",
            "point_loads": [
                {
                    "name": "Point A",
                    "force_moment": {
                        "fx": 100.0, "fy": 200.0, "fz": 300.0,
                        "mx": 10.0, "my": 20.0, "mz": 30.0
                    }
                }
            ]
        }
    ]
}

# Write test data
import json
Path("test_loadset.json").write_text(json.dumps(test_data, indent=2))

# Load with LoadSet
loadset = LoadSet.read_json("test_loadset.json")
print(f"Loaded LoadSet: {loadset.name}")
print(f"Units: {loadset.units.forces} / {loadset.units.moments}")
print(f"Load cases: {len(loadset.load_cases)}")

# Convert units
converted = loadset.convert_to("kN")
print(f"Converted to: {converted.units.forces} / {converted.units.moments}")

# Export result
result_data = converted.model_dump()
Path("converted_loadset.json").write_text(json.dumps(result_data, indent=2))
print("Conversion completed and saved!")
'''
        
        result = self.provider.execute_python_script(script, include_loadset_imports=True)
        
        assert result["success"] is True
        execution_result = result["execution_result"]
        assert execution_result["success"] is True
        
        stdout = execution_result["stdout"]
        assert "Loaded LoadSet: Test LoadSet" in stdout
        assert "Converted to: kN" in stdout
        assert "Conversion completed" in stdout
        
        # Check that output files were created
        output_files = execution_result["output_files"]
        assert any("test_loadset.json" in f for f in output_files)
        assert any("converted_loadset.json" in f for f in output_files)


if __name__ == "__main__":
    pytest.main([__file__])