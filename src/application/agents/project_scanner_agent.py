"""Project Scanner Agent using LangGraph."""

import json
import logging
import re
import tomllib
from collections.abc import Collection
from pathlib import Path
from typing import Any

from langgraph.graph import END, StateGraph

from src.application.state.project_scanner_state import ProjectScannerState
from src.domain.entities.agent_base import BaseAgent
from src.domain.entities.project_scan import (
    Dependency,
    FileInfo,
    ProjectScanResult,
    ProjectSignal,
    SelectedFile,
    Technology,
)
from src.domain.ports.llm import ILlmPort
from src.domain.ports.repositories import DEFAULT_EXCLUDED_DIRS, IFileSystemPort

logger = logging.getLogger(__name__)

MAX_SELECTED_FILES = 8
MAX_SELECTED_FILE_SIZE_BYTES = 12_000
MAX_SELECTED_EXCERPT_CHARS = 1_200


class ProjectScannerAgent(BaseAgent[ProjectScannerState]):
    """Agent that scans a local repository and builds a factual inventory.

    This agent performs file discovery, technology detection, and dependency
    extraction without any LLM interpretation - just facts.
    """

    def __init__(
        self,
        file_system: IFileSystemPort,
        llm_port: ILlmPort,
        excluded_dirs: Collection[str] | None = None,
    ) -> None:
        super().__init__("ProjectScanner")
        self.file_system = file_system
        self.llm_port = llm_port
        self._excluded_dirs = excluded_dirs or DEFAULT_EXCLUDED_DIRS

    def create_graph(self) -> Any:  # type: ignore[return]
        """Create the LangGraph state machine."""
        graph = StateGraph(ProjectScannerState)  # type: ignore

        graph.add_node("scan_files", self._scan_files_node)
        graph.add_node("detect_technologies", self._detect_technologies_node)
        graph.add_node("extract_dependencies", self._extract_dependencies_node)
        graph.add_node("select_relevant_files", self._select_relevant_files_node)
        graph.add_node("detect_project_signals", self._detect_project_signals_node)
        graph.add_node("build_result", self._build_result_node)

        graph.set_entry_point("scan_files")
        graph.add_edge("scan_files", "detect_technologies")
        graph.add_edge("detect_technologies", "extract_dependencies")
        graph.add_edge("extract_dependencies", "select_relevant_files")
        graph.add_edge("select_relevant_files", "detect_project_signals")
        graph.add_edge("detect_project_signals", "build_result")
        graph.add_edge("build_result", END)

        return graph.compile()

    def _scan_files_node(self, state: ProjectScannerState) -> ProjectScannerState:
        """Scan file system for all files in the repository."""
        root = Path(state["root_path"])
        all_files = self.file_system.list_files(
            root, "**/*", exclude_dirs=self._excluded_dirs
        )

        files = []
        for f in all_files:
            if f.is_file():
                try:
                    stat = f.stat()
                    files.append(
                        {
                            "path": str(f.relative_to(root)),
                            "size_bytes": stat.st_size,
                            "extension": f.suffix.lstrip("."),
                        }
                    )
                except OSError:
                    logger.debug("Could not stat file: %s", f)

        state["files"] = files
        return state

    def _detect_technologies_node(
        self,
        state: ProjectScannerState,
    ) -> ProjectScannerState:
        """Detect technologies based on config files."""
        root = Path(state["root_path"])
        technologies = []

        tech_configs = {
            "package.json": ("npm", "package_manager"),
            "pyproject.toml": ("Python", "language"),
            "requirements.txt": ("Python", "language"),
            "Cargo.toml": ("Rust", "language"),
            "go.mod": ("Go", "language"),
            "pom.xml": ("Maven", "build_tool"),
            "build.gradle": ("Gradle", "build_tool"),
            "docker-compose.yml": ("Docker", "container"),
            "Dockerfile": ("Docker", "container"),
            "tsconfig.json": ("TypeScript", "language"),
            "astro.config.mjs": ("Astro", "framework"),
            "next.config.js": ("Next.js", "framework"),
            "nuxt.config.ts": ("Nuxt", "framework"),
            "svelte.config.js": ("Svelte", "framework"),
            "vite.config.ts": ("Vite", "build_tool"),
            "webpack.config.js": ("Webpack", "build_tool"),
        }

        for config_file, (tech_name, tech_type) in tech_configs.items():
            if (root / config_file).exists():
                technologies.append(
                    {
                        "name": tech_name,
                        "type": tech_type,
                        "config_file": config_file,
                    }
                )

        state["technologies"] = technologies
        return state

    def _extract_dependencies_node(
        self,
        state: ProjectScannerState,
    ) -> ProjectScannerState:
        """Extract dependencies from config files."""
        root = Path(state["root_path"])
        dependencies = []

        if (root / "pyproject.toml").exists():
            try:
                content = self.file_system.read_file(root / "pyproject.toml")
                data = tomllib.loads(content)

                project_deps = data.get("project", {}).get("dependencies", [])
                for dep in project_deps:
                    if isinstance(dep, str):
                        name, version = self._parse_dependency_string(dep)
                        dependencies.append(
                            {"name": name, "version": version, "type": "runtime"}
                        )

                dep_groups = data.get("dependency-groups", {})
                for group_name, group_deps in dep_groups.items():
                    dep_type = "dev" if group_name == "dev" else "runtime"
                    for dep in group_deps:
                        if isinstance(dep, str):
                            name, version = self._parse_dependency_string(dep)
                            dependencies.append(
                                {"name": name, "version": version, "type": dep_type}
                            )
            except Exception:
                logger.debug("Failed to parse pyproject.toml")

        if (root / "package.json").exists():
            try:
                content = self.file_system.read_file(root / "package.json")
                pkg = json.loads(content)
                for name, version in pkg.get("dependencies", {}).items():
                    dependencies.append(
                        {
                            "name": name,
                            "version": version.lstrip("^~"),
                            "type": "runtime",
                        }
                    )
                for name, version in pkg.get("devDependencies", {}).items():
                    dependencies.append(
                        {
                            "name": name,
                            "version": version.lstrip("^~"),
                            "type": "dev",
                        }
                    )
            except Exception:
                logger.debug("Failed to parse package.json")

        if (root / "Cargo.toml").exists():
            try:
                content = self.file_system.read_file(root / "Cargo.toml")
                data = tomllib.loads(content)

                for name, value in data.get("dependencies", {}).items():
                    if isinstance(value, str):
                        dependencies.append(
                            {"name": name, "version": value, "type": "runtime"}
                        )
                    elif isinstance(value, dict):
                        version = value.get("version")
                        dependencies.append(
                            {
                                "name": name,
                                "version": version
                                if isinstance(version, str)
                                else None,
                                "type": "runtime",
                            }
                        )

                for name, value in data.get("dev-dependencies", {}).items():
                    if isinstance(value, str):
                        dependencies.append(
                            {"name": name, "version": value, "type": "dev"}
                        )
                    elif isinstance(value, dict):
                        version = value.get("version")
                        dependencies.append(
                            {
                                "name": name,
                                "version": version
                                if isinstance(version, str)
                                else None,
                                "type": "dev",
                            }
                        )
            except Exception:
                logger.debug("Failed to parse Cargo.toml")

        state["dependencies"] = dependencies[:50]
        return state

    def _select_relevant_files_node(
        self,
        state: ProjectScannerState,
    ) -> ProjectScannerState:
        """Select a bounded set of files as evidence for downstream analysis."""
        root = Path(state["root_path"])
        files = [FileInfo(**f) for f in state["files"]]
        selected = []

        for file_info in sorted(files, key=self._file_relevance_score):
            if len(selected) >= MAX_SELECTED_FILES:
                break
            path = root / file_info.path
            if not self._is_relevant_for_analysis(file_info):
                continue
            if file_info.size_bytes > MAX_SELECTED_FILE_SIZE_BYTES:
                continue

            try:
                content = self.file_system.read_file(path)
            except UnicodeDecodeError:
                logger.debug("Skipping non-text file: %s", path)
                continue
            except OSError:
                logger.debug("Could not read file: %s", path)
                continue

            selected.append(
                {
                    "path": file_info.path,
                    "reason": self._selection_reason(file_info.path),
                    "excerpt": content[:MAX_SELECTED_EXCERPT_CHARS],
                }
            )

        state["selected_files"] = selected
        return state

    def _detect_project_signals_node(
        self,
        state: ProjectScannerState,
    ) -> ProjectScannerState:
        """Detect factual project signals from files and directory structure."""
        paths = {f["path"] for f in state["files"]}
        signal_paths = {path for path in paths if not self._is_low_value_file(path)}
        signals = []

        architecture_paths = sorted(
            path for path in signal_paths if self._has_architectural_path_name(path)
        )
        if architecture_paths:
            signals.append(
                {
                    "name": "Architectural naming in directory structure",
                    "confidence": "medium",
                    "evidence": architecture_paths[:8],
                }
            )

        test_paths = sorted(path for path in signal_paths if self._is_test_path(path))
        if test_paths:
            signals.append(
                {
                    "name": "Automated tests",
                    "confidence": "high",
                    "evidence": test_paths[:8],
                }
            )

        automation_paths = sorted(
            path for path in signal_paths if self._is_automation_path(path)
        )
        if automation_paths:
            signals.append(
                {
                    "name": "Developer automation or runtime configuration",
                    "confidence": "high",
                    "evidence": automation_paths[:8],
                }
            )

        doc_paths = sorted(
            path for path in signal_paths if self._is_documentation_path(path)
        )
        if doc_paths:
            signals.append(
                {
                    "name": "Local project documentation",
                    "confidence": "high",
                    "evidence": doc_paths[:8],
                }
            )

        entrypoint_paths = sorted(
            path for path in signal_paths if self._is_entrypoint_path(path)
        )
        if entrypoint_paths:
            signals.append(
                {
                    "name": "Probable executable entrypoints",
                    "confidence": "medium",
                    "evidence": entrypoint_paths[:8],
                }
            )

        state["signals"] = signals
        return state

    def _parse_dependency_string(self, dep: str) -> tuple[str, str | None]:
        """Parse a dependency string into name and version.

        Args:
            dep: Dependency string like "package>=1.0" or "package[extra]".

        Returns:
            Tuple of (name, version).
        """
        match = re.match(r"([a-zA-Z0-9_-]+)(.*)", dep)
        if not match:
            return dep, None

        name, rest = match.groups()
        version_match = re.search(r"([><=!~]+[\d.]+)", rest)
        version = version_match.group(1) if version_match else None

        return name, version

    def _build_result_node(
        self,
        state: ProjectScannerState,
    ) -> ProjectScannerState:
        """Build the final scan result."""
        root = Path(state["root_path"])

        files = [FileInfo(**f) for f in state["files"]]
        technologies = [Technology(**t) for t in state["technologies"]]
        dependencies = [Dependency(**d) for d in state["dependencies"]]
        selected_files = [SelectedFile(**f) for f in state["selected_files"]]
        signals = [ProjectSignal(**s) for s in state["signals"]]

        result = ProjectScanResult(
            root_path=str(root),
            total_files=len(files),
            total_directories=len({Path(f.path).parent for f in files}),
            files=files,
            technologies=technologies,
            dependencies=dependencies,
            languages=self._detect_languages(files),
            selected_files=selected_files,
            signals=signals,
        )

        state["result"] = result.model_dump()
        return state

    def _detect_languages(self, files: list[FileInfo]) -> dict[str, int]:
        """Detect languages from file extensions."""
        ext_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "JavaScript",
            ".tsx": "TypeScript",
            ".rs": "Rust",
            ".go": "Go",
            ".java": "Java",
            ".md": "Markdown",
            ".json": "JSON",
            ".yaml": "YAML",
            ".yml": "YAML",
        }

        counts: dict[str, int] = {}
        for f in files:
            ext = f".{f.extension}" if f.extension else ""
            lang = ext_map.get(ext, "Other")
            counts[lang] = counts.get(lang, 0) + 1

        return counts

    def _file_relevance_score(self, file_info: FileInfo) -> tuple[int, str]:
        """Sort files by usefulness for technical analysis."""
        path = file_info.path
        if self._is_readme_path(path):
            return 0, path
        if self._is_manifest_path(path):
            return 1, path
        if self._is_automation_path(path):
            return 2, path
        if self._is_documentation_path(path):
            return 3, path
        if self._is_entrypoint_path(path):
            return 4, path
        if self._has_architectural_path_name(path):
            return 5, path
        if self._is_test_path(path):
            return 6, path
        if self._is_shallow_source_file(path):
            return 7, path
        return 99, path

    def _is_relevant_for_analysis(self, file_info: FileInfo) -> bool:
        """Check whether a file should be offered as analysis evidence."""
        return (
            self._is_text_file(file_info)
            and not self._is_low_value_file(file_info.path)
            and self._file_relevance_score(file_info)[0] < 99
        )

    def _selection_reason(self, path: str) -> str:
        """Explain why a file was selected for analysis."""
        if self._is_readme_path(path):
            return "Project overview"
        if self._is_manifest_path(path):
            return "Project manifest"
        if self._is_automation_path(path):
            return "Automation or runtime configuration"
        if self._is_documentation_path(path):
            return "Local project documentation"
        if self._is_entrypoint_path(path):
            return "Probable executable entrypoint"
        if self._has_architectural_path_name(path):
            return "Architectural naming signal"
        if self._is_test_path(path):
            return "Representative test"
        if self._is_shallow_source_file(path):
            return "Representative source file"
        return "Relevant project file"

    def _is_text_file(self, file_info: FileInfo) -> bool:
        """Check whether a file extension is safe to read as text evidence."""
        return file_info.extension in {
            "",
            "cfg",
            "css",
            "go",
            "html",
            "java",
            "js",
            "json",
            "jsx",
            "md",
            "py",
            "rs",
            "toml",
            "ts",
            "tsx",
            "txt",
            "xml",
            "yaml",
            "yml",
        }

    def _is_low_value_file(self, path: str) -> bool:
        """Check whether a file is unlikely to add useful analysis evidence."""
        return Path(path).name in {"__init__.py"}

    def _is_readme_path(self, path: str) -> bool:
        """Check whether a path is a README-like overview."""
        return Path(path).name.lower().startswith("readme")

    def _is_manifest_path(self, path: str) -> bool:
        """Check whether a path is a common project manifest."""
        return Path(path).name.lower() in {
            "cargo.toml",
            "go.mod",
            "package.json",
            "pom.xml",
            "pyproject.toml",
            "requirements.txt",
            "setup.cfg",
            "setup.py",
        }

    def _is_automation_path(self, path: str) -> bool:
        """Check whether a path describes automation or runtime setup."""
        name = Path(path).name.lower()
        return (
            name
            in {
                "docker-compose.yml",
                "docker-compose.yaml",
                "dockerfile",
                "justfile",
                "makefile",
                "taskfile.yml",
                "taskfile.yaml",
            }
            or ".github/workflows/" in path.lower()
        )

    def _is_documentation_path(self, path: str) -> bool:
        """Check whether a path looks like local project documentation."""
        parts = self._path_parts_lower(path)
        return any(part in {"doc", "docs", "documentation"} for part in parts)

    def _is_entrypoint_path(self, path: str) -> bool:
        """Check whether a path looks like an executable entrypoint."""
        stem = Path(path).stem.lower()
        return stem in {
            "app",
            "cli",
            "cmd",
            "index",
            "main",
            "manage",
            "server",
        }

    def _is_test_path(self, path: str) -> bool:
        """Check whether a path looks like a test or spec file."""
        parts = self._path_parts_lower(path)
        name = Path(path).name.lower()
        return (
            any(part in {"spec", "specs", "test", "tests"} for part in parts)
            or name.startswith(("test_", "spec_"))
            or name.endswith(
                ("_test.py", ".spec.ts", ".test.ts", ".spec.js", ".test.js")
            )
        )

    def _has_architectural_path_name(self, path: str) -> bool:
        """Check for architecture-oriented names without assuming layout."""
        parts = set(self._path_parts_lower(path))
        architecture_names = {
            "adapter",
            "adapters",
            "application",
            "domain",
            "entities",
            "infrastructure",
            "ports",
            "repository",
            "repositories",
            "service",
            "services",
            "use_cases",
            "usecases",
        }
        return bool(parts & architecture_names)

    def _is_shallow_source_file(self, path: str) -> bool:
        """Check whether a path is a shallow source file worth sampling."""
        suffix = Path(path).suffix.lstrip(".")
        source_extensions = {"go", "java", "js", "jsx", "py", "rs", "ts", "tsx"}
        return suffix in source_extensions and len(Path(path).parts) <= 4

    def _path_parts_lower(self, path: str) -> tuple[str, ...]:
        """Return normalized lower-case path components."""
        return tuple(part.lower() for part in Path(path).parts)

    def scan(self, path: str) -> ProjectScanResult:
        """Scan a repository and return the result.

        Args:
            path: Root directory of the repository.

        Returns:
            Project scan result.
        """
        initial_state: ProjectScannerState = {
            "root_path": path,
            "files": [],
            "technologies": [],
            "dependencies": [],
            "selected_files": [],
            "signals": [],
            "result": None,
        }

        final_state = self.run(initial_state)
        return ProjectScanResult(**final_state["result"])
