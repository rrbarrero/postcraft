"""Project Scanner agent state definitions."""

from typing import TypedDict


class ProjectScannerState(TypedDict):
    """State for Project Scanner agent."""

    root_path: str
    files: list[dict]
    technologies: list[dict]
    dependencies: list[dict]
    selected_files: list[dict]
    signals: list[dict]
    result: dict | None


class RepositoryAnalystState(TypedDict):
    """State for Repository Analyst agent."""

    scan_result: dict
    analysis: dict[str, str]
