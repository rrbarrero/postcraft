"""Workspace adapter for local draft generation artifacts."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class WorkspaceAdapter:
    """Adapter for writing auditable local generation workspaces."""

    def create_workspace(self, root: Path, project_path: Path) -> Path:
        """Create a deterministic-enough workspace directory.

        Args:
            root: Root directory for workspaces.
            project_path: Project being processed.

        Returns:
            Created workspace path.
        """
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        project_name = project_path.resolve().name or "project"
        workspace = root / f"{project_name}-{timestamp}"
        workspace.mkdir(parents=True, exist_ok=False)
        return workspace

    def write_text(self, workspace: Path, filename: str, content: str) -> Path:
        """Write a text artifact into a workspace."""
        path = workspace / filename
        path.write_text(content, encoding="utf-8")
        return path

    def write_json(self, workspace: Path, filename: str, data: Any) -> Path:
        """Write a JSON artifact into a workspace."""
        serializable = self._to_jsonable(data)
        path = workspace / filename
        path.write_text(
            json.dumps(serializable, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return path

    def _to_jsonable(self, data: Any) -> Any:
        """Convert common project models to JSON-serializable values."""
        if isinstance(data, BaseModel):
            return data.model_dump(mode="json")
        if isinstance(data, Path):
            return str(data)
        if isinstance(data, dict):
            return {key: self._to_jsonable(value) for key, value in data.items()}
        if isinstance(data, list):
            return [self._to_jsonable(item) for item in data]
        return data
