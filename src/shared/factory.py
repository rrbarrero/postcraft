"""Factory for creating application instances and services."""

from typing import Protocol, TypeVar

from src.shared.config import config
from src.shared.llm import LLM


class LlmAdapterProto(Protocol):
    """Protocol for LLM adapter."""

    def generate(self, prompt: str) -> str: ...
    def get_model(self) -> object: ...


class FileSystemAdapterProto(Protocol):
    """Protocol for file system adapter."""

    def list_files(self, path: object, pattern: str = "**/*") -> list[object]: ...
    def read_file(self, path: object) -> str: ...
    def file_exists(self, path: object) -> bool: ...


T = TypeVar("T")


class ServiceFactory:
    """Central factory for creating application services and adapters."""

    _instance: ServiceFactory | None = None
    _llm: LLM | None = None
    _config: object | None = None
    _adapters: dict[str, object] | None = None

    def __new__(cls) -> ServiceFactory:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._adapters = {}
        return cls._instance

    @property
    def config(self) -> object:
        """Get configuration instance."""
        if self._config is None:
            self._config = config
        return self._config

    @property
    def llm(self) -> LLM:
        """Get LLM instance."""
        if self._llm is None:
            self._llm = LLM()
        return self._llm

    def get_llm_model(self) -> object:
        """Get the LLM model instance."""
        return self.llm.get_instance()

    def register_adapter(self, name: str, adapter: object) -> None:
        """Register an adapter instance.

        Args:
            name: Adapter name.
            adapter: Adapter instance.
        """
        if self._adapters is None:
            self._adapters = {}
        self._adapters[name] = adapter

    def get_adapter(self, name: str) -> object:
        """Get a cached adapter by name.

        Args:
            name: Adapter name (e.g., 'llm', 'filesystem').

        Returns:
            Adapter instance.

        Raises:
            ValueError: If adapter not found.
        """
        if self._adapters and name in self._adapters:
            return self._adapters[name]
        raise ValueError(
            f"Adapter '{name}' not registered. Use register_adapter() first."
        )

    def clear_cache(self) -> None:
        """Clear all cached adapters."""
        if self._adapters:
            self._adapters.clear()


factory = ServiceFactory()
