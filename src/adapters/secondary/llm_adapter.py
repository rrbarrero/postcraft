"""LLM adapter implementing ILlmPort."""

from typing import Any

from langchain_core.language_models import BaseChatModel

from src.domain.ports.llm import ILlmPort
from src.shared.llm import LLM


class LlmAdapter(ILlmPort):
    """Adapter for LLM operations."""

    def __init__(self) -> None:
        self._llm_instance = LLM()
        self._model = self._llm_instance.get_instance()

    def generate(self, prompt: str, **kwargs: Any) -> str:  # type: ignore[override]
        """Generate text from prompt.

        Args:
            prompt: Input prompt.
            **kwargs: Additional parameters.

        Returns:
            Generated text.
        """
        response = self._model.invoke(prompt, **kwargs)  # type: ignore[assignment]
        content = response.content
        if isinstance(content, str) and content.strip():
            return content.strip()
        if isinstance(content, list) and content:
            text_parts = [
                str(item.get("text", item)) if isinstance(item, dict) else str(item)
                for item in content
            ]
            text = "\n".join(text_parts).strip()
            if text:
                return text

        additional_kwargs = getattr(response, "additional_kwargs", {})
        reasoning = additional_kwargs.get("reasoning_content")
        if isinstance(reasoning, str) and reasoning.strip():
            return reasoning.strip()

        return "[No final content returned by the LLM.]"

    def get_model(self) -> BaseChatModel:
        """Get the underlying LLM instance.

        Returns:
            The LLM model instance.
        """
        return self._model
