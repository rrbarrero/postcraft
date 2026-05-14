"""Observability adapter for last-run metrics."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class ObservabilityAdapter:
    """Writes run metrics to a truncating JSON log file."""

    def write_last_run(self, path: Path, metrics: dict[str, Any]) -> Path:
        """Overwrite the metrics log with the latest run only.

        Args:
            path: Metrics log path.
            metrics: Metrics payload.

        Returns:
            Path to the written metrics log.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self._to_jsonable(metrics), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return path

    def now_iso(self) -> str:
        """Return current UTC time as an ISO timestamp."""
        return datetime.now(UTC).isoformat()

    def _to_jsonable(self, data: Any) -> Any:
        """Convert common project values to JSON-serializable values."""
        if isinstance(data, BaseModel):
            return data.model_dump(mode="json")
        if isinstance(data, Path):
            return str(data)
        if isinstance(data, dict):
            return {str(key): self._to_jsonable(value) for key, value in data.items()}
        if isinstance(data, list):
            return [self._to_jsonable(item) for item in data]
        if isinstance(data, tuple):
            return [self._to_jsonable(item) for item in data]
        return data
