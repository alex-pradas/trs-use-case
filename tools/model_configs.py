"""
Multi-model configuration system for pydantic-ai agents.

This module provides centralized configuration for multiple AI models including
Anthropic, Fireworks, and Ollama models with their specific provider setups.
"""

from typing import Dict, Any, Optional
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider


class ModelConfig:
    """Configuration for a specific AI model."""
    
    def __init__(
        self,
        model_name: str,
        provider: Optional[str] = None,
        provider_kwargs: Optional[Dict[str, Any]] = None,
        description: str = ""
    ):
        self.model_name = model_name
        self.provider = provider
        self.provider_kwargs = provider_kwargs or {}
        self.description = description
    
    def create_model(self) -> str | OpenAIModel:
        """Create the appropriate model instance based on configuration."""
        if self.provider == "fireworks":
            # Fireworks models use the simple string format with provider prefix
            return f"fireworks:{self.model_name}"
        
        elif self.provider == "ollama":
            # Ollama models need custom OpenAI provider setup
            provider = OpenAIProvider(
                base_url='http://localhost:11434/v1',
                **self.provider_kwargs
            )
            return OpenAIModel(self.model_name, provider=provider)
        
        else:
            # Standard models (Anthropic, OpenAI, etc.) use simple string format
            return self.model_name


# Centralized model configurations
MODEL_CONFIGS: Dict[str, ModelConfig] = {
    # Anthropic Models
    "haiku": ModelConfig(
        model_name="anthropic:claude-3-haiku-20240307",
        description="Anthropic Claude 3 Haiku - Fast and efficient"
    ),
    
    "sonnet4": ModelConfig(
        model_name="anthropic:claude-4-sonnet-20250514", 
        description="Anthropic Claude 4 Sonnet - High capability"
    ),
    
    # Fireworks Models
    "kimi": ModelConfig(
        model_name="accounts/fireworks/models/kimi-k2-instruct",
        provider="fireworks",
        description="Moonshot AI Kimi K2 Instruct via Fireworks"
    ),
    
    "qwen-coder": ModelConfig(
        model_name="accounts/fireworks/models/qwen3-coder-480b-a35b-instruct",
        provider="fireworks", 
        description="Qwen3 Coder 480B A35B Instruct via Fireworks"
    ),
    
    # Ollama Models  
    "qwen-thinking": ModelConfig(
        model_name="hf.co/unsloth/Qwen3-30B-A3B-Thinking-2507-GGUF:latest",
        provider="ollama",
        description="Qwen3 30B A3B Thinking via Ollama (supports tools)"
    ),
}


def get_model_config(model_key: str) -> ModelConfig:
    """Get model configuration by key."""
    if model_key not in MODEL_CONFIGS:
        raise ValueError(f"Unknown model key: {model_key}. Available: {list(MODEL_CONFIGS.keys())}")
    return MODEL_CONFIGS[model_key]


def list_available_models() -> Dict[str, str]:
    """List all available model keys and their descriptions."""
    return {key: config.description for key, config in MODEL_CONFIGS.items()}


def create_model_from_key(model_key: str) -> str | OpenAIModel:
    """Create a model instance from a simple key."""
    config = get_model_config(model_key)
    return config.create_model()


def is_valid_model_key(model_key: str) -> bool:
    """Check if a model key is valid."""
    return model_key in MODEL_CONFIGS


def get_provider_type(model_key: str) -> str:
    """Get the provider type for a model key."""
    if not is_valid_model_key(model_key):
        return "unknown"
    return MODEL_CONFIGS[model_key].provider or "standard"


if __name__ == "__main__":
    print("🤖 Available AI Models")
    print("=" * 50)
    
    for key, description in list_available_models().items():
        provider = get_provider_type(key)
        print(f"  {key:<15} | {provider:<10} | {description}")
    
    print("\n🔧 Testing Model Creation")
    print("=" * 50)
    
    for key in MODEL_CONFIGS.keys():
        try:
            model = create_model_from_key(key)
            model_type = type(model).__name__ if hasattr(model, '__class__') else 'str'
            print(f"  ✅ {key:<15} → {model_type}")
        except Exception as e:
            print(f"  ❌ {key:<15} → Error: {e}")