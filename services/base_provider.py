"""
Base provider module defining the abstract interface for all LLM providers.

All concrete provider implementations must inherit from BaseProvider
and implement the generate_text and generate_with_image methods.
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseProvider(ABC):
    """
    Abstract base class for LLM service providers.

    Every provider must implement:
        - generate_text: Handle text-only chat completions.
        - generate_with_image: Handle multimodal (text + image) completions.
    """

    @abstractmethod
    def generate_text(
        self, prompt: str, model_name: str, temperature: float
    ) -> str:
        """
        Generate a text response from a text-only prompt.

        Args:
            prompt: The user's text prompt.
            model_name: The provider-specific model identifier.
            temperature: Sampling temperature for response generation.

        Returns:
            The generated text response from the model.

        Raises:
            Exception: If the API call fails.
        """
        pass

    @abstractmethod
    def generate_with_image(
        self,
        prompt: str,
        image_content: str,
        model_name: str,
        temperature: float,
        image_media_type: Optional[str] = None,
    ) -> str:
        """
        Generate a text response from a multimodal prompt (text + image).

        Args:
            prompt: The user's text prompt.
            image_content: Base64-encoded image data or image URL.
            model_name: The provider-specific model identifier.
            temperature: Sampling temperature for response generation.
            image_media_type: MIME type of the image (e.g., 'image/png').

        Returns:
            The generated text response from the model.

        Raises:
            Exception: If the API call fails or the model does not support vision.
        """
        pass
