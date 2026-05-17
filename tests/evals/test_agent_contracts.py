"""Agent contract evals with fake LLMs (Layer 4).

These evals use deterministic fake LLM responses to verify that each agent
and the full pipeline enforces its contract: correct context is passed,
malformed output is caught, review verdicts are respected, and warnings
are actionable.
"""

from pathlib import Path
from typing import Any, ClassVar

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
from tests.evals.helpers import (
    extract_verdict,
    has_forbidden_headings,
    has_generic_phrases,
    is_standalone_article,
)


class _RecordingLlm(ILlmPort):
    """Fake LLM that records every prompt for inspection."""

    def __init__(self, response: str = "Fake response.") -> None:
        self.prompts: list[str] = []
        self._response = response

    def generate(self, prompt: str, **kwargs: Any) -> str:
        self.prompts.append(prompt)
        return self._response

    def get_model(self) -> BaseChatModel:
        raise NotImplementedError


FAKE_ANALYSIS = "## Architecture\n\nsrc/cli.py is the CLI entrypoint."
FAKE_FACTS = "## Technologies\n\n- Python\n- Rust"
FAKE_ANGLES = "## Candidate Angles\n\n### Angle 1\n- Thesis: Build a CLI tool."
FAKE_POSITIONING = "## Strong Signals\n\n- Evidence-backed signal."
FAKE_OUTLINE = "# Working Title\n\n## Outline\n1. Problem context\n2. Design"
FAKE_DRAFT = "# A Real Article\n\n## Design\n\nThe system uses a pipeline of eight agents. Each agent has a single responsibility. This approach keeps the code modular and testable.\n\n## Decisions\n\nThe scanner uses a language-agnostic heuristic. It looks for manifests, entrypoints, and domain modules. This works across Python, Rust, and JavaScript.\n"
FAKE_REVIEW_PASS = "## Supported Claims\n\n- Claim one.\n\n## Verdict\n\nPASS\n"
FAKE_REVIEW_BLOCK = "## Supported Claims\n\n- Weak claim.\n\n## Weak Or Unsupported Claims\n\n- Generic unsupported claim.\n\n## Verdict\n\nBLOCK\n"
FAKE_FINAL = "# Final Post\n\nContent.\n"


class _ScriptedDraftLlm(ILlmPort):
    """Fake LLM with prompt-specific responses for pipeline contract tests."""

    def __init__(
        self,
        *,
        analysis: str = FAKE_ANALYSIS,
        angles: str = FAKE_ANGLES,
        positioning: str = FAKE_POSITIONING,
        outline: str = FAKE_OUTLINE,
        draft: str = FAKE_DRAFT,
        repaired_draft: str = FAKE_DRAFT,
        review: str = FAKE_REVIEW_PASS,
        final: str = FAKE_FINAL,
    ) -> None:
        self.prompts: list[str] = []
        self.analysis = analysis
        self.angles = angles
        self.positioning = positioning
        self.outline = outline
        self.draft = draft
        self.repaired_draft = repaired_draft
        self.review = review
        self.final = final

    def generate(self, prompt: str, **kwargs: Any) -> str:
        self.prompts.append(prompt)
        if "Rewrite the malformed draft" in prompt:
            return self.repaired_draft
        if "Review the draft against the evidence" in prompt:
            return self.review
        if "Edit the draft into a final local portfolio post" in prompt:
            return self.final
        if "Write a standalone portfolio technical post" in prompt:
            return self.draft
        if "Create a technical post outline" in prompt:
            return self.outline
        if "positioning a technical project" in prompt:
            return self.positioning
        if "planning a portfolio technical post" in prompt:
            return self.angles
        if "Repository Analyst" in prompt or "Analyze" in prompt:
            return self.analysis
        return self.analysis

    def prompts_containing(self, text: str) -> list[str]:
        """Return recorded prompts containing text."""
        return [prompt for prompt in self.prompts if text in prompt]

    def get_model(self) -> BaseChatModel:
        raise NotImplementedError


def _build_use_case(llm: ILlmPort) -> DraftProjectPostUseCase:
    fs = FileSystemAdapter()
    return DraftProjectPostUseCase(
        scanner=ProjectScannerAgent(fs, llm),
        analyst=RepositoryAnalystAgent(llm),
        architecture_narrator=ArchitectureNarratorAgent(llm),
        portfolio_positioning=PortfolioPositioningAgent(llm),
        outline_agent=OutlineAgent(llm),
        writer=TechnicalWriterAgent(llm),
        reviewer=TechnicalReviewerAgent(llm),
        final_editor=FinalEditorAgent(llm),
        workspace=WorkspaceAdapter(),
    )


def _create_project(path: Path) -> None:
    (path / "README.md").write_text("# Project\n")
    (path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    (path / "src").mkdir()
    (path / "src/main.py").write_text("print('hello')\n")
    (path / "tests").mkdir()
    (path / "tests/test_main.py").write_text("def test(): pass\n")


class TestWriterAgentContract:
    """TechnicalWriterAgent must receive outline + analysis + positioning."""

    def test_writer_receives_outline(self) -> None:
        llm = _RecordingLlm(FAKE_DRAFT)
        agent = TechnicalWriterAgent(llm)
        agent.generate(FAKE_OUTLINE, FAKE_ANALYSIS, FAKE_POSITIONING)
        prompt = llm.prompts[0]
        assert FAKE_OUTLINE in prompt, "writer prompt must contain the outline"
        assert FAKE_ANALYSIS in prompt, "writer prompt must contain technical analysis"
        assert FAKE_POSITIONING in prompt, (
            "writer prompt must contain portfolio positioning"
        )

    def test_writer_prompt_contains_no_raw_scan_artifacts(self) -> None:
        llm = _RecordingLlm(FAKE_DRAFT)
        agent = TechnicalWriterAgent(llm)
        agent.generate(FAKE_OUTLINE, FAKE_ANALYSIS, FAKE_POSITIONING)
        prompt = llm.prompts[0]
        assert "selected_files" not in prompt.lower(), (
            "writer must not receive raw selected_files artifact"
        )
        assert "file_inventory" not in prompt.lower(), (
            "writer must not receive raw file inventory"
        )
        assert "project_facts" not in prompt.lower(), (
            "writer must not receive raw project facts"
        )

    def test_writer_generates_output_as_string(self) -> None:
        llm = _RecordingLlm(FAKE_DRAFT)
        agent = TechnicalWriterAgent(llm)
        result = agent.generate(FAKE_OUTLINE, FAKE_ANALYSIS, FAKE_POSITIONING)
        assert isinstance(result, str) and len(result) > 0, (
            "writer must return a non-empty string"
        )


class TestReviewerAgentContract:
    """TechnicalReviewerAgent must receive draft + facts + analysis."""

    def test_reviewer_receives_draft_and_evidence(self) -> None:
        llm = _RecordingLlm(FAKE_REVIEW_BLOCK)
        agent = TechnicalReviewerAgent(llm)
        agent.generate(FAKE_DRAFT, FAKE_FACTS, FAKE_ANALYSIS)
        prompt = llm.prompts[0]
        assert FAKE_DRAFT in prompt, "reviewer prompt must contain the draft"
        assert FAKE_FACTS in prompt, "reviewer prompt must contain project facts"
        assert FAKE_ANALYSIS in prompt, (
            "reviewer prompt must contain technical analysis"
        )

    def test_reviewer_output_has_verdict(self) -> None:
        llm = _RecordingLlm(FAKE_REVIEW_BLOCK)
        agent = TechnicalReviewerAgent(llm)
        result = agent.generate(FAKE_DRAFT, FAKE_FACTS, FAKE_ANALYSIS)
        verdict = extract_verdict(result)
        assert verdict is not None, (
            "reviewer output must contain a verdict (PASS or BLOCK)"
        )


class TestOutlineAgentContract:
    """OutlineAgent must receive angles and positioning."""

    def test_outline_agent_receives_angles_and_positioning(self) -> None:
        llm = _RecordingLlm(FAKE_OUTLINE)
        agent = OutlineAgent(llm)
        agent.generate(FAKE_ANGLES, FAKE_POSITIONING, "medium")
        prompt = llm.prompts[0]
        assert FAKE_ANGLES in prompt, "outline agent prompt must contain post angles"
        assert FAKE_POSITIONING in prompt, (
            "outline agent prompt must contain positioning"
        )


class TestNarratorAgentContract:
    """ArchitectureNarrator must receive facts and analysis."""

    def test_narrator_receives_facts_and_analysis(self) -> None:
        llm = _RecordingLlm(FAKE_ANGLES)
        agent = ArchitectureNarratorAgent(llm)
        agent.generate(FAKE_FACTS, FAKE_ANALYSIS)
        prompt = llm.prompts[0]
        assert FAKE_FACTS in prompt, "narrator prompt must contain project facts"
        assert FAKE_ANALYSIS in prompt, (
            "narrator prompt must contain technical analysis"
        )


class TestPipelineBlockContract:
    """Pipeline must respect BLOCK verdict and produce coherent artifacts."""

    def test_pipeline_blocks_finalization_on_review_block(self, tmp_path: Path) -> None:
        project_path = tmp_path / "project"
        workspace_root = tmp_path / "workspaces"
        project_path.mkdir()
        _create_project(project_path)

        llm = _ScriptedDraftLlm(review=FAKE_REVIEW_BLOCK)
        result = _build_use_case(llm).execute(
            DraftRequest(
                project_path=str(project_path),
                workspace_root=str(workspace_root),
            )
        )
        final = result.final_post_path.read_text(encoding="utf-8")
        assert final.startswith("# Finalization Blocked"), (
            "final.md must start with '# Finalization Blocked' when review blocks"
        )

    def test_pipeline_passes_when_review_passes(self, tmp_path: Path) -> None:
        project_path = tmp_path / "project"
        workspace_root = tmp_path / "workspaces"
        project_path.mkdir()
        _create_project(project_path)

        llm = _ScriptedDraftLlm(review=FAKE_REVIEW_PASS, final=FAKE_FINAL)
        result = _build_use_case(llm).execute(
            DraftRequest(
                project_path=str(project_path),
                workspace_root=str(workspace_root),
            )
        )
        final = result.final_post_path.read_text(encoding="utf-8")
        assert not final.startswith("# Finalization Blocked"), (
            "final.md must not be blocked when review passes"
        )
        assert final == FAKE_FINAL, "final.md must be produced by FinalEditorAgent"

    def test_blocked_pipeline_warnings_mention_block(self, tmp_path: Path) -> None:
        project_path = tmp_path / "project"
        workspace_root = tmp_path / "workspaces"
        project_path.mkdir()
        _create_project(project_path)

        llm = _ScriptedDraftLlm(review=FAKE_REVIEW_BLOCK)
        result = _build_use_case(llm).execute(
            DraftRequest(
                project_path=str(project_path),
                workspace_root=str(workspace_root),
            )
        )
        warnings = (result.workspace_path / "warnings.md").read_text(encoding="utf-8")
        assert "BLOCK" in warnings, "warnings must mention BLOCK when review blocks"
        assert "unsupported" in warnings.lower(), (
            "warnings should reference unsupported claims when review blocks"
        )

    def test_passed_pipeline_warnings_no_block(self, tmp_path: Path) -> None:
        project_path = tmp_path / "project"
        workspace_root = tmp_path / "workspaces"
        project_path.mkdir()
        _create_project(project_path)

        llm = _ScriptedDraftLlm(review=FAKE_REVIEW_PASS)
        result = _build_use_case(llm).execute(
            DraftRequest(
                project_path=str(project_path),
                workspace_root=str(workspace_root),
            )
        )
        warnings = (result.workspace_path / "warnings.md").read_text(encoding="utf-8")
        assert "BLOCK" not in warnings, (
            "warnings must not mention BLOCK when review passes"
        )


class TestPipelineArtifactContracts:
    """Generated artifacts must follow contract rules even with fake LLMs."""

    def test_generated_draft_is_standalone_article(self, tmp_path: Path) -> None:
        project_path = tmp_path / "project"
        workspace_root = tmp_path / "workspaces"
        project_path.mkdir()
        _create_project(project_path)

        llm = _ScriptedDraftLlm(draft=FAKE_DRAFT)
        result = _build_use_case(llm).execute(
            DraftRequest(
                project_path=str(project_path),
                workspace_root=str(workspace_root),
            )
        )
        draft = (result.workspace_path / "draft.md").read_text(encoding="utf-8")
        assert is_standalone_article(draft), (
            "generated draft must be a standalone article"
        )

    def test_generated_draft_has_no_forbidden_headings(self, tmp_path: Path) -> None:
        project_path = tmp_path / "project"
        workspace_root = tmp_path / "workspaces"
        project_path.mkdir()
        _create_project(project_path)

        llm = _ScriptedDraftLlm(draft=FAKE_DRAFT)
        result = _build_use_case(llm).execute(
            DraftRequest(
                project_path=str(project_path),
                workspace_root=str(workspace_root),
            )
        )
        draft = (result.workspace_path / "draft.md").read_text(encoding="utf-8")
        found = has_forbidden_headings(draft)
        assert found == [], f"draft must not contain forbidden headings: {found}"

    def test_malformed_writer_output_caught_before_review(self, tmp_path: Path) -> None:
        """Writer returning outline dump should be caught before reaching the reviewer."""
        project_path = tmp_path / "project"
        workspace_root = tmp_path / "workspaces"
        project_path.mkdir()
        _create_project(project_path)

        malformed_draft = "# Title\n\n## Outline\n1. Problem\n2. Solution\n\n## Technical Analysis\n\nStuff."
        llm = _ScriptedDraftLlm(
            draft=malformed_draft,
            repaired_draft=FAKE_DRAFT,
            review=FAKE_REVIEW_PASS,
        )
        result = _build_use_case(llm).execute(
            DraftRequest(
                project_path=str(project_path),
                workspace_root=str(workspace_root),
            )
        )
        draft = (result.workspace_path / "draft.md").read_text(encoding="utf-8")
        assert is_standalone_article(draft), (
            "pipeline must repair malformed writer output before review"
        )
        review_prompts = llm.prompts_containing("Review the draft against the evidence")
        assert review_prompts, "reviewer must run after draft repair"
        assert "## Outline" not in review_prompts[0], (
            "reviewer must receive repaired draft, not malformed outline dump"
        )

    def test_outline_with_generic_claims_is_flagged(self, tmp_path: Path) -> None:
        """Outline containing 'users often struggle' should be caught before writing."""
        project_path = tmp_path / "project"
        workspace_root = tmp_path / "workspaces"
        project_path.mkdir()
        _create_project(project_path)

        outline_with_generic = (
            "# Title\n\n## Outline\n1. Problem: users often struggle with X."
        )
        llm = _ScriptedDraftLlm(outline=outline_with_generic)
        result = _build_use_case(llm).execute(
            DraftRequest(
                project_path=str(project_path),
                workspace_root=str(workspace_root),
            )
        )
        outline = (result.workspace_path / "outline.md").read_text(encoding="utf-8")
        found = has_generic_phrases(outline)
        assert found == [], (
            f"outline must not contain generic claims before reaching writer: {found}"
        )

    def test_outline_generic_claim_cleaning_is_case_insensitive(
        self, tmp_path: Path
    ) -> None:
        """Outline cleanup must remove generic claims regardless of casing."""
        project_path = tmp_path / "project"
        workspace_root = tmp_path / "workspaces"
        project_path.mkdir()
        _create_project(project_path)

        outline_with_generic = (
            "# Title\n\n## Outline\n1. Problem: Users Often Struggle with X."
        )
        llm = _ScriptedDraftLlm(outline=outline_with_generic)
        result = _build_use_case(llm).execute(
            DraftRequest(
                project_path=str(project_path),
                workspace_root=str(workspace_root),
            )
        )
        outline = (result.workspace_path / "outline.md").read_text(encoding="utf-8")
        found = has_generic_phrases(outline)
        assert found == [], f"outline cleanup must be case-insensitive, found: {found}"

    def test_duplicate_review_claims_across_sections_flagged(
        self, tmp_path: Path
    ) -> None:
        """Review with the same claim in Supported and Exaggerations should be flagged."""
        duplicate_review = (
            "## Supported Claims\n\n- Claim about architecture.\n"
            "## Exaggerations\n\n- Claim about architecture.\n"
            "## Verdict\n\nBLOCK\n"
        )
        project_path = tmp_path / "project"
        workspace_root = tmp_path / "workspaces"
        project_path.mkdir()
        _create_project(project_path)

        llm = _ScriptedDraftLlm(review=duplicate_review)
        result = _build_use_case(llm).execute(
            DraftRequest(
                project_path=str(project_path),
                workspace_root=str(workspace_root),
            )
        )
        review = (result.workspace_path / "technical_review.md").read_text(
            encoding="utf-8"
        )
        assert "duplicate" in review.lower() or "inconsistent" in review.lower(), (
            "pipeline should flag duplicate claims in review categories"
        )


class TestPipelineArtifactExistence:
    """Pipeline must create all expected workspace artifacts."""

    EXPECTED_ARTIFACTS: ClassVar[set[str]] = {
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

    def test_all_artifacts_created(self, tmp_path: Path) -> None:
        project_path = tmp_path / "project"
        workspace_root = tmp_path / "workspaces"
        project_path.mkdir()
        _create_project(project_path)

        llm = _ScriptedDraftLlm(draft=FAKE_DRAFT)
        result = _build_use_case(llm).execute(
            DraftRequest(
                project_path=str(project_path),
                workspace_root=str(workspace_root),
            )
        )
        found = {p.name for p in result.workspace_path.iterdir()}
        missing = self.EXPECTED_ARTIFACTS - found
        assert not missing, f"missing workspace artifacts: {missing}"
