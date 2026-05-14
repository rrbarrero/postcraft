"""File system adapter implementing IFileSystemPort."""

from collections.abc import Collection
from pathlib import Path

from src.domain.ports.repositories import DEFAULT_EXCLUDED_DIRS, IFileSystemPort


class FileSystemAdapter(IFileSystemPort):
    """Adapter for file system operations."""

    def __init__(
        self,
        excluded_dirs: Collection[str] | None = None,
    ) -> None:
        self._excluded_dirs = frozenset(excluded_dirs or DEFAULT_EXCLUDED_DIRS)

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
        root = Path(path)
        if not root.exists():
            return []

        excluded = exclude_dirs or self._excluded_dirs

        def should_include(p: Path) -> bool:
            rel_path = p.relative_to(root)
            for parent in rel_path.parents:
                if parent.name in excluded:
                    return False
            return True

        return [p for p in root.glob(pattern) if p.is_file() and should_include(p)]

    def read_file(self, path: Path) -> str:
        """Read file contents.

        Args:
            path: Path to file.

        Returns:
            File contents as string.
        """
        return path.read_text(encoding="utf-8")

    def file_exists(self, path: Path) -> bool:
        """Check if file exists.

        Args:
            path: Path to check.

        Returns:
            True if file exists.
        """
        return path.exists()
