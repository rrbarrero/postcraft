"""Scanner and evidence selection evals (Layer 3).

These evals verify that the factual foundation from Phase 1 is strong enough:
dependency extraction, balanced file selection, language/technology detection,
signal discovery, and exclusion of non-source artifacts.
"""

from pathlib import Path
from typing import cast

import pytest
from langchain_core.language_models import BaseChatModel

from src.adapters.secondary.file_system import FileSystemAdapter
from src.application.agents.project_scanner_agent import ProjectScannerAgent
from src.domain.entities.project_scan import ProjectScanResult
from src.domain.ports.llm import ILlmPort

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "repos"


class _FakeLlm(ILlmPort):
    """LLM stub — the scanner never calls it but needs the dependency."""

    def generate(self, prompt: str, **kwargs: object) -> str:
        return ""

    def get_model(self) -> BaseChatModel:
        raise NotImplementedError


def _scan(fixture_name: str) -> ProjectScanResult:
    """Run the scanner against a fixture repo and return the result."""
    fs = FileSystemAdapter()
    llm = cast(ILlmPort, _FakeLlm())
    agent = ProjectScannerAgent(fs, llm)
    return agent.scan(str(FIXTURES / fixture_name))


def test_rust_fixture_detects_technology() -> None:
    """Scanner must detect Rust as a technology from Cargo.toml."""
    result = _scan("rust_home_assistant_cli")
    tech_names = {t.name for t in result.technologies}
    assert "Rust" in tech_names, "Rust must be detected from Cargo.toml"
    assert "Cargo.toml" in {t.config_file for t in result.technologies}


@pytest.mark.xfail(
    strict=True,
    reason="Cargo.toml dependency parsing not yet implemented in scanner",
)
def test_rust_fixture_extracts_cargo_dependencies() -> None:
    """Scanner must extract dependencies from Cargo.toml."""
    result = _scan("rust_home_assistant_cli")
    dep_names = {d.name for d in result.dependencies}
    for expected in {"clap", "reqwest", "serde", "serde_yaml", "tokio", "chrono"}:
        assert expected in dep_names, (
            f"dependency {expected} must be extracted from Cargo.toml"
        )
    assert len(result.dependencies) >= 5, (
        f"expected at least 5 dependencies, got {len(result.dependencies)}"
    )


def test_rust_fixture_selects_balanced_evidence() -> None:
    """Scanner must select manifest, README, entrypoint, CLI, app, and infra files."""
    result = _scan("rust_home_assistant_cli")
    selected_paths = {f.path for f in result.selected_files}
    assert "README.md" in selected_paths, "README.md must be selected"
    assert "Cargo.toml" in selected_paths, "Cargo.toml (manifest) must be selected"
    assert "makefile" in selected_paths, "makefile (automation) must be selected"
    assert "src/main.rs" in selected_paths, "src/main.rs (entrypoint) must be selected"
    assert "src/cli.rs" in selected_paths, "src/cli.rs (CLI adapter) must be selected"
    assert "src/app/prompts_service.rs" in selected_paths, (
        "src/app/prompts_service.rs (app module) must be selected"
    )
    assert "src/infra/ha_repo.rs" in selected_paths, (
        "src/infra/ha_repo.rs (infra module) must be selected"
    )


def test_rust_fixture_detects_signals() -> None:
    """Scanner must detect automation, entrypoint, and documentation signals."""
    result = _scan("rust_home_assistant_cli")
    signal_names = {s.name for s in result.signals}
    assert "Developer automation or runtime configuration" in signal_names, (
        "makefile should trigger automation signal"
    )
    assert "Probable executable entrypoints" in signal_names, (
        "main.rs should trigger entrypoint signal"
    )


def test_rust_fixture_allows_capped_selected_files() -> None:
    """Scanner must not exceed the maximum selected file limit (8)."""
    result = _scan("rust_home_assistant_cli")
    assert len(result.selected_files) <= 8, (
        f"selected {len(result.selected_files)} files, max is 8"
    )


def test_python_fixture_detects_technology() -> None:
    """Scanner must detect Python as a technology from pyproject.toml."""
    result = _scan("python_layered_cli")
    tech_names = {t.name for t in result.technologies}
    assert "Python" in tech_names, "Python must be detected from pyproject.toml"


def test_python_fixture_extracts_pyproject_dependencies() -> None:
    """Scanner must extract dependencies from pyproject.toml."""
    result = _scan("python_layered_cli")
    dep_names = {d.name for d in result.dependencies}
    for expected in {"click", "requests", "pydantic"}:
        assert expected in dep_names, (
            f"dependency {expected} must be extracted from pyproject.toml"
        )


def test_python_fixture_detects_layered_structure() -> None:
    """Scanner must detect architectural naming from domain/application/adapters layout."""
    result = _scan("python_layered_cli")
    selected_paths = {f.path for f in result.selected_files}
    assert "src/domain/model.py" in selected_paths, "domain file must be selected"
    assert "src/application/use_case.py" in selected_paths, (
        "application file must be selected"
    )
    assert "src/adapters/repository.py" in selected_paths, (
        "adapters file must be selected"
    )
    signal_names = {s.name for s in result.signals}
    assert "Architectural naming in directory structure" in signal_names, (
        "domain/application/adapters must trigger architectural naming signal"
    )


def test_python_fixture_selects_entrypoint_and_readme() -> None:
    """Scanner must select README, manifest, entrypoint, and automation files."""
    result = _scan("python_layered_cli")
    selected_paths = {f.path for f in result.selected_files}
    assert "README.md" in selected_paths, "README.md must be selected"
    assert "pyproject.toml" in selected_paths, "pyproject.toml must be selected"
    assert "Makefile" in selected_paths, "Makefile must be selected"
    assert "src/cli.py" in selected_paths, "src/cli.py (entrypoint) must be selected"


def test_python_fixture_empty_init_files_not_selected() -> None:
    """Scanner must skip empty __init__.py files from evidence selection."""
    result = _scan("python_layered_cli")
    selected_paths = {f.path for f in result.selected_files}
    init_files = {p for p in selected_paths if p.endswith("__init__.py")}
    assert init_files == set(), (
        f"empty __init__.py files must not be selected, got: {init_files}"
    )


def test_minimal_script_detects_python() -> None:
    """Scanner must detect Python from .py files even without config."""
    result = _scan("minimal_script")
    assert result.languages.get("Python", 0) >= 1, (
        "Python must be detected from .py extension"
    )


def test_minimal_script_does_not_invent_architecture() -> None:
    """Scanner must not create architectural or automation signals for a single script."""
    result = _scan("minimal_script")
    selected_paths = {f.path for f in result.selected_files}
    assert "script.py" in selected_paths, "the single source file must be selected"
    signal_names = {s.name for s in result.signals}
    assert "Architectural naming in directory structure" not in signal_names, (
        "single-file script must not trigger architectural naming signal"
    )
    assert "Local project documentation" not in signal_names, (
        "single-file script must not trigger documentation signal"
    )


def test_rust_fixture_selected_excerpts_preserve_content() -> None:
    """Selected file excerpts must contain enough content to identify behavior."""
    result = _scan("rust_home_assistant_cli")
    excerpts = {f.path: f.excerpt for f in result.selected_files}
    main_excerpt = excerpts.get("src/main.rs", "")
    cli_excerpt = excerpts.get("src/cli.rs", "")
    assert "DailyPrompt" in main_excerpt or "daily_prompt" in main_excerpt, (
        "excerpt from main.rs should reference daily prompt behavior"
    )
    assert "Get" in cli_excerpt and "Set" in cli_excerpt, (
        "excerpt from cli.rs should reference CLI subcommands"
    )


def test_fixture_detects_languages() -> None:
    """Scanner must report accurate language counts for each fixture."""
    rust_result = _scan("rust_home_assistant_cli")
    assert rust_result.languages.get("Rust", 0) >= 4, (
        "Rust fixture must have at least 4 Rust files"
    )
    py_result = _scan("python_layered_cli")
    assert py_result.languages.get("Python", 0) >= 3, (
        "Python fixture must have at least 3 Python files"
    )


def test_fixture_content_not_truncated_too_aggressively() -> None:
    """Selected file excerpts must be at least 50 chars to be meaningful."""
    result = _scan("rust_home_assistant_cli")
    for sf in result.selected_files:
        assert len(sf.excerpt) >= 50, (
            f"excerpt for {sf.path} is only {len(sf.excerpt)} chars"
        )
