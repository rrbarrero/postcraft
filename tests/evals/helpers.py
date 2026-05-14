"""Helper functions for deterministic eval tests."""

import re
from pathlib import Path

FORBIDDEN_DRAFT_HEADINGS = [
    "## Outline",
    "Technical Analysis",
    "Portfolio Positioning",
    "Claims To Avoid",
]


def load_artifact(workspace_path: Path, filename: str) -> str:
    """Load a workspace artifact, returning empty string if not found."""
    path = workspace_path / filename
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def has_forbidden_headings(content: str) -> list[str]:
    """Check if content contains any forbidden headings.

    Returns list of forbidden headings that were found.
    """
    found = []
    for heading in FORBIDDEN_DRAFT_HEADINGS:
        if heading in content:
            found.append(heading)
    return found


def extract_verdict(content: str) -> str | None:
    """Extract the review verdict from technical_review.md content.

    Returns PASS, BLOCK, or None if no valid verdict is found.
    """
    match = re.search(
        r"(?:##\s*Verdict|Veridict)\s*\n\s*\*{0,2}(PASS|BLOCK)\*{0,2}",
        content,
    )
    if match:
        return match.group(1)
    match = re.search(r"\*{0,2}Verdict\*{0,2}:\s*\*{0,2}(PASS|BLOCK)\*{0,2}", content)
    if match:
        return match.group(1)
    return None


def count_verdicts(content: str) -> int:
    """Count how many distinct verdict mentions exist in the review."""
    pattern = re.compile(
        r"(?:##\s*Verdict|Veridict)\s*\n\s*\*{0,2}(PASS|BLOCK)\*{0,2}"
    )
    matches = pattern.findall(content)
    if matches:
        return len(matches)
    inline_pattern = re.compile(
        r"\*{0,2}Verdict\*{0,2}:\s*\*{0,2}(PASS|BLOCK)\*{0,2}"
    )
    inline_matches = inline_pattern.findall(content)
    return len(inline_matches)


def has_prose_paragraphs(content: str, min_paragraphs: int = 3) -> bool:
    """Check if content has enough prose paragraphs.

    A prose paragraph is a block of text containing at least 2 sentences,
    separated by blank lines, that is not a heading, list, or code block.
    """
    paragraphs = 0
    for block in content.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        if block.startswith("#"):
            continue
        if block.startswith(("- ", "* ")):
            continue
        if re.match(r"\d+\.\s", block):
            continue
        if block.startswith("```"):
            continue
        sentence_count = len(re.findall(r"[.!?](?: |$)", block))
        if sentence_count >= 2:
            paragraphs += 1
    return paragraphs >= min_paragraphs


def is_standalone_article(content: str) -> bool:
    """Check if draft is a standalone article, not an outline dump."""
    if not content.strip():
        return False
    lines = content.strip().split("\n")
    has_title = any(line.startswith("# ") for line in lines)
    if not has_title:
        return False
    return has_prose_paragraphs(content, min_paragraphs=2)
