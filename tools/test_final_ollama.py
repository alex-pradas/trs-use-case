import asyncio
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

class CityLocation(BaseModel):
    city: str
    country: str

async def test_tool_support():
    """Quick test of working Ollama configuration."""

    # SOLUTION: Use hf.co/unsloth/Qwen3-30B-A3B-Thinking-2507-GGUF:latest which supports tools
    model_name = "hf.co/unsloth/Qwen3-30B-A3B-Thinking-2507-GGUF:latest"

    print(f"✅ Using {model_name} (supports tools)")
    
    ollama_model = OpenAIModel(
        model_name=model_name,
        provider=OpenAIProvider(base_url='http://localhost:11434/v1')
    )
    
    # Test structured output
    agent = Agent(ollama_model, output_type=CityLocation)
    result = await agent.run("Where were the 2012 Olympics?")
    
    print(f"Result: {result.output}")
    print(f"Type: {type(result.output)}")
    print("🎉 SUCCESS: Tools and structured output working!")

if __name__ == "__main__":
    asyncio.run(test_tool_support())