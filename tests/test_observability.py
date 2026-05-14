"""Tests for observability metrics logging."""

import json
from pathlib import Path

from src.adapters.secondary.observability import ObservabilityAdapter


def test_observability_log_is_truncated_per_write(tmp_path: Path) -> None:
    """Test metrics log keeps only the latest run."""
    adapter = ObservabilityAdapter()
    log_path = tmp_path / "last_run_metrics.json"

    adapter.write_last_run(log_path, {"command": "first", "value": 1})
    adapter.write_last_run(log_path, {"command": "second", "value": 2})

    data = json.loads(log_path.read_text(encoding="utf-8"))

    assert data == {"command": "second", "value": 2}
