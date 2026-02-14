"""
Anthropic Claude provider module.

Handles communication with the Anthropic Messages API for text and multimodal
(text + image) completions using the official Anthropic Python SDK.

Environment Variables:
    ANTHROPIC_API_KEY: API key for authenticating with Anthropic.
"""

import os
import logging
from typing import Optional

import anthropic

from services.base_provider import BaseProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    """
    Provider implementation for the Anthropic Claude API.

    Uses the Anthropic Python SDK to interact with Claude models
    such as Claude Sonnet 4 and Claude 3.5 Haiku.
    """

    def __init__(self):
        """Initialize the Anthropic client with the API key from environment."""
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")
        self.client = anthropic.Anthropic(api_key=api_key)
        logger.info("Anthropic provider initialized successfully.")

    def generate_text(
        self, prompt: str, model_name: str, temperature: float
    ) -> str:
        """
        Generate a text response using the Anthropic Messages API.

        Args:
            prompt: The user's text prompt.
            model_name: Anthropic model identifier (e.g., 'claude-sonnet-4-20250514').
            temperature: Sampling temperature (0.0 to 1.0).

        Returns:
            The model's text response.
        """
        logger.info(
            "Anthropic text generation: model=%s, temperature=%.2f",
            model_name,
            temperature,
        )

        message = self.client.messages.create(
            model=model_name,
            max_tokens=4096,
            temperature=temperature,
            messages=[
                {"role": "user", "content": prompt}
            ],
        )

        # Extract text from the response content blocks
        return "".join(
            block.text for block in message.content if block.type == "text"
        )

    def generate_with_image(
        self,
        prompt: str,
        image_content: str,
        model_name: str,
        temperature: float,
        image_media_type: Optional[str] = None,
    ) -> str:
        """
        Generate a text response from a text + image prompt via Anthropic.

        Anthropic's API expects images as base64-encoded data with a
        specified media type.

        Args:
            prompt: The user's text prompt.
            image_content: Base64-encoded image data.
            model_name: Anthropic model identifier.
            temperature: Sampling temperature (0.0 to 1.0).
            image_media_type: MIME type (e.g., 'image/png'). Defaults to 'image/png'.

        Returns:
            The model's text response.
        """
        logger.info(
            "Anthropic vision generation: model=%s, temperature=%.2f",
            model_name,
            temperature,
        )

        media_type = image_media_type or "image/png"

        # If a URL is provided, the Anthropic API supports source type "url"
        if image_content.startswith("http"):
            image_source = {
                "type": "url",
                "url": image_content,
            }
        else:
            image_source = {
                "type": "base64",
                "media_type": media_type,
                "data": image_content,
            }

        message = self.client.messages.create(
            model=model_name,
            max_tokens=4096,
            temperature=temperature,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": image_source,
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
        )

        return "".join(
            block.text for block in message.content if block.type == "text"
        )
