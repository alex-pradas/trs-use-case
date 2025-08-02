import asyncio
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai import Agent
from dotenv import load_dotenv
from pydantic import BaseModel

class CityLocation(BaseModel):
    city: str
    country: str

load_dotenv()

async def main():
    print("🚀 Testing with increased retry limit")
    
    model_name = "accounts/fireworks/models/kimi-k2-instruct"
    # model_name = "accounts/fireworks/models/qwen3-coder-480b-a35b-instruct"
    
    model = OpenAIModel(model_name, provider="fireworks")
    
    # Increase max_result_retries to handle validation failures
    agent = Agent(
        model,
        output_type=CityLocation,
        retries=5,
        # max_result_retries=5,  # Increase from default 1 to 5
    )

    try:
        print("Testing with structured output and increased retries...")
        response = await agent.run("Where were the 2012 Olympics?")
        print(f"✅ Success: {response.output}")
        print(f"Type: {type(response.output)}")
        print(f"Usage: {response.usage()}")
    except Exception as e:
        print(f"❌ Failed after retries: {e}")
        
        # Try without structured output as fallback
        print("\nTrying without structured output...")
        fallback_agent = Agent(model)
        response = await fallback_agent.run("Where were the 2012 Olympics?")
        print(f"Fallback result: {response.output}")

if __name__ == "__main__":
    asyncio.run(main())