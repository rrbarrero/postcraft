"""Integration tests for Phase 2 local draft generation."""

from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseChatModel

from src.adapters.secondary.file_system import FileSystemAdapter
from src.adapters.secondary.workspace import WorkspaceAdapter
from src.application.agents.draft_generation_agents import (
    ArchitectureNarratorAgent,
    FinalEditorAgent,
    OutlineAgent,
    PortfolioPositioningAgent,
    TechnicalReviewerAgent,
    TechnicalWriterAgent,
)
from src.application.agents.project_scanner_agent import ProjectScannerAgent
from src.application.agents.repository_analyst_agent import RepositoryAnalystAgent
from src.application.use_cases.draft_project_post import DraftProjectPostUseCase
from src.domain.entities.draft_generation import DraftRequest
from src.domain.ports.llm import ILlmPort


class FakeDraftLlm(ILlmPort):
    """Deterministic LLM double for draft generation tests."""

    def __init__(self, *, block_review: bool = False) -> None:
        self.prompts: list[str] = []
        self.block_review = block_review

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Return stable content based on the requested artifact."""
        self.prompts.append(prompt)
        if "Required format:\n## Supported Claims" in prompt:
            verdict = "BLOCK" if self.block_review else "PASS"
            return f"## Supported Claims\n\n- Claim with evidence.\n\n## Verdict\n{verdict}"
        if "Return only the Markdown draft" in prompt:
            return "# Draft\n\nA grounded draft."
        if "Return only Markdown" in prompt:
            return "# Final\n\nA corrected final post."
        return "Generated artifact."

    def get_model(self) -> BaseChatModel:
        """Return a placeholder model."""
        raise NotImplementedError


def build_use_case(llm: ILlmPort) -> DraftProjectPostUseCase:
    """Build the Phase 2 use case with fake dependencies."""
    file_system = FileSystemAdapter()
    return DraftProjectPostUseCase(
        scanner=ProjectScannerAgent(file_system, llm),
        analyst=RepositoryAnalystAgent(llm),
        architecture_narrator=ArchitectureNarratorAgent(llm),
        portfolio_positioning=PortfolioPositioningAgent(llm),
        outline_agent=OutlineAgent(llm),
        writer=TechnicalWriterAgent(llm),
        reviewer=TechnicalReviewerAgent(llm),
        final_editor=FinalEditorAgent(llm),
        workspace=WorkspaceAdapter(),
    )


def create_sample_project(path: Path) -> None:
    """Create a minimal project for draft generation."""
    (path / "docs").mkdir()
    (path / "src").mkdir()
    (path / "tests").mkdir()
    (path / "pyproject.toml").write_text("[project]\nname = 'sample'\n")
    (path / "README.md").write_text("# Sample\n")
    (path / "docs/design.md").write_text("# Design\n")
    (path / "src/main.py").write_text("print('hello')\n")
    (path / "tests/test_main.py").write_text("def test_main(): pass\n")


def test_draft_project_post_creates_workspace_artifacts(tmp_path: Path) -> None:
    """Test Phase 2 writes all expected workspace artifacts."""
    project_path = tmp_path / "sample"
    workspace_root = tmp_path / "workspaces"
    project_path.mkdir()
    create_sample_project(project_path)

    result = build_use_case(FakeDraftLlm()).execute(
        DraftRequest(
            project_path=str(project_path),
            workspace_root=str(workspace_root),
        )
    )

    expected_files = {
        "input.json",
        "file_inventory.md",
        "selected_files.md",
        "project_facts.md",
        "technical_analysis.md",
        "post_angles.md",
        "portfolio_positioning.md",
        "outline.md",
        "draft.md",
        "technical_review.md",
        "final.md",
        "warnings.md",
    }

    assert result.workspace_path.exists()
    assert expected_files <= {path.name for path in result.workspace_path.iterdir()}
    assert result.final_post_path.read_text(encoding="utf-8").startswith("# Final")
    assert result.metrics["command"] == "draft-project-post"
    assert result.metrics["scan"]["total_files"] >= 5
    assert result.metrics["artifacts"]["char_counts"]["final_post"] > 0
    assert "total_ms" in result.metrics["timings_ms"]


def test_draft_project_post_blocks_finalization_on_review_block(
    tmp_path: Path,
) -> None:
    """Test critical review issues block final editing."""
    project_path = tmp_path / "sample"
    workspace_root = tmp_path / "workspaces"
    project_path.mkdir()
    create_sample_project(project_path)

    result = build_use_case(FakeDraftLlm(block_review=True)).execute(
        DraftRequest(
            project_path=str(project_path),
            workspace_root=str(workspace_root),
        )
    )

    final_content = result.final_post_path.read_text(encoding="utf-8")
    warnings = (result.workspace_path / "warnings.md").read_text(encoding="utf-8")

    assert final_content.startswith("# Finalization Blocked")
    assert "Technical review returned BLOCK" in warnings
