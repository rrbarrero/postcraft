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


def require_artifact(workspace_path: Path, filename: str) -> str:
    """Load a workspace artifact, raising FileNotFoundError if missing."""
    path = workspace_path / filename
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
    heading_pattern = re.compile(
        r"(?:##\s*Verdict|Veridict)\s*\n\s*\*{0,2}(PASS|BLOCK)\*{0,2}"
    )
    inline_pattern = re.compile(
        r"\*{0,2}Verdict\*{0,2}:\s*\*{0,2}(PASS|BLOCK)\*{0,2}"
    )
    return len(heading_pattern.findall(content)) + len(inline_pattern.findall(content))


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


GENERIC_PHRASES = [
    "users often struggle",
    "seamlessly",
    "production-ready",
    "scalable",
    "full-featured",
    "must-have",
]


def has_generic_phrases(content: str) -> list[str]:
    """Check if content contains any forbidden generic marketing phrases.

    Returns list of matched phrases (case-insensitive).
    """
    lower = content.lower()
    return [phrase for phrase in GENERIC_PHRASES if phrase in lower]


UNSUPPORTED_ARCHITECTURE_LABELS = [
    "hexagonal architecture",
    "microservices architecture",
    "event-driven architecture",
    "clean architecture",
    "onion architecture",
]


def has_unsupported_architecture_labels(content: str) -> list[str]:
    """Check if content uses absolute architecture labels without hedging.

    Returns list of matched labels (case-insensitive).
    """
    lower = content.lower()
    found = []
    for label in UNSUPPORTED_ARCHITECTURE_LABELS:
        if label in lower:
            found.append(label)
    return found


FILE_PATH_PATTERN = re.compile(r"(?:^|[\s(])([\w./-]+\.\w{1,4})(?:[\s$:,)\]])")


def extract_file_paths(content: str) -> list[str]:
    """Extract file paths referenced in the content.

    Looks for patterns resembling source file paths with extensions.
    """
    matches = FILE_PATH_PATTERN.findall(content)
    seen: set[str] = set()
    paths: list[str] = []
    for m in matches:
        m = m.strip().rstrip(":,.)")
        if m not in seen and "." in m:
            seen.add(m)
            paths.append(m)
    return paths


def extract_review_sections(content: str) -> dict[str, list[str]]:
    """Parse a technical_review.md into section headings and their claims.

    Returns dict mapping section title to list of claim strings.
    """
    sections: dict[str, list[str]] = {}
    current_section: str | None = None
    for line in content.split("\n"):
        section_match = re.match(r"^##\s+(.+)", line)
        if section_match:
            current_section = section_match.group(1).strip()
            sections[current_section] = []
        elif current_section is not None and line.strip().startswith("- "):
            claim = line.strip()[2:]
            if claim:
                sections[current_section].append(claim)
    return sections


def normalize_claim(text: str) -> str:
    """Normalize a claim string for duplicate comparison."""
    return re.sub(r"\s+", " ", text).replace("**", "").strip().lower().rstrip(".")


SHORTEN_THRESHOLD = 80


def shorten(text: str) -> str:
    """Truncate claim text for readable error messages."""
    if len(text) > SHORTEN_THRESHOLD:
        return text[: SHORTEN_THRESHOLD - 3] + "..."
    return text


def find_duplicate_claims_across_sections(
    sections: dict[str, list[str]],
) -> list[tuple[str, str, str]]:
    """Find claims that appear in multiple review sections.

    Returns list of (claim_text, section_a, section_b) tuples.
    """
    normalized_map: dict[str, list[tuple[str, str]]] = {}
    for section, claims in sections.items():
        for claim in claims:
            key = normalize_claim(claim)
            if key not in normalized_map:
                normalized_map[key] = []
            normalized_map[key].append((claim, section))

    duplicates: list[tuple[str, str, str]] = []
    for key, entries in normalized_map.items():
        if len(entries) >= 2:
            for i in range(len(entries)):
                for j in range(i + 1, len(entries)):
                    if entries[i][1] != entries[j][1]:
                        duplicates.append((key, entries[i][1], entries[j][1]))
    return duplicates
