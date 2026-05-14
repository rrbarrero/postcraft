"""Repository Analyst Agent using LangGraph."""

from typing import Any

from langgraph.graph import END, StateGraph

from src.application.state.project_scanner_state import RepositoryAnalystState
from src.domain.entities.agent_base import BaseAgent
from src.domain.entities.project_scan import ProjectScanResult
from src.domain.ports.llm import ILlmPort

MAX_CONTEXT_CHARS = 8_500
MAX_FACTS_FILES = 40
MAX_SELECTED_FILES_WITH_EXCERPTS = 4
MAX_SELECTED_EXCERPT_CHARS = 900
MAX_ANALYSIS_CHARS = 700


class RepositoryAnalystAgent(BaseAgent[RepositoryAnalystState]):
    """Agent that analyzes repository structure and generates technical insights.

    This agent takes the Project Scanner output and uses the LLM to generate
    architectural insights, patterns, and technical summaries.
    """

    def __init__(self, llm_port: ILlmPort) -> None:
        super().__init__("RepositoryAnalyst")
        self.llm_port = llm_port

    def create_graph(self) -> Any:
        """Create the LangGraph state machine."""
        graph = StateGraph(RepositoryAnalystState)  # type: ignore

        graph.add_node("analyze_architecture", self._analyze_architecture_node)
        graph.add_node("detect_patterns", self._detect_patterns_node)
        graph.add_node("generate_summary", self._generate_summary_node)

        graph.set_entry_point("analyze_architecture")
        graph.add_edge("analyze_architecture", "detect_patterns")
        graph.add_edge("detect_patterns", "generate_summary")
        graph.add_edge("generate_summary", END)

        return graph.compile()

    def _analyze_architecture_node(
        self,
        state: RepositoryAnalystState,
    ) -> RepositoryAnalystState:
        """Analyze the project architecture using LLM."""
        scan = ProjectScanResult(**state["scan_result"])

        prompt = self._build_architecture_prompt(scan)
        response = self.llm_port.generate(prompt)

        state["analysis"] = {
            "architecture": response,
        }
        return state

    def _detect_patterns_node(
        self,
        state: RepositoryAnalystState,
    ) -> RepositoryAnalystState:
        """Detect code patterns and conventions."""
        scan = ProjectScanResult(**state["scan_result"])

        prompt = self._build_patterns_prompt(scan)
        response = self.llm_port.generate(prompt)

        state["analysis"]["patterns"] = response
        return state

    def _generate_summary_node(
        self,
        state: RepositoryAnalystState,
    ) -> RepositoryAnalystState:
        """Generate a technical summary."""
        scan = ProjectScanResult(**state["scan_result"])

        prompt = self._build_summary_prompt(scan, state["analysis"])
        response = self.llm_port.generate(prompt)

        state["analysis"]["summary"] = response
        return state

    def _build_architecture_prompt(self, scan: ProjectScanResult) -> str:
        """Build prompt for architecture analysis."""
        context = self._build_architecture_context(scan)

        return f"""/no_think
You are a strict technical analyst. Answer in English using only observed evidence.

{context}

Required format:
Observed facts:
- Maximum 3 bullets. Each bullet must cite file paths.

Reasonable inferences:
- Maximum 2 bullets. Clearly label them as inferences.

Doubts or limits:
- Maximum 2 bullets.

Do not use Markdown headings like ###. Do not invent purpose, flows, reports, or features without evidence."""

    def _build_patterns_prompt(self, scan: ProjectScanResult) -> str:
        """Build prompt for pattern detection."""
        context = self._build_patterns_context(scan)

        return f"""/no_think
Identify patterns and conventions using only the evidence. Answer in English.

{context}

Required format:
Observed or tentative patterns:
- Maximum 5 bullets.
- Each bullet must start with [observed] or [tentative].
- Each bullet must cite file paths.

If there is not enough evidence, say exactly:
Observed or tentative patterns:
- Not enough evidence."""

    def _build_summary_prompt(
        self,
        scan: ProjectScanResult,
        analysis: dict,
    ) -> str:
        """Build prompt for summary generation."""
        context = self._build_summary_context(scan)

        return f"""/no_think
Create a useful, sober technical summary. Answer in English.

{context}

Previous analysis:
Architecture: {self._truncate(str(analysis.get("architecture", "")), MAX_ANALYSIS_CHARS)}
Patterns: {self._truncate(str(analysis.get("patterns", "")), MAX_ANALYSIS_CHARS)}

Required format:
Summary:
- 2 or 3 bullets about what the project appears to be and how it is built.

Observed strengths:
- Maximum 3 bullets with file paths.

Limitations or doubts:
- Maximum 3 bullets.

Do not mention JSON, Markdown, reports, data processing, production-ready, or strong patterns unless supported by concrete file paths."""

    def _build_architecture_context(self, scan: ProjectScanResult) -> str:
        """Build bounded context for architecture analysis."""
        return self._truncate_context(
            self._build_evidence_context(
                scan,
                include_inventory=True,
                include_excerpts=True,
                selected_file_limit=MAX_SELECTED_FILES_WITH_EXCERPTS,
            )
        )

    def _build_patterns_context(self, scan: ProjectScanResult) -> str:
        """Build bounded context for pattern detection."""
        return self._truncate_context(
            self._build_evidence_context(
                scan,
                include_inventory=True,
                include_excerpts=False,
                selected_file_limit=0,
            )
        )

    def _build_summary_context(self, scan: ProjectScanResult) -> str:
        """Build bounded context for summary generation."""
        return self._truncate_context(
            self._build_evidence_context(
                scan,
                include_inventory=False,
                include_excerpts=False,
                selected_file_limit=0,
            )
        )

    def _build_evidence_context(
        self,
        scan: ProjectScanResult,
        *,
        include_inventory: bool,
        include_excerpts: bool,
        selected_file_limit: int,
    ) -> str:
        """Build factual context provided to repository analysis prompts."""
        techs = ", ".join(
            f"{t.name} ({t.type}, {t.config_file or 'no config file'})"
            for t in scan.technologies
        )
        deps = ", ".join(
            f"{d.name}{f' {d.version}' if d.version else ''} [{d.type}]"
            for d in scan.dependencies[:20]
        )
        langs = ", ".join(
            f"{name}: {count} files" for name, count in scan.languages.items()
        )
        files = "\n".join(f"- {file.path}" for file in scan.files[:MAX_FACTS_FILES])
        signals = "\n".join(
            f"- {signal.name} ({signal.confidence}): {', '.join(signal.evidence)}"
            for signal in scan.signals
        )
        selected_file_list = "\n".join(
            f"- {file.path}: {file.reason}" for file in scan.selected_files
        )
        selected_files = self._format_selected_files(scan, selected_file_limit)

        sections = [
            f"""Repository facts:
- Root path: {scan.root_path}
- Total files: {scan.total_files}
- Total directories: {scan.total_directories}
- Technologies: {techs or "none detected"}
- Dependencies: {deps or "none detected"}
- Languages: {langs or "none detected"}""",
            f"""Observed project signals:
{signals or "- none detected"}""",
            f"""Selected evidence index:
{selected_file_list or "- no selected files available"}""",
        ]

        if include_inventory:
            sections.append(
                f"""File inventory excerpt:
{files or "- no files detected"}"""
            )

        if include_excerpts:
            sections.append(
                f"""Selected evidence excerpts:
{selected_files or "- no selected file excerpts available"}"""
            )

        return "\n\n".join(sections)

    def _format_selected_files(
        self,
        scan: ProjectScanResult,
        limit: int,
    ) -> str:
        """Format a bounded set of selected file excerpts."""
        return "\n\n".join(
            self._format_selected_file(
                file.path,
                file.reason,
                self._truncate(file.excerpt, MAX_SELECTED_EXCERPT_CHARS),
            )
            for file in scan.selected_files[:limit]
        )

    def _format_selected_file(self, path: str, reason: str, excerpt: str) -> str:
        """Format selected file evidence for prompt context."""
        return f"""### {path}
Reason: {reason}
```text
{excerpt}
```"""

    def _truncate_context(self, context: str) -> str:
        """Keep prompt context within the local model budget."""
        return self._truncate(context, MAX_CONTEXT_CHARS)

    def _truncate(self, value: str, max_chars: int) -> str:
        """Truncate text with an explicit marker."""
        if len(value) <= max_chars:
            return value
        return f"{value[:max_chars]}\n[truncated]"

    def analyze(self, scan_result: ProjectScanResult) -> dict[str, str]:
        """Analyze a repository scan result.

        Args:
            scan_result: Output from Project Scanner.

        Returns:
            Analysis dictionary with architecture, patterns, and summary.
        """
        initial_state: RepositoryAnalystState = {
            "scan_result": scan_result.model_dump(),
            "analysis": {},
        }

        final_state = self.run(initial_state)
        return final_state["analysis"]
