"""Deterministic artifact contract evals (Layer 1).

These evals inspect generated workspace artifacts without calling an LLM.
They verify that each artifact follows its expected contract.
"""

from pathlib import Path

from tests.evals.helpers import (
    count_verdicts,
    extract_verdict,
    has_forbidden_headings,
    has_prose_paragraphs,
    is_standalone_article,
    load_artifact,
)


def _write(workspace: Path, filename: str, content: str) -> None:
    (workspace / filename).write_text(content, encoding="utf-8")


def test_draft_is_standalone_article(tmp_path: Path) -> None:
    """Verify that a well-formed draft with prose paragraphs and a title is detected as a standalone article."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _write(
        workspace,
        "draft.md",
        """# Building a Multi-Agent System

## Problem Context

Writing technical portfolio posts is time-consuming. After completing a project, the details fade and the motivation to document them drops. Most developers have a collection of repositories that could demonstrate their skills, but no structured way to turn them into portfolio content.

## Project Goal

I built a tool that takes a local repository and generates a credible portfolio-oriented technical post. The system scans the repository, identifies architecture and evidence, and produces a draft with supported claims.

## General Design

The system follows a pipeline architecture with eight agents. Each agent has a single responsibility: scanning, analysis, angle selection, positioning, outlining, writing, reviewing, and final editing. All intermediate artifacts are persisted to a workspace for auditability.

## Technical Decisions

The scanner uses a language-agnostic file selection heuristic. It looks for manifests, entrypoints, domain modules, adapters, tests, and documentation. This approach works across Python, Rust, and JavaScript projects without per-language configuration.

## What I Learned

Building deterministic evaluation into the pipeline earlier would have saved significant debugging time. Artifact contract checks catch malformed output before it reaches the reviewer.
""",
    )
    content = load_artifact(workspace, "draft.md")
    assert is_standalone_article(content)


def test_draft_outline_dump_is_not_standalone_article(tmp_path: Path) -> None:
    """Verify that a draft mixing outline, analysis sections, and bullet lists is rejected as not a standalone article."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _write(
        workspace,
        "draft.md",
        """# CLI Tool for Home Assistant Integration

## Outline

1. **Problem Context**
   - Users often struggle with manually accessing Home Assistant data.
   - This creates a need for a tool that simplifies interaction.

2. **Project Goal**
   - Define the objective of creating a CLI tool.
   - Provide a command-line interface for retrieving sensor data.

3. **General Design**
   - The tool uses clap, reqwest, and serde_yaml.
   - Configuration files store user-specific settings.

## Technical Analysis

### Architecture

**Observed facts:**
- src/cli.rs contains a CLI parser with subcommands.
- Cargo.toml lists dependencies including clap and reqwest.

### Patterns

**Observed or tentative patterns:**
- The project uses Rust as the primary language.
- The presence of modules suggests a modular design.

## Portfolio Positioning

**Strong Signals**
- The project uses Rust with a Cargo.toml manifest.
- The presence of clap suggests a CLI tool.

**Claims To Avoid**
- "Full-featured integration tool" is not supported.
""",
    )
    content = load_artifact(workspace, "draft.md")
    assert not is_standalone_article(content)


def test_draft_has_no_forbidden_headings(tmp_path: Path) -> None:
    """Verify that a valid article draft does not contain forbidden pipeline artifact headings."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _write(
        workspace,
        "draft.md",
        """# Building a Multi-Agent System

## Problem Context

Writing technical portfolio posts is time-consuming. After completing a project, the details fade and the motivation to document them drops.

## Project Goal

I built a tool that takes a local repository and generates a credible portfolio-oriented technical post.

## General Design

The system follows a pipeline architecture with eight agents. Each agent has a single responsibility.

## Technical Decisions

The scanner uses a language-agnostic file selection heuristic. It looks for manifests, entrypoints, domain modules, adapters, tests, and documentation.
""",
    )
    content = load_artifact(workspace, "draft.md")
    assert has_forbidden_headings(content) == []


def test_draft_with_forbidden_headings_fails(tmp_path: Path) -> None:
    """Verify that forbidden headings like ## Outline and Technical Analysis are detected in a malformed draft."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _write(
        workspace,
        "draft.md",
        """# CLI Tool for Home Assistant Integration

## Outline

1. Problem Context
2. Project Goal

## Technical Analysis

Architecture details here.
""",
    )
    content = load_artifact(workspace, "draft.md")
    found = has_forbidden_headings(content)
    assert "## Outline" in found
    assert "Technical Analysis" in found


def test_draft_has_prose_paragraphs(tmp_path: Path) -> None:
    """Verify that a draft with multiple multi-sentence prose blocks is detected as having sufficient prose paragraphs."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _write(
        workspace,
        "draft.md",
        """# Building a Multi-Agent System

## Problem Context

Writing technical portfolio posts is time-consuming. After completing a project, the details fade and the motivation to document them drops. Most developers have a collection of repositories that could demonstrate their skills, but no structured way to turn them into portfolio content.

## Project Goal

I built a tool that takes a local repository and generates a credible portfolio-oriented technical post. The system scans the repository, identifies architecture and evidence, and produces a draft with supported claims.

## General Design

The system follows a pipeline architecture with eight agents. Each agent has a single responsibility: scanning, analysis, angle selection, positioning, outlining, writing, reviewing, and final editing. All intermediate artifacts are persisted to a workspace for auditability.

## What I Learned

Building deterministic evaluation into the pipeline earlier would have saved significant debugging time. Artifact contract checks catch malformed output before it reaches the reviewer.
""",
    )
    content = load_artifact(workspace, "draft.md")
    assert has_prose_paragraphs(content)


def test_draft_without_prose_paragraphs_fails(tmp_path: Path) -> None:
    """Verify that a draft consisting only of headings and bullet lists is rejected for lacking prose paragraphs."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _write(
        workspace,
        "draft.md",
        """# CLI Tool

## Features

- Feature one
- Feature two
- Feature three

## Installation

1. Step one
2. Step two
3. Step three
""",
    )
    content = load_artifact(workspace, "draft.md")
    assert not has_prose_paragraphs(content)


def test_final_article_is_accepted(tmp_path: Path) -> None:
    """Verify that a final artifact containing a complete article is accepted as valid output."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _write(
        workspace,
        "final.md",
        """# Building a Multi-Agent System

## Problem Context

Writing technical portfolio posts is time-consuming. After completing a project, the details fade and the motivation to document them drops. Most developers have a collection of repositories that could demonstrate their skills, but no structured way to turn them into portfolio content.

## Project Goal

I built a tool that takes a local repository and generates a credible portfolio-oriented technical post. The system scans the repository, identifies architecture and evidence, and produces a draft with supported claims. This turns a manual writing task into an automated pipeline.

## Conclusion

This tool turns the post-generation problem from a manual writing task into an automated evidence-to-narrative pipeline. The result is consistent, auditable, and portfolio-ready.
""",
    )
    content = load_artifact(workspace, "final.md")
    assert is_standalone_article(content)


def test_final_blocked_artifact_is_accepted(tmp_path: Path) -> None:
    """Verify that a final artifact starting with '# Finalization Blocked' is accepted as a valid blocked output."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _write(
        workspace,
        "final.md",
        "# Finalization Blocked\n\nThe technical reviewer found critical issues.\n",
    )
    content = load_artifact(workspace, "final.md")
    assert content.startswith("# Finalization Blocked")
    assert not is_standalone_article(content)


def test_technical_review_has_exactly_one_verdict(tmp_path: Path) -> None:
    """Verify that a well-formed technical review contains exactly one verdict section."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _write(
        workspace,
        "technical_review.md",
        """## Supported Claims

- Claim one.

## Weak Or Unsupported Claims

- Weak claim.

## Verdict

PASS
""",
    )
    content = load_artifact(workspace, "technical_review.md")
    assert count_verdicts(content) == 1
    assert extract_verdict(content) == "PASS"


def test_technical_review_with_duplicate_verdict_fails(tmp_path: Path) -> None:
    """Verify that a technical review with multiple verdict sections is detected as malformed."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _write(
        workspace,
        "technical_review.md",
        """## Supported Claims

- Claim one.

## Verdict

PASS

## Verdict

BLOCK
""",
    )
    content = load_artifact(workspace, "technical_review.md")
    assert count_verdicts(content) > 1


def test_technical_review_without_verdict_fails(tmp_path: Path) -> None:
    """Verify that a technical review missing a verdict section is detected."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _write(
        workspace,
        "technical_review.md",
        """## Supported Claims

- Claim one.

## Weak Or Unsupported Claims

- Weak claim.
""",
    )
    content = load_artifact(workspace, "technical_review.md")
    assert extract_verdict(content) is None


def test_technical_review_verdict_is_valid(tmp_path: Path) -> None:
    """Verify that a verdict value of PASS or BLOCK is correctly extracted from the review."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _write(
        workspace,
        "technical_review.md",
        "## Verdict\n\n**PASS**\n",
    )
    content = load_artifact(workspace, "technical_review.md")
    verdict = extract_verdict(content)
    assert verdict in ("PASS", "BLOCK")


def test_technical_review_invalid_verdict_fails(tmp_path: Path) -> None:
    """Verify that an invalid verdict value like MAYBE is not accepted as PASS or BLOCK."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _write(
        workspace,
        "technical_review.md",
        "## Verdict\n\nMAYBE\n",
    )
    content = load_artifact(workspace, "technical_review.md")
    assert extract_verdict(content) is None


def test_warnings_reflect_review_block(tmp_path: Path) -> None:
    """Verify that warnings.md contains BLOCK when the technical review verdict is BLOCK."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _write(
        workspace,
        "technical_review.md",
        "## Verdict\n\nBLOCK\n",
    )
    _write(
        workspace,
        "warnings.md",
        "# Warnings\n\n- Technical review returned BLOCK.\n- The draft has unsupported claims.\n",
    )
    review = load_artifact(workspace, "technical_review.md")
    warnings = load_artifact(workspace, "warnings.md")
    verdict = extract_verdict(review)
    if verdict == "BLOCK":
        assert "BLOCK" in warnings
    elif verdict == "PASS":
        assert "BLOCK" not in warnings


def test_warnings_reflect_review_pass(tmp_path: Path) -> None:
    """Verify that warnings.md does not claim BLOCK when the technical review verdict is PASS."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _write(
        workspace,
        "technical_review.md",
        "## Verdict\n\nPASS\n",
    )
    _write(
        workspace,
        "warnings.md",
        "# Warnings\n\n- Minor formatting issue.\n",
    )
    review = load_artifact(workspace, "technical_review.md")
    warnings = load_artifact(workspace, "warnings.md")
    verdict = extract_verdict(review)
    if verdict == "PASS":
        assert "BLOCK" not in warnings
    elif verdict == "BLOCK":
        assert "BLOCK" in warnings


def test_warnings_mismatch_is_detected_when_block_verdict_not_reflected(
    tmp_path: Path,
) -> None:
    """Verify mismatch is caught when BLOCK verdict has no matching warnings."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _write(
        workspace,
        "technical_review.md",
        "## Verdict\n\nBLOCK\n",
    )
    _write(
        workspace,
        "warnings.md",
        "# Warnings\n\n- Minor formatting issue.\n",
    )
    review = load_artifact(workspace, "technical_review.md")
    warnings = load_artifact(workspace, "warnings.md")
    verdict = extract_verdict(review)
    warnings_match = "BLOCK" in warnings or "blocked" in warnings.lower()
    assert verdict == "BLOCK" and not warnings_match
