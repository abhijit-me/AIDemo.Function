"""
Azure OpenAI provider module.

Handles communication with the Azure OpenAI Service for text and multimodal
(text + image) completions using the official OpenAI Python SDK configured
for Azure endpoints.

Environment Variables:
    AZURE_OPENAI_API_KEY: API key for Azure OpenAI.
    AZURE_OPENAI_ENDPOINT: The Azure OpenAI resource endpoint URL.
    AZURE_OPENAI_API_VERSION: API version string (e.g., '2024-10-21').
"""

import os
import logging
from typing import Optional

from openai import AzureOpenAI

from services.base_provider import BaseProvider

logger = logging.getLogger(__name__)


class AzureOpenAIProvider(BaseProvider):
    """
    Provider implementation for Azure OpenAI Service.

    Uses the OpenAI Python SDK's AzureOpenAI client to interact with
    Azure-hosted deployments of GPT models.
    """

    def __init__(self):
        """Initialize the Azure OpenAI client with environment configuration."""
        api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21")

        if not api_key:
            raise ValueError("AZURE_OPENAI_API_KEY environment variable is not set.")
        if not endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is not set.")

        self.client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
        )
        logger.info("Azure OpenAI provider initialized successfully.")

    def generate_text(
        self, prompt: str, model_name: str, temperature: float
    ) -> str:
        """
        Generate a text response using Azure OpenAI Chat Completions.

        In Azure OpenAI, the model_name corresponds to the deployment name.

        Args:
            prompt: The user's text prompt.
            model_name: Azure deployment name (e.g., 'gpt-4o').
            temperature: Sampling temperature (0.0 to 2.0).

        Returns:
            The model's text response.
        """
        logger.info(
            "Azure OpenAI text generation: model=%s, temperature=%.2f",
            model_name,
            temperature,
        )

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
        Generate a text response from a text + image prompt via Azure OpenAI.

        Args:
            prompt: The user's text prompt.
            image_content: Base64-encoded image data or image URL.
            model_name: Azure deployment name (e.g., 'gpt-4o').
            temperature: Sampling temperature (0.0 to 2.0).
            image_media_type: MIME type (e.g., 'image/png'). Defaults to 'image/png'.

        Returns:
            The model's text response.
        """
        logger.info(
            "Azure OpenAI vision generation: model=%s, temperature=%.2f",
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
