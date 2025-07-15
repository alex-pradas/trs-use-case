"""
Model configuration for pydantic-ai agents.

This module provides a single point of configuration for model selection
across all agents, following pydantic-ai best practices.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Single model selection via environment variable
# Supports any pydantic-ai compatible model string:
# - anthropic:claude-3-5-sonnet-latest
# - fireworks:accounts/fireworks/models/llama-v3p3-70b-instruct  
# - openai:gpt-4o
# - google-gla:gemini-1.5-flash
MODEL_NAME = os.getenv("AI_MODEL", "anthropic:claude-3-5-sonnet-latest")


def get_model_name() -> str:
    """Get the currently configured model name."""
    return MODEL_NAME


def is_anthropic_model() -> bool:
    """Check if current model is an Anthropic model."""
    return MODEL_NAME.startswith("anthropic:")


def is_fireworks_model() -> bool:
    """Check if current model is a FIREWORKS model."""
    return MODEL_NAME.startswith("fireworks:")


def is_openai_model() -> bool:
    """Check if current model is an OpenAI model."""
    return MODEL_NAME.startswith("openai:")


def get_provider_name() -> str:
    """Get the provider name from the model string."""
    if ":" in MODEL_NAME:
        return MODEL_NAME.split(":", 1)[0]
    return "unknown"


def get_model_id() -> str:
    """Get the model ID without the provider prefix."""
    if ":" in MODEL_NAME:
        return MODEL_NAME.split(":", 1)[1]
    return MODEL_NAME


def validate_model_config() -> tuple[bool, Optional[str]]:
    """
    Validate that the model is properly configured.
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not MODEL_NAME:
        return False, "AI_MODEL environment variable not set"
    
    provider = get_provider_name()
    
    # Check for required API keys based on provider
    if provider == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY"):
            return False, "ANTHROPIC_API_KEY required for Anthropic models"
    elif provider == "fireworks":
        if not os.getenv("FIREWORKS_API_KEY"):
            return False, "FIREWORKS_API_KEY required for FIREWORKS models"
    elif provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            return False, "OPENAI_API_KEY required for OpenAI models"
    elif provider == "google-gla":
        if not os.getenv("GOOGLE_API_KEY"):
            return False, "GOOGLE_API_KEY required for Google models"
    else:
        return False, f"Unknown provider: {provider}"
    
    return True, None


if __name__ == "__main__":
    print("🤖 AI Model Configuration")
    print("=" * 30)
    print(f"Model: {get_model_name()}")
    print(f"Provider: {get_provider_name()}")
    print(f"Model ID: {get_model_id()}")
    
    is_valid, error = validate_model_config()
    if is_valid:
        print("✅ Configuration is valid")
    else:
        print(f"❌ Configuration error: {error}")