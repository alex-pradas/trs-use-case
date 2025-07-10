import asyncio
from pathlib import Path
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio
import logfire
from dotenv import load_dotenv

load_dotenv()


mcp_loads = MCPServerStdio(
    "/opt/homebrew/bin/uv",
    args=[
        "--directory",
        "/Users/alex/repos/trs-use-case",
        "run",
        "python",
        "tools/mcp_server.py",
    ],
)


loads_agent = Agent(
    "anthropic:claude-4-sonnet-20250514",
    mcp_servers=[mcp_loads],
)


async def main():
    # Start the MCP server connection
    async with mcp_loads:
        user_prompt = """Please help me process the loads in solution/loads/new_loads.json. 
        Factor by 1.5 and convert to klbf. Generate files for ansys in a subfolder called output."""

        result = await loads_agent.run(user_prompt)

        print(f"✅ Agent response: {result}")

        # Show generated files in output folder
        output_folder = Path("output")
        if output_folder.exists():
            ansys_files = list(output_folder.glob("*.inp"))
            print(f"\n📊 Generated {len(ansys_files)} ANSYS files:")
            for file in ansys_files[:5]:  # Show first 5
                print(f"  - {file.name}")
            if len(ansys_files) > 5:
                print(f"  ... and {len(ansys_files) - 5} more files")
        else:
            print("No output folder found")


if __name__ == "__main__":
    logfire.configure()
    logfire.instrument_pydantic_ai()
    asyncio.run(main())
