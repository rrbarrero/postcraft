"""Port interfaces for LLM operations."""

from abc import ABC, abstractmethod
from typing import Any

from langchain_core.language_models import BaseChatModel


class ILlmPort(ABC):
    """Port for LLM operations."""

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate text from prompt.

        Args:
            prompt: Input prompt.
            **kwargs: Additional parameters.

        Returns:
            Generated text.
        """
        ...

    @abstractmethod
    def get_model(self) -> BaseChatModel:
        """Get the underlying LLM instance.

        Returns:
            The LLM model instance.
        """
        ...
