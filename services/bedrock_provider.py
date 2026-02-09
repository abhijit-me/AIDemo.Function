"""
AWS Bedrock provider module.

Handles communication with AWS Bedrock for Anthropic Claude and Meta Llama
models using the Bedrock Converse API via the boto3 SDK.

Environment Variables:
    AWS_ACCESS_KEY_ID: AWS access key ID.
    AWS_SECRET_ACCESS_KEY: AWS secret access key.
    AWS_REGION: AWS region for the Bedrock service (default: 'us-east-1').
"""

import os
import json
import base64
import logging
from typing import Optional

import boto3

from services.base_provider import BaseProvider

logger = logging.getLogger(__name__)


class BedrockProvider(BaseProvider):
    """
    Provider implementation for AWS Bedrock.

    Supports Anthropic Claude models and Meta Llama models through
    the Bedrock Converse API, providing a unified interface for both.
    """

    def __init__(self):
        """Initialize the Bedrock runtime client with AWS credentials."""
        region = os.environ.get("AWS_REGION", "us-east-1")
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=region,
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        )
        logger.info("AWS Bedrock provider initialized (region=%s).", region)

    def _is_meta_model(self, model_name: str) -> bool:
        """Check if the model is a Meta Llama model."""
        return model_name.startswith("meta.")

    def generate_text(
        self, prompt: str, model_name: str, temperature: float
    ) -> str:
        """
        Generate a text response using the AWS Bedrock Converse API.

        Uses the unified Converse API which works with both Anthropic
        and Meta models hosted on Bedrock.

        Args:
            prompt: The user's text prompt.
            model_name: Bedrock model identifier
                        (e.g., 'anthropic.claude-sonnet-4-20250514-v1:0').
            temperature: Sampling temperature.

        Returns:
            The model's text response.
        """
        logger.info(
            "Bedrock text generation: model=%s, temperature=%.2f",
            model_name,
            temperature,
        )

        response = self.client.converse(
            modelId=model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"text": prompt}
                    ],
                }
            ],
            inferenceConfig={
                "temperature": temperature,
                "maxTokens": 4096,
            },
        )

        # Extract text from the Converse API response
        output_message = response.get("output", {}).get("message", {})
        content_blocks = output_message.get("content", [])
        return "".join(
            block.get("text", "") for block in content_blocks
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
        Generate a text response from a text + image prompt via AWS Bedrock.

        Uses the Bedrock Converse API with image content blocks.
        Note: Meta Llama models on Bedrock generally do not support vision.

        Args:
            prompt: The user's text prompt.
            image_content: Base64-encoded image data.
            model_name: Bedrock model identifier.
            temperature: Sampling temperature.
            image_media_type: MIME type (e.g., 'image/png'). Defaults to 'image/png'.

        Returns:
            The model's text response.

        Raises:
            ValueError: If the model does not support vision input.
        """
        if self._is_meta_model(model_name):
            raise ValueError(
                f"Model '{model_name}' does not support image/vision input."
            )

        logger.info(
            "Bedrock vision generation: model=%s, temperature=%.2f",
            model_name,
            temperature,
        )

        media_type = image_media_type or "image/png"

        # Map MIME type to Bedrock format string
        format_map = {
            "image/png": "png",
            "image/jpeg": "jpeg",
            "image/gif": "gif",
            "image/webp": "webp",
        }
        image_format = format_map.get(media_type, "png")

        # Decode base64 image to bytes for the Bedrock API
        image_bytes = base64.b64decode(image_content)

        response = self.client.converse(
            modelId=model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "image": {
                                "format": image_format,
                                "source": {
                                    "bytes": image_bytes,
                                },
                            },
                        },
                        {
                            "text": prompt,
                        },
                    ],
                }
            ],
            inferenceConfig={
                "temperature": temperature,
                "maxTokens": 4096,
            },
        )

        output_message = response.get("output", {}).get("message", {})
        content_blocks = output_message.get("content", [])
        return "".join(
            block.get("text", "") for block in content_blocks
        )
