"""Data structures for project scanning results."""

from pydantic import BaseModel, Field


class FileInfo(BaseModel):
    """Information about a single file."""

    path: str
    size_bytes: int
    extension: str | None = None


class Technology(BaseModel):
    """Detected technology in the project."""

    name: str
    type: str  # e.g., "language", "framework", "library", "tool"
    version: str | None = None
    config_file: str | None = None


class Dependency(BaseModel):
    """A project dependency."""

    name: str
    version: str | None = None
    type: str  # e.g., "runtime", "dev"


class SelectedFile(BaseModel):
    """A file selected as relevant evidence for repository analysis."""

    path: str
    reason: str
    excerpt: str


class ProjectSignal(BaseModel):
    """An observed technical signal with supporting file evidence."""

    name: str
    confidence: str
    evidence: list[str]


class ProjectScanResult(BaseModel):
    """Result of project scanning."""

    root_path: str
    total_files: int
    total_directories: int
    files: list[FileInfo]
    technologies: list[Technology]
    dependencies: list[Dependency]
    languages: dict[str, int]  # language: file count
    selected_files: list[SelectedFile] = Field(default_factory=list)
    signals: list[ProjectSignal] = Field(default_factory=list)
