"""
FIREWORKS AI client configuration for pydantic-ai.

This module provides utilities to configure and use FIREWORKS AI models
with pydantic-ai, offering an alternative to Anthropic Claude models.
"""

import os
from typing import Optional, Union
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

# Load environment variables
load_dotenv()


class FireworksConfig:
    """Configuration class for FIREWORKS AI models."""
    
    # Available FIREWORKS models (verified working)
    LLAMA_3_3_70B_INSTRUCT = "accounts/fireworks/models/llama-v3p3-70b-instruct"
    LLAMA_3_1_70B_INSTRUCT = "accounts/fireworks/models/llama-v3p1-70b-instruct"
    
    # Default model for code generation
    DEFAULT_CODE_MODEL = LLAMA_3_3_70B_INSTRUCT
    
    @staticmethod
    def get_api_key() -> Optional[str]:
        """Get FIREWORKS API key from environment."""
        return os.getenv("FIREWORKS_API_KEY")
    
    @staticmethod
    def is_configured() -> bool:
        """Check if FIREWORKS is properly configured."""
        return FireworksConfig.get_api_key() is not None


def create_fireworks_model(
    model_name: str = FireworksConfig.DEFAULT_CODE_MODEL,
    api_key: Optional[str] = None,
    **kwargs
) -> OpenAIModel:
    """
    Create a FIREWORKS AI model using pydantic-ai's OpenAIModel.
    
    Args:
        model_name: FIREWORKS model identifier (defaults to Llama 3.3 70B)
        api_key: Optional API key (defaults to FIREWORKS_API_KEY env var)
        **kwargs: Additional arguments passed to OpenAIModel
        
    Returns:
        Configured OpenAIModel instance for FIREWORKS
        
    Raises:
        ValueError: If API key is not available
    """
    if api_key is None:
        api_key = FireworksConfig.get_api_key()
    
    if not api_key:
        raise ValueError(
            "FIREWORKS_API_KEY not found. Please set it in your .env file or pass it explicitly."
        )
    
    # Set the API key in environment for the provider to pick up
    os.environ["FIREWORKS_API_KEY"] = api_key
    
    # Note: Model parameters like temperature are set during agent.run() calls
    # not during model initialization
    return OpenAIModel(
        model_name,
        provider="fireworks"
    )


def create_fireworks_agent(
    system_prompt: str,
    model_name: str = FireworksConfig.DEFAULT_CODE_MODEL,
    api_key: Optional[str] = None,
    **kwargs
) -> Agent:
    """
    Create a pydantic-ai Agent using FIREWORKS AI.
    
    Args:
        system_prompt: System prompt for the agent
        model_name: FIREWORKS model identifier
        api_key: Optional API key
        **kwargs: Additional arguments passed to model creation
        
    Returns:
        Configured Agent instance using FIREWORKS
    """
    model = create_fireworks_model(model_name, api_key, **kwargs)
    return Agent(model, system_prompt=system_prompt)


def create_code_generation_agent(
    api_key: Optional[str] = None,
    model_name: str = FireworksConfig.DEFAULT_CODE_MODEL,
    **kwargs
) -> Agent:
    """
    Create an agent specifically optimized for code generation using FIREWORKS.
    
    Args:
        api_key: Optional API key
        model_name: FIREWORKS model identifier
        **kwargs: Additional arguments
        
    Returns:
        Agent configured for code generation
    """
    system_prompt = """
    You are an expert Python programmer with deep knowledge of software engineering best practices.
    
    When writing code:
    - Write clean, readable, and well-documented code
    - Follow PEP 8 style guidelines
    - Include proper error handling
    - Add type hints where appropriate
    - Explain your reasoning for complex logic
    - Prefer standard library solutions when possible
    
    When solving problems:
    - Break down complex problems into smaller steps
    - Consider edge cases and error conditions
    - Write code that is maintainable and testable
    - Provide examples of how to use the code
    
    Always execute and test your code when possible to ensure it works correctly.
    """
    
    return create_fireworks_agent(
        system_prompt=system_prompt,
        model_name=model_name,
        api_key=api_key,
        **kwargs
    )


# Convenience functions for common use cases
def get_default_fireworks_model() -> OpenAIModel:
    """Get a default FIREWORKS model instance."""
    return create_fireworks_model()


def get_code_generation_model() -> OpenAIModel:
    """Get a FIREWORKS model optimized for code generation."""
    return create_fireworks_model(
        model_name=FireworksConfig.DEFAULT_CODE_MODEL
    )


# Model information for users (verified working models only)
AVAILABLE_MODELS = {
    "llama-3.3-70b": {
        "name": FireworksConfig.LLAMA_3_3_70B_INSTRUCT,  
        "description": "Llama 3.3 70B Instruct - Latest model with improved coding capabilities",
        "use_case": "Advanced coding, tool calling, multilingual support"
    },
    "llama-3.1-70b": {
        "name": FireworksConfig.LLAMA_3_1_70B_INSTRUCT,
        "description": "Llama 3.1 70B Instruct - Enhanced reasoning and long context",
        "use_case": "Long context reasoning, complex analysis"
    }
}


def list_available_models() -> dict:
    """Return information about available FIREWORKS models."""
    return AVAILABLE_MODELS


if __name__ == "__main__":
    # Quick test of configuration
    print("🔥 FIREWORKS AI Configuration Test")
    print("=" * 40)
    
    if FireworksConfig.is_configured():
        print("✅ FIREWORKS_API_KEY found")
        print(f"🔑 Key length: {len(FireworksConfig.get_api_key())} characters")
        
        try:
            model = get_default_fireworks_model()
            print(f"✅ Default model created: {FireworksConfig.DEFAULT_CODE_MODEL}")
            
            print("\n📋 Available Models:")
            for key, info in AVAILABLE_MODELS.items():
                print(f"  {key}: {info['description']}")
                
        except Exception as e:
            print(f"❌ Error creating model: {e}")
    else:
        print("❌ FIREWORKS_API_KEY not found in environment")
        print("   Please add FIREWORKS_API_KEY to your .env file")