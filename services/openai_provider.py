"""
OpenAI provider module.

Handles communication with the OpenAI API for text and multimodal
(text + image) completions using the official OpenAI Python SDK.

Environment Variables:
    OPENAI_API_KEY: API key for authenticating with OpenAI.
"""

import os
import logging
from typing import Optional

from openai import OpenAI

from services.base_provider import BaseProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """
    Provider implementation for the OpenAI API.

    Uses the OpenAI Python SDK to interact with models such as
    GPT-4o, GPT-4o Mini, and GPT-4 Turbo.
    """

    def __init__(self):
        """Initialize the OpenAI client with the API key from environment."""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")
        self.client = OpenAI(api_key=api_key)
        logger.info("OpenAI provider initialized successfully.")

    def generate_text(
        self, prompt: str, model_name: str, temperature: float
    ) -> str:
        """
        Generate a text response using the OpenAI Chat Completions API.

        Args:
            prompt: The user's text prompt.
            model_name: OpenAI model identifier (e.g., 'gpt-4o').
            temperature: Sampling temperature (0.0 to 2.0).

        Returns:
            The model's text response.
        """
        logger.info("OpenAI text generation: model=%s, temperature=%.2f", model_name, temperature)

        response = self.client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
        )

        return response.choices[0].message.content

    def generate_with_image(
        self,
        prompt: str,
        image_content: str,
        model_name: str,
        temperature: float,
        image_media_type: Optional[str] = None,
    ) -> str:
        """
        Generate a text response from a text + image prompt using OpenAI.

        The image can be provided as a base64-encoded string or a URL.
        If the image starts with 'http', it is treated as a URL; otherwise
        it is treated as base64 data.

        Args:
            prompt: The user's text prompt.
            image_content: Base64-encoded image data or image URL.
            model_name: OpenAI model identifier (e.g., 'gpt-4o').
            temperature: Sampling temperature (0.0 to 2.0).
            image_media_type: MIME type (e.g., 'image/png'). Defaults to 'image/png'.

        Returns:
            The model's text response.
        """
        logger.info(
            "OpenAI vision generation: model=%s, temperature=%.2f",
            model_name,
            temperature,
        )

        media_type = image_media_type or "image/png"

        # Determine if image_content is a URL or base64 data
        if image_content.startswith("http"):
            image_url = image_content
        else:
            image_url = f"data:{media_type};base64,{image_content}"

        response = self.client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                    ],
                }
            ],
            temperature=temperature,
        )

        return response.choices[0].message.content
