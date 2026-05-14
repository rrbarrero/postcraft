"""Grounding and claim safety evals (Layer 2).

These evals check whether claims stay close to observed evidence,
forbidden generic phrases are absent, architecture labels are not
overstated, and reviewer categories remain mutually exclusive.
"""

from pathlib import Path

from tests.evals.helpers import (
    extract_file_paths,
    extract_review_sections,
    find_duplicate_claims_across_sections,
    has_generic_phrases,
    has_unsupported_architecture_labels,
)


def _write(workspace: Path, filename: str, content: str) -> None:
    (workspace / filename).write_text(content, encoding="utf-8")


def test_forbidden_generic_phrases_detected(tmp_path: Path) -> None:
    """Verify that generic marketing phrases like 'users often struggle' and 'seamlessly' are detected."""
    content = """The CLI tool integrates seamlessly with Home Assistant.
Users often struggle with manually accessing data.
It is a production-ready, scalable, full-featured solution.
This must-have tool solves all problems.
"""
    found = has_generic_phrases(content)
    assert "seamlessly" in found
    assert "users often struggle" in found
    assert "production-ready" in found
    assert "scalable" in found
    assert "full-featured" in found
    assert "must-have" in found


def test_draft_without_generic_phrases_passes(tmp_path: Path) -> None:
    """Verify that a draft written with concrete, evidence-based language has no generic phrases."""
    content = """# Building a Multi-Agent System

## Problem Context

Writing technical portfolio posts takes time. After finishing a project, the details fade and the motivation to document them drops.

## Design

The system uses eight agents in a pipeline. Each agent handles one responsibility: scanning, analysis, angle selection, positioning, outlining, writing, reviewing, and editing. Artifacts are persisted to a workspace directory for auditability.
"""
    assert has_generic_phrases(content) == []


def test_generic_problem_claims_require_evidence(tmp_path: Path) -> None:
    """Verify that generic problem claims in a draft are detected and flagged.

    The outline phase should not introduce unsupported product claims
    like 'users often struggle' without repository evidence.
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _write(
        workspace,
        "draft.md",
        """# CLI Tool for Home Assistant Integration

## Problem Context

Users often struggle with manually accessing Home Assistant data or managing calendar events across multiple platforms. This creates a need for a tool that simplifies interaction.

## Project Goal

The goal is to create a user-friendly CLI that integrates seamlessly with Home Assistant.

## Design

The tool uses clap and reqwest for CLI parsing and HTTP access.
""",
    )
    content = (workspace / "draft.md").read_text(encoding="utf-8")
    found = has_generic_phrases(content)
    assert "users often struggle" in found, (
        "Generic problem claim 'users often struggle' must be flagged in the draft"
    )
    assert "seamlessly" in found


def test_unsupported_architecture_label_detected(tmp_path: Path) -> None:
    """Verify that absolute architecture labels like 'hexagonal architecture' are detected without hedging evidence."""
    content = """The project uses a hexagonal architecture pattern.
The codebase follows clean architecture principles.
Microservices architecture is used throughout.
"""
    found = has_unsupported_architecture_labels(content)
    assert "hexagonal architecture" in found
    assert "microservices architecture" in found
    assert "clean architecture" in found


def test_draft_without_architecture_labels_passes(tmp_path: Path) -> None:
    """Verify that descriptive architecture language is not flagged."""
    content = """The project separates CLI, application, and infrastructure concerns.
The codebase is organized into domain, application, and adapter layers.
Controllers handle input, services contain logic, and repositories manage data.
"""
    assert has_unsupported_architecture_labels(content) == []


def test_technical_analysis_includes_file_paths(tmp_path: Path) -> None:
    """Verify that technical analysis artifacts reference specific source file paths."""
    content = """## Architecture

Observed facts:
- src/cli.rs contains the CLI parser with subcommands.
- Cargo.toml lists dependencies including clap and reqwest.
- src/app/prompts_service.rs builds daily prompts from configured calendars.
- src/infra/ha_repo.rs models sensor state and uses reqwest for HTTP calls.
"""
    paths = extract_file_paths(content)
    assert "src/cli.rs" in paths
    assert "Cargo.toml" in paths
    assert "src/app/prompts_service.rs" in paths
    assert "src/infra/ha_repo.rs" in paths


def test_technical_review_includes_file_paths(tmp_path: Path) -> None:
    """Verify that technical review references file paths for its supported claims."""
    content = """## Supported Claims

- The scanner selects language-agnostic evidence. (src/application/agents/project_scanner_agent.py)
- The pipeline uses eight agents. (src/application/use_cases/draft_project_post.py)

## Weak Or Unsupported Claims

- Generic claim without file-path evidence.
"""
    paths = extract_file_paths(content)
    assert "src/application/agents/project_scanner_agent.py" in paths
    assert "src/application/use_cases/draft_project_post.py" in paths


def test_analysis_without_file_paths_is_empty(tmp_path: Path) -> None:
    """Verify that analysis without file references returns an empty list."""
    content = """## Architecture

The project has a modular design and uses several libraries.
"""
    assert extract_file_paths(content) == []


def test_no_duplicate_claims_across_supported_and_unsupported(tmp_path: Path) -> None:
    """Verify that a well-formed review has no claim appearing in multiple categories."""
    content = """## Supported Claims

- The scanner selects language-agnostic evidence.
- The pipeline uses eight agents.

## Weak Or Unsupported Claims

- The system can handle any repository size.

## Exaggerations

- The tool replaces all manual documentation work.

## Verdict

PASS
"""
    sections = extract_review_sections(content)
    dupes = find_duplicate_claims_across_sections(sections)
    assert dupes == []


def test_duplicate_claims_across_sections_detected(tmp_path: Path) -> None:
    """Verify that claims appearing in both 'Supported Claims' and 'Exaggerations' are detected."""
    content = """## Supported Claims

- The scanner selects language-agnostic evidence.
- The tool integrates with Home Assistant for sensor data and calendar events.

## Weak Or Unsupported Claims

- The system can handle any repository size.

## Exaggerations

- The tool integrates with Home Assistant for sensor data and calendar events.

## Verdict

BLOCK
"""
    sections = extract_review_sections(content)
    dupes = find_duplicate_claims_across_sections(sections)
    assert len(dupes) >= 1
    matched_sections = {(d[1], d[2]) for d in dupes}
    assert ("Supported Claims", "Exaggerations") in matched_sections or (
        "Exaggerations",
        "Supported Claims",
    ) in matched_sections


def test_duplicate_claim_with_formatting_normalized(tmp_path: Path) -> None:
    """Verify that duplicate detection handles bold markers and whitespace differences."""
    content = """## Supported Claims

- The **CLI tool** is designed to bridge the gap between Home Assistant and user workflows.

## Exaggerations

- The CLI tool is designed to bridge the gap between Home Assistant and user workflows.

## Verdict

BLOCK
"""
    sections = extract_review_sections(content)
    dupes = find_duplicate_claims_across_sections(sections)
    assert len(dupes) >= 1


def test_generic_phrases_in_review_are_flagged(tmp_path: Path) -> None:
    """Verify that generic phrases appearing in technical review warnings are detected."""
    review = """## Weak Or Unsupported Claims

- "Seamlessly integrates with Home Assistant" is not supported by evidence.
- Claiming the tool is "production-ready" is exaggerated.

## Verdict

BLOCK
"""
    found = has_generic_phrases(review)
    assert "seamlessly" in found
    assert "production-ready" in found


def test_multiple_sections_with_claims_extracted(tmp_path: Path) -> None:
    """Verify extract_review_sections parses all expected sections and their bullet claims."""
    content = """## Supported Claims

- Claim one.
- Claim two.

## Weak Or Unsupported Claims

- Claim three.

## Exaggerations

- Claim four.

## Required Corrections

Remove unsupported claims.

## Optional Improvements

Add more evidence.

## Verdict

PASS
"""
    sections = extract_review_sections(content)
    assert "Supported Claims" in sections
    assert "Weak Or Unsupported Claims" in sections
    assert "Exaggerations" in sections
    assert sections["Supported Claims"] == ["Claim one.", "Claim two."]
    assert sections["Weak Or Unsupported Claims"] == ["Claim three."]
    assert sections["Exaggerations"] == ["Claim four."]


def test_architecture_label_requires_context(tmp_path: Path) -> None:
    """Verify that naming a directory pattern like 'ports' and 'adapters' is not the same as claiming a formal architecture pattern without evidence."""
    with_evidence = "The project structure includes src/domain, src/application, and src/adapters directories suggesting layered separation."
    assert has_unsupported_architecture_labels(with_evidence) == []

    without_evidence = "The project implements hexagonal architecture with full port-adapter separation."
    found = has_unsupported_architecture_labels(without_evidence)
    assert "hexagonal architecture" in found
