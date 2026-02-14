"""
Provider factory module.

Provides a factory function that returns the appropriate provider instance
based on the provider name from the model configuration. Provider instances
are cached (singleton pattern) to avoid re-initializing clients on every request.
"""

import logging
from typing import Dict

from services.base_provider import BaseProvider
from services.openai_provider import OpenAIProvider
from services.azure_openai_provider import AzureOpenAIProvider
from services.anthropic_provider import AnthropicProvider
from services.bedrock_provider import BedrockProvider

logger = logging.getLogger(__name__)

# Cache for provider instances (singleton per provider type)
_provider_cache: Dict[str, BaseProvider] = {}


def get_provider(provider_name: str) -> BaseProvider:
    """
    Return the appropriate provider instance for the given provider name.

    Provider instances are lazily initialized and cached so that the
    underlying API clients are created only once per provider type.

    Args:
        provider_name: One of 'OpenAI', 'Azure OpenAI', 'Anthropic',
                       or 'AWS Bedrock'.

    Returns:
        An instance of the corresponding BaseProvider subclass.

    Raises:
        ValueError: If the provider name is not recognized.
    """
    # Normalize the provider name for consistent cache keys
    key = provider_name.strip().lower()

    if key in _provider_cache:
        return _provider_cache[key]

    provider_map = {
        "openai": OpenAIProvider,
        "azure openai": AzureOpenAIProvider,
        "anthropic": AnthropicProvider,
        "aws bedrock": BedrockProvider,
    }

    provider_class = provider_map.get(key)
    if provider_class is None:
        raise ValueError(
            f"Unknown provider '{provider_name}'. "
            f"Supported providers: {', '.join(provider_map.keys())}"
        )

    logger.info("Initializing provider: %s", provider_name)
    instance = provider_class()
    _provider_cache[key] = instance
    return instance
