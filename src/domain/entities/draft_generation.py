"""Data structures for local draft generation."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class DraftRequest(BaseModel):
    """Input parameters for generating a local portfolio draft."""

    project_path: str
    workspace_root: str = "workspaces"
    audience: str = "technical hiring managers and senior engineers"
    angle: str | None = None
    target_length: str = "medium"
    language: str = "English"


class DraftArtifacts(BaseModel):
    """Intermediate and final artifacts produced by Phase 2."""

    file_inventory: str
    selected_files: str
    project_facts: str
    technical_analysis: str
    post_angles: str
    portfolio_positioning: str
    outline: str
    draft: str
    technical_review: str
    final_post: str
    warnings: list[str] = Field(default_factory=list)


class DraftResult(BaseModel):
    """Result of a local draft generation run."""

    workspace_path: Path
    final_post_path: Path
    artifacts: DraftArtifacts
    metrics: dict[str, Any] = Field(default_factory=dict)
