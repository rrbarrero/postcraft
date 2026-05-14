"""Self-evaluation: run the full pipeline against the blog-poster project itself.

These tests run the complete DraftProjectPostUseCase against this repository,
then apply all Layer 1 and Layer 2 artifact contract checks on the generated
workspace. They require a real LLM backend and are marked @pytest.mark.llm.
"""

from pathlib import Path

import pytest

from src.adapters.secondary.llm_adapter import LlmAdapter
from src.domain.entities.draft_generation import DraftRequest
from tests.evals.helpers import (
    count_verdicts,
    extract_file_paths,
    extract_review_sections,
    extract_verdict,
    find_duplicate_claims_across_sections,
    has_forbidden_headings,
    has_generic_phrases,
    has_prose_paragraphs,
    is_standalone_article,
    require_artifact,
)
from tests.integration.test_draft_project_post import build_use_case

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="module")
def workspace_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Run the full Phase 2 pipeline against the blog-poster repository."""
    tmp = tmp_path_factory.mktemp("self-eval")
    llm = LlmAdapter()
    result = build_use_case(llm).execute(
        DraftRequest(
            project_path=str(REPO_ROOT),
            workspace_root=str(tmp),
        )
    )
    return result.workspace_path


@pytest.mark.llm
def test_self_eval_draft_is_standalone_article(workspace_path: Path) -> None:
    """draft.md must be a standalone article, not an outline dump."""
    draft = require_artifact(workspace_path, "draft.md")
    assert is_standalone_article(draft), (
        "draft.md must be a standalone article with prose paragraphs"
    )


@pytest.mark.llm
def test_self_eval_draft_has_no_forbidden_headings(workspace_path: Path) -> None:
    """draft.md must not contain pipeline artifact sections like ## Outline."""
    draft = require_artifact(workspace_path, "draft.md")
    found = has_forbidden_headings(draft)
    assert found == [], f"draft.md contains forbidden headings: {found}"


@pytest.mark.llm
def test_self_eval_draft_has_prose(workspace_path: Path) -> None:
    """draft.md must have article-like prose paragraphs."""
    draft = require_artifact(workspace_path, "draft.md")
    assert has_prose_paragraphs(draft), "draft.md must have at least 3 prose paragraphs"


@pytest.mark.llm
def test_self_eval_draft_avoids_generic_phrases(workspace_path: Path) -> None:
    """draft.md must not contain generic marketing phrases."""
    draft = require_artifact(workspace_path, "draft.md")
    found = has_generic_phrases(draft)
    assert found == [], f"draft.md contains generic phrases: {found}"


@pytest.mark.llm
def test_self_eval_final_is_article_or_blocked(workspace_path: Path) -> None:
    """final.md must be either a valid article or explicitly blocked."""
    final = require_artifact(workspace_path, "final.md")
    is_valid = final.startswith("# Finalization Blocked") or is_standalone_article(
        final
    )
    assert is_valid, (
        "final.md must be a valid article or start with '# Finalization Blocked'"
    )


@pytest.mark.llm
def test_self_eval_review_has_exactly_one_verdict(workspace_path: Path) -> None:
    """technical_review.md must contain exactly one verdict."""
    review = require_artifact(workspace_path, "technical_review.md")
    count = count_verdicts(review)
    assert count == 1, (
        f"expected exactly 1 verdict in technical_review.md, found {count}"
    )


@pytest.mark.llm
def test_self_eval_review_verdict_is_valid(workspace_path: Path) -> None:
    """Review verdict must be PASS or BLOCK."""
    review = require_artifact(workspace_path, "technical_review.md")
    verdict = extract_verdict(review)
    assert verdict in ("PASS", "BLOCK"), (
        f"invalid verdict in technical_review.md: {verdict!r}"
    )


@pytest.mark.llm
def test_self_eval_warnings_match_verdict(workspace_path: Path) -> None:
    """warnings.md must be consistent with the review verdict."""
    review = require_artifact(workspace_path, "technical_review.md")
    warnings = require_artifact(workspace_path, "warnings.md")
    verdict = extract_verdict(review)
    if verdict == "BLOCK":
        assert "BLOCK" in warnings, (
            "warnings.md must mention BLOCK when review verdict is BLOCK"
        )
    elif verdict == "PASS":
        assert "BLOCK" not in warnings, (
            "warnings.md must not mention BLOCK when review verdict is PASS"
        )


@pytest.mark.llm
def test_self_eval_analysis_references_file_paths(workspace_path: Path) -> None:
    """technical_analysis.md must reference specific source files as evidence."""
    analysis = require_artifact(workspace_path, "technical_analysis.md")
    paths = extract_file_paths(analysis)
    assert len(paths) >= 3, (
        f"technical_analysis.md references only {len(paths)} file paths, expected >= 3: {paths}"
    )


@pytest.mark.llm
def test_self_eval_review_references_file_paths(workspace_path: Path) -> None:
    """technical_review.md must reference file paths for its claims."""
    review = require_artifact(workspace_path, "technical_review.md")
    sections = extract_review_sections(review)
    claim_sections = [
        "Supported Claims",
        "Weak Or Unsupported Claims",
        "Exaggerations",
    ]
    claim_text = "\n".join(
        "\n".join(sections.get(section, [])) for section in claim_sections
    )
    paths = extract_file_paths(claim_text)
    assert len(paths) >= 1, (
        "technical_review.md claim sections reference no file paths, "
        f"expected at least 1: {paths}"
    )


@pytest.mark.llm
def test_self_eval_no_duplicate_claims_across_sections(workspace_path: Path) -> None:
    """Reviewer must not classify the same claim in multiple categories."""
    review = require_artifact(workspace_path, "technical_review.md")
    sections = extract_review_sections(review)
    dupes = find_duplicate_claims_across_sections(sections)
    assert dupes == [], f"duplicate claims found across review sections: {dupes}"
