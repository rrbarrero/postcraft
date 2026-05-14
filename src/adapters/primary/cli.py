"""CLI for blog poster agents."""

from pathlib import Path
from time import perf_counter
from typing import Any

import typer

from src.adapters.secondary.file_system import FileSystemAdapter
from src.adapters.secondary.llm_adapter import LlmAdapter
from src.adapters.secondary.observability import ObservabilityAdapter
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
from src.domain.entities.project_scan import ProjectScanResult
from src.shared.config import config

app = typer.Typer(
    help="Blog Poster - Multi-agent system for generating portfolio posts"
)


@app.command()
def scan(
    path: str,
    metrics_log: str = typer.Option(
        "logs/last_run_metrics.json",
        help="Truncating metrics log path.",
    ),
) -> None:
    """Scan a local repository and display the results."""
    started = perf_counter()
    observability = ObservabilityAdapter()
    typer.echo(f"Scanning repository: {path}")

    file_system = FileSystemAdapter()
    llm = LlmAdapter()
    scanner = ProjectScannerAgent(file_system, llm)

    result = scanner.scan(path)
    duration_ms = _elapsed_ms(started)
    metrics = _build_scan_metrics(
        command="scan",
        path=path,
        scan_result=result,
        duration_ms=duration_ms,
    )
    metrics["recorded_at"] = observability.now_iso()
    metrics["metrics_log_path"] = metrics_log
    observability.write_last_run(Path(metrics_log), metrics)

    typer.echo("\n--- Scan Results ---")
    typer.echo(f"Total files: {result.total_files}")
    typer.echo(f"Total directories: {result.total_directories}")
    typer.echo("\nTechnologies detected:")
    for tech in result.technologies:
        typer.echo(f"  - {tech.name} ({tech.type})")

    typer.echo("\nLanguages:")
    for lang, count in result.languages.items():
        typer.echo(f"  - {lang}: {count} files")

    typer.echo(f"\nDependencies ({len(result.dependencies)}):")
    for dep in result.dependencies[:10]:
        version = dep.version or "unknown"
        typer.echo(f"  - {dep.name} ({version})")
    typer.echo(f"\nMetrics log: {metrics_log}")


@app.command()
def analyze(
    path: str,
    metrics_log: str = typer.Option(
        "logs/last_run_metrics.json",
        help="Truncating metrics log path.",
    ),
) -> None:
    """Scan and analyze a repository."""
    started = perf_counter()
    observability = ObservabilityAdapter()
    typer.echo(f"Analyzing repository: {path}")

    file_system = FileSystemAdapter()
    llm = LlmAdapter()

    # Scan
    typer.echo("Scanning...")
    scanner = ProjectScannerAgent(file_system, llm)
    scan_result = scanner.scan(path)

    # Analyze
    typer.echo("Analyzing...")
    analyst = RepositoryAnalystAgent(llm)
    analysis = analyst.analyze(scan_result)

    typer.echo("\n--- Analysis ---")
    typer.echo(f"\nArchitecture:\n{analysis.get('architecture', 'N/A')}")
    typer.echo(f"\nPatterns:\n{analysis.get('patterns', 'N/A')}")
    typer.echo(f"\nSummary:\n{analysis.get('summary', 'N/A')}")
    metrics = _build_scan_metrics(
        command="analyze",
        path=path,
        scan_result=scan_result,
        duration_ms=_elapsed_ms(started),
    )
    metrics["recorded_at"] = observability.now_iso()
    metrics["metrics_log_path"] = metrics_log
    metrics["analysis"] = {
        "architecture_chars": len(analysis.get("architecture", "")),
        "patterns_chars": len(analysis.get("patterns", "")),
        "summary_chars": len(analysis.get("summary", "")),
        "empty_sections": [
            name for name, value in analysis.items() if not value.strip()
        ],
    }
    observability.write_last_run(Path(metrics_log), metrics)
    typer.echo(f"\nMetrics log: {metrics_log}")


@app.command("draft-project-post")
def draft_project_post(
    path: str,
    workspace: str = typer.Option("workspaces", help="Workspace output root."),
    metrics_log: str = typer.Option(
        "logs/last_run_metrics.json",
        help="Truncating metrics log path.",
    ),
    audience: str = typer.Option(
        "technical hiring managers and senior engineers",
        help="Target audience for the post.",
    ),
    angle: str | None = typer.Option(None, help="Optional preferred post angle."),
    target_length: str = typer.Option("medium", help="Target post length."),
    language: str = typer.Option("English", help="Output language."),
) -> None:
    """Generate a local auditable portfolio post draft."""
    observability = ObservabilityAdapter()
    typer.echo(f"Generating local draft for repository: {path}")

    file_system = FileSystemAdapter()
    llm = LlmAdapter()

    use_case = DraftProjectPostUseCase(
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
    result = use_case.execute(
        DraftRequest(
            project_path=path,
            workspace_root=workspace,
            audience=audience,
            angle=angle,
            target_length=target_length,
            language=language,
        )
    )

    typer.echo("\n--- Draft Generation Complete ---")
    typer.echo(f"Workspace: {result.workspace_path}")
    typer.echo(f"Final post: {result.final_post_path}")
    metrics = {
        **result.metrics,
        "recorded_at": observability.now_iso(),
        "metrics_log_path": metrics_log,
        "llm": _build_llm_metrics(),
    }
    observability.write_last_run(Path(metrics_log), metrics)
    typer.echo(f"Metrics log: {metrics_log}")
    if result.artifacts.warnings:
        typer.echo("\nWarnings:")
        for warning in result.artifacts.warnings:
            typer.echo(f"  - {warning}")


def _build_scan_metrics(
    command: str,
    path: str,
    scan_result: ProjectScanResult,
    duration_ms: float,
) -> dict[str, Any]:
    """Build scan/analyze metrics payload."""
    return {
        "command": command,
        "project_path": path,
        "timings_ms": {
            "total_ms": duration_ms,
        },
        "llm": _build_llm_metrics(),
        "scan": {
            "total_files": scan_result.total_files,
            "total_directories": scan_result.total_directories,
            "technologies": [tech.name for tech in scan_result.technologies],
            "dependency_count": len(scan_result.dependencies),
            "languages": scan_result.languages,
            "selected_file_count": len(scan_result.selected_files),
            "selected_paths": [file.path for file in scan_result.selected_files],
            "selected_excerpt_chars": sum(
                len(file.excerpt) for file in scan_result.selected_files
            ),
            "signal_count": len(scan_result.signals),
            "signals": [
                {
                    "name": signal.name,
                    "confidence": signal.confidence,
                    "evidence_count": len(signal.evidence),
                }
                for signal in scan_result.signals
            ],
        },
    }


def _build_llm_metrics() -> dict[str, Any]:
    """Build LLM configuration metrics."""
    return {
        "base_url": config.llm_base_url,
        "model": config.llm_model,
        "temperature": config.llm_temperature,
        "max_tokens": config.llm_max_tokens,
    }


def _elapsed_ms(start: float) -> float:
    """Return elapsed milliseconds."""
    return round((perf_counter() - start) * 1000, 2)


if __name__ == "__main__":
    app()
