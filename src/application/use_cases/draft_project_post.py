"""Use case for generating a local portfolio draft from a repository."""

import re
from pathlib import Path
from time import perf_counter
from typing import Any

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
from src.domain.entities.draft_generation import (
    DraftArtifacts,
    DraftRequest,
    DraftResult,
)
from src.domain.entities.project_scan import FileInfo, ProjectScanResult, SelectedFile

FORBIDDEN_DRAFT_HEADINGS = (
    "## Outline",
    "Technical Analysis",
    "Portfolio Positioning",
    "Claims To Avoid",
    "Supported Claims",
    "Weak Or Unsupported Claims",
    "Required Corrections",
)

GENERIC_DRAFT_PHRASES = (
    "users often struggle",
    "seamlessly",
    "production-ready",
    "scalable",
    "full-featured",
    "must-have",
)


class DraftProjectPostUseCase:
    """Generate a local auditable workspace with a portfolio post draft."""

    def __init__(
        self,
        scanner: ProjectScannerAgent,
        analyst: RepositoryAnalystAgent,
        architecture_narrator: ArchitectureNarratorAgent,
        portfolio_positioning: PortfolioPositioningAgent,
        outline_agent: OutlineAgent,
        writer: TechnicalWriterAgent,
        reviewer: TechnicalReviewerAgent,
        final_editor: FinalEditorAgent,
        workspace: WorkspaceAdapter,
    ) -> None:
        self.scanner = scanner
        self.analyst = analyst
        self.architecture_narrator = architecture_narrator
        self.portfolio_positioning = portfolio_positioning
        self.outline_agent = outline_agent
        self.writer = writer
        self.reviewer = reviewer
        self.final_editor = final_editor
        self.workspace = workspace

    def execute(self, request: DraftRequest) -> DraftResult:
        """Run the complete Phase 2 local draft pipeline."""
        total_start = perf_counter()
        timings: dict[str, float] = {}
        project_path = Path(request.project_path).resolve()
        workspace_root = Path(request.workspace_root).resolve()

        stage_start = perf_counter()
        workspace_path = self.workspace.create_workspace(workspace_root, project_path)
        timings["create_workspace_ms"] = self._elapsed_ms(stage_start)

        stage_start = perf_counter()
        scan = self.scanner.scan(str(project_path))
        timings["scan_ms"] = self._elapsed_ms(stage_start)

        stage_start = perf_counter()
        analysis = self.analyst.analyze(scan)
        timings["analysis_ms"] = self._elapsed_ms(stage_start)

        stage_start = perf_counter()
        file_inventory = self._render_file_inventory(scan.files)
        selected_files = self._render_selected_files(scan.selected_files)
        project_facts = self._render_project_facts(scan)
        technical_analysis = self._render_technical_analysis(analysis)
        timings["render_phase1_artifacts_ms"] = self._elapsed_ms(stage_start)

        stage_start = perf_counter()
        post_angles = self.architecture_narrator.generate(
            project_facts=project_facts,
            technical_analysis=technical_analysis,
            requested_angle=request.angle,
            language=request.language,
        )
        timings["post_angles_ms"] = self._elapsed_ms(stage_start)

        stage_start = perf_counter()
        portfolio_positioning = self.portfolio_positioning.generate(
            technical_analysis=technical_analysis,
            post_angles=post_angles,
            audience=request.audience,
            language=request.language,
        )
        timings["portfolio_positioning_ms"] = self._elapsed_ms(stage_start)

        stage_start = perf_counter()
        outline = self.outline_agent.generate(
            post_angles=post_angles,
            portfolio_positioning=portfolio_positioning,
            target_length=request.target_length,
            language=request.language,
        )
        timings["outline_ms"] = self._elapsed_ms(stage_start)

        stage_start = perf_counter()
        draft = self.writer.generate(
            outline=outline,
            technical_analysis=technical_analysis,
            portfolio_positioning=portfolio_positioning,
            language=request.language,
        )
        timings["draft_ms"] = self._elapsed_ms(stage_start)

        draft_contract_issues = self._draft_contract_issues(draft)
        if draft_contract_issues:
            stage_start = perf_counter()
            draft = self.writer.repair(
                draft=draft,
                issues=draft_contract_issues,
                outline=outline,
                technical_analysis=technical_analysis,
                portfolio_positioning=portfolio_positioning,
                language=request.language,
            )
            timings["draft_repair_ms"] = self._elapsed_ms(stage_start)
        else:
            timings["draft_repair_ms"] = 0.0

        stage_start = perf_counter()
        technical_review = self.reviewer.generate(
            draft=draft,
            project_facts=project_facts,
            technical_analysis=technical_analysis,
            language=request.language,
        )
        technical_review = self._ensure_technical_review_contract(
            technical_review,
            project_facts=project_facts,
            technical_analysis=technical_analysis,
        )
        timings["technical_review_ms"] = self._elapsed_ms(stage_start)

        stage_start = perf_counter()
        if self._review_blocks_finalization(technical_review):
            final_post = self._render_blocked_final(technical_review)
        else:
            final_post = self.final_editor.generate(
                draft=draft,
                technical_review=technical_review,
                language=request.language,
            )
        timings["final_editor_ms"] = self._elapsed_ms(stage_start)

        artifacts = DraftArtifacts(
            file_inventory=file_inventory,
            selected_files=selected_files,
            project_facts=project_facts,
            technical_analysis=technical_analysis,
            post_angles=post_angles,
            portfolio_positioning=portfolio_positioning,
            outline=outline,
            draft=draft,
            technical_review=technical_review,
            final_post=final_post,
            warnings=self._collect_warnings(technical_review),
        )

        stage_start = perf_counter()
        self._write_workspace(request, workspace_path, artifacts)
        timings["write_workspace_ms"] = self._elapsed_ms(stage_start)
        timings["total_ms"] = self._elapsed_ms(total_start)

        metrics = self._build_metrics(
            request=request,
            workspace_path=workspace_path,
            scan=scan,
            analysis=analysis,
            artifacts=artifacts,
            timings=timings,
        )

        return DraftResult(
            workspace_path=workspace_path,
            final_post_path=workspace_path / "final.md",
            artifacts=artifacts,
            metrics=metrics,
        )

    def _write_workspace(
        self,
        request: DraftRequest,
        workspace_path: Path,
        artifacts: DraftArtifacts,
    ) -> None:
        """Persist all run artifacts."""
        self.workspace.write_json(workspace_path, "input.json", request)
        self.workspace.write_text(
            workspace_path, "file_inventory.md", artifacts.file_inventory
        )
        self.workspace.write_text(
            workspace_path, "selected_files.md", artifacts.selected_files
        )
        self.workspace.write_text(
            workspace_path, "project_facts.md", artifacts.project_facts
        )
        self.workspace.write_text(
            workspace_path,
            "technical_analysis.md",
            artifacts.technical_analysis,
        )
        self.workspace.write_text(
            workspace_path, "post_angles.md", artifacts.post_angles
        )
        self.workspace.write_text(
            workspace_path,
            "portfolio_positioning.md",
            artifacts.portfolio_positioning,
        )
        self.workspace.write_text(workspace_path, "outline.md", artifacts.outline)
        self.workspace.write_text(workspace_path, "draft.md", artifacts.draft)
        self.workspace.write_text(
            workspace_path,
            "technical_review.md",
            artifacts.technical_review,
        )
        self.workspace.write_text(workspace_path, "final.md", artifacts.final_post)
        self.workspace.write_text(
            workspace_path,
            "warnings.md",
            self._render_warnings(artifacts.warnings),
        )

    def _render_file_inventory(self, files: list[FileInfo]) -> str:
        """Render a Markdown inventory from file scan data."""
        lines = ["# File Inventory", ""]
        for file in files:
            lines.append(f"- `{file.path}` ({file.size_bytes} bytes)")
        return "\n".join(lines)

    def _render_selected_files(self, selected_files: list[SelectedFile]) -> str:
        """Render selected evidence files."""
        lines = ["# Selected Files", ""]
        for file in selected_files:
            lines.extend(
                [
                    f"## {file.path}",
                    "",
                    f"Reason: {file.reason}",
                    "",
                    "```text",
                    file.excerpt,
                    "```",
                    "",
                ]
            )
        return "\n".join(lines)

    def _render_project_facts(self, scan: ProjectScanResult) -> str:
        """Render factual scan output."""
        lines = [
            "# Project Facts",
            "",
            f"- Root path: `{scan.root_path}`",
            f"- Total files: {scan.total_files}",
            f"- Total directories: {scan.total_directories}",
            "",
            "## Technologies",
            "",
        ]
        lines.extend(
            f"- {tech.name} ({tech.type}) from `{tech.config_file or 'unknown'}`"
            for tech in scan.technologies
        )
        lines.extend(["", "## Dependencies", ""])
        lines.extend(
            f"- {dep.name} {dep.version or ''} [{dep.type}]".strip()
            for dep in scan.dependencies
        )
        lines.extend(["", "## Languages", ""])
        lines.extend(
            f"- {name}: {count} files" for name, count in scan.languages.items()
        )
        lines.extend(["", "## Observed Signals", ""])
        lines.extend(
            f"- {signal.name} ({signal.confidence}): "
            f"{', '.join(f'`{item}`' for item in signal.evidence)}"
            for signal in scan.signals
        )
        return "\n".join(lines)

    def _render_technical_analysis(self, analysis: dict[str, str]) -> str:
        """Render repository analyst output."""
        return "\n\n".join(
            [
                "# Technical Analysis",
                "## Architecture",
                analysis.get("architecture", ""),
                "## Patterns",
                analysis.get("patterns", ""),
                "## Summary",
                analysis.get("summary", ""),
            ]
        )

    def _collect_warnings(self, technical_review: str) -> list[str]:
        """Collect lightweight warnings from the technical review."""
        warnings = []
        if self._review_blocks_finalization(technical_review):
            warnings.append("Technical review returned BLOCK.")
        if "unsupported" in technical_review.lower():
            warnings.append("Technical review mentions unsupported claims.")
        return warnings

    def _ensure_technical_review_contract(
        self,
        technical_review: str,
        project_facts: str,
        technical_analysis: str,
    ) -> str:
        """Conservatively repair missing machine-readable review contract parts."""
        repaired = technical_review.strip()
        if not self._extract_review_verdict(repaired):
            verdict = self._infer_review_verdict(repaired)
            repaired = "\n\n".join([repaired, "## Verdict", verdict])
        if not self._extract_file_paths(repaired):
            evidence_paths = self._extract_file_paths(
                "\n\n".join([project_facts, technical_analysis])
            )
            if evidence_paths:
                repaired = "\n\n".join(
                    [
                        repaired,
                        "## Evidence References",
                        "\n".join(f"- `{path}`" for path in evidence_paths[:5]),
                    ]
                )
        return repaired

    def _extract_review_verdict(self, content: str) -> str | None:
        """Extract a machine-readable review verdict."""
        match = re.search(
            r"(?:##\s*Verdict|Verdict:)\s*\n?\s*\*{0,2}(PASS|BLOCK)\*{0,2}",
            content,
        )
        if match:
            return match.group(1)
        return None

    def _infer_review_verdict(self, technical_review: str) -> str:
        """Infer a conservative verdict when the LLM omits the final section."""
        lower = technical_review.lower()
        blocking_terms = (
            "unsupported",
            "not supported",
            "weak",
            "exaggeration",
            "exaggerated",
            "required correction",
        )
        if any(term in lower for term in blocking_terms):
            return "BLOCK"
        return "PASS"

    def _extract_file_paths(self, content: str) -> list[str]:
        """Extract Markdown-friendly file path references."""
        pattern = re.compile(r"`?([\w./-]+\.[A-Za-z0-9]{1,8})`?")
        paths = []
        seen: set[str] = set()
        for match in pattern.findall(content):
            path = match.strip().rstrip(":,.)")
            if path not in seen:
                seen.add(path)
                paths.append(path)
        return paths

    def _draft_contract_issues(self, draft: str) -> list[str]:
        """Return deterministic contract issues for a generated draft."""
        issues = []
        if not draft.strip():
            return ["draft is empty"]
        if not any(line.startswith("# ") for line in draft.splitlines()):
            issues.append("draft must start with one H1 title")
        forbidden = [
            heading for heading in FORBIDDEN_DRAFT_HEADINGS if heading in draft
        ]
        if forbidden:
            issues.append(
                "draft contains forbidden pipeline headings: " + ", ".join(forbidden)
            )
        if not self._has_prose_paragraphs(draft):
            issues.append("draft must contain at least three prose paragraphs")
        generic = [
            phrase for phrase in GENERIC_DRAFT_PHRASES if phrase in draft.lower()
        ]
        if generic:
            issues.append(
                "draft contains generic or overstated phrases: " + ", ".join(generic)
            )
        return issues

    def _has_prose_paragraphs(self, content: str, min_paragraphs: int = 3) -> bool:
        """Check whether Markdown content has enough prose paragraphs."""
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

    def _review_blocks_finalization(self, technical_review: str) -> bool:
        """Check whether the technical review blocks finalization."""
        return "BLOCK" in technical_review.upper()

    def _render_blocked_final(self, technical_review: str) -> str:
        """Render a final artifact when review blocks publication."""
        return "\n\n".join(
            [
                "# Finalization Blocked",
                "The technical reviewer found critical issues. Fix the draft before "
                "creating a final post.",
                "## Technical Review",
                technical_review,
            ]
        )

    def _render_warnings(self, warnings: list[str]) -> str:
        """Render warnings artifact."""
        if not warnings:
            return "# Warnings\n\n- None"
        return "# Warnings\n\n" + "\n".join(f"- {warning}" for warning in warnings)

    def _build_metrics(
        self,
        request: DraftRequest,
        workspace_path: Path,
        scan: ProjectScanResult,
        analysis: dict[str, str],
        artifacts: DraftArtifacts,
        timings: dict[str, float],
    ) -> dict[str, Any]:
        """Build observability metrics for the draft generation run."""
        selected_excerpt_chars = sum(
            len(selected_file.excerpt) for selected_file in scan.selected_files
        )
        artifact_char_counts = {
            "file_inventory": len(artifacts.file_inventory),
            "selected_files": len(artifacts.selected_files),
            "project_facts": len(artifacts.project_facts),
            "technical_analysis": len(artifacts.technical_analysis),
            "post_angles": len(artifacts.post_angles),
            "portfolio_positioning": len(artifacts.portfolio_positioning),
            "outline": len(artifacts.outline),
            "draft": len(artifacts.draft),
            "technical_review": len(artifacts.technical_review),
            "final_post": len(artifacts.final_post),
        }

        return {
            "command": "draft-project-post",
            "project_path": request.project_path,
            "workspace_path": workspace_path,
            "request": {
                "audience": request.audience,
                "angle": request.angle,
                "target_length": request.target_length,
                "language": request.language,
            },
            "timings_ms": timings,
            "scan": {
                "total_files": scan.total_files,
                "total_directories": scan.total_directories,
                "technologies": [tech.name for tech in scan.technologies],
                "dependency_count": len(scan.dependencies),
                "languages": scan.languages,
                "selected_file_count": len(scan.selected_files),
                "selected_paths": [file.path for file in scan.selected_files],
                "selected_excerpt_chars": selected_excerpt_chars,
                "signal_count": len(scan.signals),
                "signals": [
                    {
                        "name": signal.name,
                        "confidence": signal.confidence,
                        "evidence_count": len(signal.evidence),
                    }
                    for signal in scan.signals
                ],
            },
            "analysis": {
                "architecture_chars": len(analysis.get("architecture", "")),
                "patterns_chars": len(analysis.get("patterns", "")),
                "summary_chars": len(analysis.get("summary", "")),
                "empty_sections": [
                    name for name, value in analysis.items() if not value.strip()
                ],
            },
            "artifacts": {
                "char_counts": artifact_char_counts,
                "draft_line_count": len(artifacts.draft.splitlines()),
                "final_line_count": len(artifacts.final_post.splitlines()),
            },
            "quality_indicators": {
                "technical_review_blocked": self._review_blocks_finalization(
                    artifacts.technical_review
                ),
                "warning_count": len(artifacts.warnings),
                "warnings": artifacts.warnings,
                "mentions_unsupported_claims": "unsupported"
                in artifacts.technical_review.lower(),
                "finalization_blocked": artifacts.final_post.startswith(
                    "# Finalization Blocked"
                ),
            },
        }

    def _elapsed_ms(self, start: float) -> float:
        """Return elapsed milliseconds from a perf counter start."""
        return round((perf_counter() - start) * 1000, 2)
