"""Port interfaces for repository operations."""

from abc import ABC, abstractmethod
from collections.abc import Collection
from pathlib import Path

from ..entities.project_scan import ProjectScanResult

DEFAULT_EXCLUDED_DIRS: frozenset[str] = frozenset(
    {
        ".venv",
        "venv",
        "env",
        ".env",
        "logs",
        "node_modules",
        "bower_components",
        ".git",
        ".svn",
        ".hg",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".eggs",
        "*.egg-info",
        "dist",
        "build",
        "target",
        "bin",
        "obj",
        "out",
        ".idea",
        ".vscode",
        ".DS_Store",
        "Thumbs.db",
        "data",
        "tmp",
        "temp",
        "cache",
        ".cache",
        "workspaces",
    }
)


class IFileSystemPort(ABC):
    """Port for file system operations."""

    @abstractmethod
    def list_files(
        self,
        path: Path,
        pattern: str = "**/*",
        exclude_dirs: Collection[str] | None = None,
    ) -> list[Path]:
        """List files in directory matching pattern.

        Args:
            path: Root directory to scan.
            pattern: Glob pattern for matching files.
            exclude_dirs: Directory names to exclude from scanning.

        Returns:
            List of file paths.
        """
        ...

    @abstractmethod
    def read_file(self, path: Path) -> str:
        """Read file contents.

        Args:
            path: Path to file.

        Returns:
            File contents as string.
        """
        ...

    @abstractmethod
    def file_exists(self, path: Path) -> bool:
        """Check if file exists.

        Args:
            path: Path to check.

        Returns:
            True if file exists.
        """
        ...


class IProjectScannerPort(ABC):
    """Port for project scanning operations."""

    @abstractmethod
    def scan(self, path: Path) -> ProjectScanResult:
        """Scan a project directory.

        Args:
            path: Root directory of the project.

        Returns:
            Project scan result with files and technologies.
        """
        ...
