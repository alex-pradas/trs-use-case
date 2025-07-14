#!/usr/bin/env python3
"""
Demo of the Script Generation Agent for LoadSet processing.

This script demonstrates the complete workflow:
1. Agent receives natural language instruction
2. Agent generates Python script
3. Agent executes script via MCP server
4. Agent downloads output files to local filesystem
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Add tools directory to path
import sys
tools_dir = Path(__file__).parent / "tools"
sys.path.insert(0, str(tools_dir))

from tools.script_exec_mcp_server import create_mcp_server
from tools.script_agent_client import ScriptGenerationAgent

# Load environment variables
load_dotenv()


async def demo_basic_processing():
    """Demo basic LoadSet processing workflow."""
    print("🚀 Script Generation Agent Demo - Basic Processing")
    print("=" * 60)
    
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY not available - cannot run agent demo")
        return
    
    # Create MCP server and agent
    server = create_mcp_server()
    agent = ScriptGenerationAgent(server, output_directory=Path("demo_outputs/basic"))
    
    instruction = """
    Process aerospace load data with these steps:
    1. Load LoadSet from 'solution/loads/new_loads.json'
    2. Show the current units and number of load cases
    3. Convert units to kN if not already in kN
    4. Scale all loads by a factor of 1.25
    5. Export the processed data to ANSYS format files
    6. Create a JSON summary with processing details
    """
    
    print(f"📝 Instruction:")
    print(f"   {instruction.strip()}")
    print("\n🤖 Processing with AI agent...")
    
    result = await agent.process_load_instruction(instruction)
    
    if result["success"]:
        print("✅ Processing completed successfully!")
        print(f"\n📁 Output directory: {result['output_directory']}")
        print(f"📄 Downloaded files: {len(result['downloaded_files'])}")
        
        for file_info in result["downloaded_files"]:
            print(f"  - {Path(file_info['local_path']).name} ({file_info['size']} bytes)")
        
        print(f"\n🤖 Agent Response Summary:")
        response_lines = result['agent_response'].split('\n')[:5]  # First 5 lines
        for line in response_lines:
            if line.strip():
                print(f"   {line}")
        if len(result['agent_response'].split('\n')) > 5:
            print("   ...")
    else:
        print(f"❌ Processing failed: {result['error']}")


async def demo_comparison_workflow():
    """Demo LoadSet comparison workflow."""
    print("\n🚀 Script Generation Agent Demo - Comparison Workflow")
    print("=" * 60)
    
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY not available - cannot run agent demo")
        return
    
    # Create MCP server and agent
    server = create_mcp_server()
    agent = ScriptGenerationAgent(server, output_directory=Path("demo_outputs/comparison"))
    
    instruction = """
    Compare two aerospace LoadSet files:
    1. Load 'solution/loads/new_loads.json' and 'solution/loads/old_loads.json'
    2. Perform detailed comparison between the datasets
    3. Generate comparison statistics showing key differences
    4. Export comparison results to JSON format
    5. Create a human-readable summary report
    6. Identify the load case with the largest differences
    """
    
    print(f"📝 Instruction:")
    print(f"   {instruction.strip()}")
    print("\n🤖 Processing with AI agent...")
    
    result = await agent.process_load_instruction(instruction)
    
    if result["success"]:
        print("✅ Comparison completed successfully!")
        print(f"\n📁 Output directory: {result['output_directory']}")
        print(f"📄 Downloaded files: {len(result['downloaded_files'])}")
        
        for file_info in result["downloaded_files"]:
            print(f"  - {Path(file_info['local_path']).name} ({file_info['size']} bytes)")
        
        print(f"\n🤖 Agent Response Summary:")
        response_lines = result['agent_response'].split('\n')[:5]
        for line in response_lines:
            if line.strip():
                print(f"   {line}")
        if len(result['agent_response'].split('\n')) > 5:
            print("   ...")
    else:
        print(f"❌ Comparison failed: {result['error']}")


async def demo_unit_analysis_workflow():
    """Demo unit conversion analysis workflow."""
    print("\n🚀 Script Generation Agent Demo - Unit Analysis Workflow")
    print("=" * 60)
    
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY not available - cannot run agent demo")
        return
    
    # Create MCP server and agent
    server = create_mcp_server()
    agent = ScriptGenerationAgent(server, output_directory=Path("demo_outputs/unit_analysis"))
    
    instruction = """
    Perform comprehensive unit analysis on aerospace load data:
    1. Load LoadSet from 'solution/loads/new_loads.json'
    2. Convert the data to three different unit systems: kN, lbf, and klbf
    3. For each unit system, save the converted LoadSet to a separate JSON file
    4. Create a comparison table showing sample force values in each unit system
    5. Calculate and show the conversion factors used
    6. Generate a detailed analysis report with unit conversion insights
    """
    
    print(f"📝 Instruction:")
    print(f"   {instruction.strip()}")
    print("\n🤖 Processing with AI agent...")
    
    result = await agent.process_load_instruction(instruction)
    
    if result["success"]:
        print("✅ Unit analysis completed successfully!")
        print(f"\n📁 Output directory: {result['output_directory']}")
        print(f"📄 Downloaded files: {len(result['downloaded_files'])}")
        
        for file_info in result["downloaded_files"]:
            print(f"  - {Path(file_info['local_path']).name} ({file_info['size']} bytes)")
        
        print(f"\n🤖 Agent Response Summary:")
        response_lines = result['agent_response'].split('\n')[:5]
        for line in response_lines:
            if line.strip():
                print(f"   {line}")
        if len(result['agent_response'].split('\n')) > 5:
            print("   ...")
    else:
        print(f"❌ Unit analysis failed: {result['error']}")


async def demo_custom_workflow():
    """Demo custom analysis workflow."""
    print("\n🚀 Script Generation Agent Demo - Custom Analysis Workflow")
    print("=" * 60)
    
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY not available - cannot run agent demo")
        return
    
    # Create MCP server and agent
    server = create_mcp_server()
    agent = ScriptGenerationAgent(server, output_directory=Path("demo_outputs/custom"))
    
    instruction = """
    Create a comprehensive aerospace load analysis report:
    1. Load LoadSet from 'solution/loads/new_loads.json'
    2. Calculate force magnitude statistics for each load case (min, max, mean, std)
    3. Identify the load case with maximum total force magnitude
    4. Create a load case summary table with point counts and force ranges
    5. Generate force distribution histograms using matplotlib
    6. Export all analysis results to well-structured JSON files
    7. Create a professional analysis report in text format
    """
    
    print(f"📝 Instruction:")
    print(f"   {instruction.strip()}")
    print("\n🤖 Processing with AI agent...")
    
    result = await agent.process_load_instruction(instruction)
    
    if result["success"]:
        print("✅ Custom analysis completed successfully!")
        print(f"\n📁 Output directory: {result['output_directory']}")
        print(f"📄 Downloaded files: {len(result['downloaded_files'])}")
        
        for file_info in result["downloaded_files"]:
            print(f"  - {Path(file_info['local_path']).name} ({file_info['size']} bytes)")
        
        print(f"\n🤖 Agent Response Summary:")
        response_lines = result['agent_response'].split('\n')[:5]
        for line in response_lines:
            if line.strip():
                print(f"   {line}")
        if len(result['agent_response'].split('\n')) > 5:
            print("   ...")
    else:
        print(f"❌ Custom analysis failed: {result['error']}")


async def main():
    """Run all demo workflows."""
    print("🎯 Script Generation Agent Complete Demo")
    print("=" * 60)
    print("This demo shows the AI agent generating and executing Python scripts")
    print("for various aerospace load processing workflows.\n")
    
    # Create output directory
    output_dir = Path("demo_outputs")
    output_dir.mkdir(exist_ok=True)
    
    try:
        # Run demo workflows
        await demo_basic_processing()
        await demo_comparison_workflow()
        await demo_unit_analysis_workflow()
        await demo_custom_workflow()
        
        print("\n🎉 All demo workflows completed!")
        print(f"📁 Check the 'demo_outputs/' directory for all generated files")
        print("\nKey achievements demonstrated:")
        print("  ✅ AI agent generates Python scripts from natural language")
        print("  ✅ Scripts execute in isolated workspaces with LoadSet integration")
        print("  ✅ Output files automatically downloaded to local filesystem")
        print("  ✅ Complete workflows from instruction to file delivery")
        print("  ✅ Real aerospace data processing with unit conversion and scaling")
        print("  ✅ LoadSet comparison and analysis capabilities")
        print("  ✅ ANSYS export and custom analysis workflows")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")


if __name__ == "__main__":
    asyncio.run(main())