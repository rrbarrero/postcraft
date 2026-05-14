"""End-to-end tests for Project Scanner and Repository Analyst agents."""

from pathlib import Path
from typing import cast

import pytest

from src.adapters.secondary.file_system import FileSystemAdapter
from src.adapters.secondary.llm_adapter import LlmAdapter
from src.application.agents.project_scanner_agent import ProjectScannerAgent
from src.application.agents.repository_analyst_agent import RepositoryAnalystAgent
from src.domain.ports.llm import ILlmPort


class FakeLlm:
    """Deterministic LLM test double."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate(self, prompt: str, **kwargs: object) -> str:
        """Record prompt and return a stable response."""
        self.prompts.append(prompt)
        return "fake response"

    def get_model(self) -> object:
        """Return a placeholder model object."""
        return object()


@pytest.mark.llm
def test_project_scanner_integration(tmp_path: Path) -> None:
    """Test Project Scanner scans a sample repository."""
    # Create a sample project structure
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    (tmp_path / "main.py").write_text("print('hello')\n")
    (tmp_path / "README.md").write_text("# Test\n")

    # Initialize scanner
    file_system = FileSystemAdapter()
    llm = LlmAdapter()
    scanner = ProjectScannerAgent(file_system, llm)

    # Run scanner
    result = scanner.scan(str(tmp_path))

    # Assertions
    assert result.total_files >= 3
    assert any(t.name == "Python" for t in result.technologies)
    assert result.languages.get("Python", 0) >= 1


def test_project_scanner_selects_evidence_and_signals(tmp_path: Path) -> None:
    """Test scanner selects relevant files and detects project signals."""
    (tmp_path / "lib/domain").mkdir(parents=True)
    (tmp_path / "app/services").mkdir(parents=True)
    (tmp_path / "cmd").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "docs").mkdir()

    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    (tmp_path / "Makefile").write_text("test:\n\tuv run pytest\n")
    (tmp_path / "docs/phase-1.md").write_text("# Phase 1\n")
    (tmp_path / "lib/domain/model.py").write_text("class Model: pass\n")
    (tmp_path / "app/services/use_case.py").write_text("class UseCase: pass\n")
    (tmp_path / "cmd/cli.py").write_text("def main(): pass\n")
    (tmp_path / "tests/test_agent.py").write_text("def test_agent(): pass\n")

    scanner = ProjectScannerAgent(FileSystemAdapter(), cast(ILlmPort, FakeLlm()))

    result = scanner.scan(str(tmp_path))

    selected_paths = {file.path for file in result.selected_files}
    signal_names = {signal.name for signal in result.signals}

    assert "pyproject.toml" in selected_paths
    assert "Makefile" in selected_paths
    assert "docs/phase-1.md" in selected_paths
    assert "Architectural naming in directory structure" in signal_names
    assert "Automated tests" in signal_names
    assert "Developer automation or runtime configuration" in signal_names


def test_repository_analyst_prompt_uses_scanner_evidence(tmp_path: Path) -> None:
    """Test analyst prompts include selected files and observed signals."""
    (tmp_path / "lib/domain").mkdir(parents=True)
    (tmp_path / "app/services").mkdir(parents=True)
    (tmp_path / "cmd").mkdir()

    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    (tmp_path / "lib/domain/model.py").write_text("class Model: pass\n")
    (tmp_path / "app/services/use_case.py").write_text("class UseCase: pass\n")
    (tmp_path / "cmd/cli.py").write_text("def main(): pass\n")

    fake_llm = FakeLlm()
    scanner = ProjectScannerAgent(FileSystemAdapter(), cast(ILlmPort, fake_llm))
    scan_result = scanner.scan(str(tmp_path))

    analyst = RepositoryAnalystAgent(cast(ILlmPort, fake_llm))
    analyst.analyze(scan_result)

    combined_prompts = "\n".join(fake_llm.prompts)

    assert "Selected evidence index" in combined_prompts
    assert "lib/domain/model.py" in combined_prompts
    assert "app/services/use_case.py" in combined_prompts
    assert "Architectural naming in directory structure" in combined_prompts
    assert "/no_think" in combined_prompts
    assert "Do not invent purpose" in combined_prompts


def test_repository_analyst_prompts_stay_within_local_context_budget(
    tmp_path: Path,
) -> None:
    """Test analyst prompts stay bounded for a local 4096-token model."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "lib/domain").mkdir(parents=True)
    (tmp_path / "app/services").mkdir(parents=True)
    (tmp_path / "tests").mkdir()

    long_content = "\n".join(f"line {index}: implementation detail" for index in range(300))
    (tmp_path / "README.md").write_text(long_content)
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    (tmp_path / "docs/design.md").write_text(long_content)
    (tmp_path / "lib/domain/model.py").write_text(long_content)
    (tmp_path / "app/services/use_case.py").write_text(long_content)
    (tmp_path / "tests/test_use_case.py").write_text(long_content)

    fake_llm = FakeLlm()
    scanner = ProjectScannerAgent(FileSystemAdapter(), cast(ILlmPort, fake_llm))
    scan_result = scanner.scan(str(tmp_path))

    analyst = RepositoryAnalystAgent(cast(ILlmPort, fake_llm))
    analyst.analyze(scan_result)

    assert fake_llm.prompts
    assert all(len(prompt) < 12_000 for prompt in fake_llm.prompts)


@pytest.mark.llm
def test_repository_analyst_integration(tmp_path: Path) -> None:
    """Test Repository Analyst analyzes a scan result."""
    # Create a sample project
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    (tmp_path / "main.py").write_text("print('hello')\n")

    # First scan
    file_system = FileSystemAdapter()
    llm = LlmAdapter()
    scanner = ProjectScannerAgent(file_system, llm)
    scan_result = scanner.scan(str(tmp_path))

    # Then analyze
    analyst = RepositoryAnalystAgent(llm)
    analysis = analyst.analyze(scan_result)

    # Assertions
    assert "architecture" in analysis
    assert "patterns" in analysis
    assert "summary" in analysis
