from __future__ import annotations

from fnmatch import fnmatch
import os
from pathlib import Path
from typing import Iterable

from core.contracts import AuditScope, EvidenceRef, RepoAnalysisAxis, RepoInventory, RepoTarget
from core.memory import SharedMemory

LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".md": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".json": "json",
    ".sh": "shell",
    ".ps1": "powershell",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".env": "dotenv",
}

IMPORTANT_FILENAMES = {
    "readme.md",
    "pyproject.toml",
    "package.json",
    "package-lock.json",
    "poetry.lock",
    "requirements.txt",
    "dockerfile",
    "compose.yaml",
    "compose.yml",
    ".env.example",
    ".gitignore",
}

AXIS_FILE_HINTS: dict[RepoAnalysisAxis, tuple[str, ...]] = {
    "architecture": ("README.md", "docs/", "compose.yaml", "compose.yml", "docker/", "api/", "core/"),
    "tests": ("tests/", "test_", "pytest.ini", "pyproject.toml"),
    "docs": ("README.md", "docs/"),
    "security": (".env", ".env.example", "compose.yaml", "compose.yml", "docker/", "security"),
    "dependencies": ("pyproject.toml", "requirements.txt", "package.json", "poetry.lock", "compose.yaml", "compose.yml"),
}

AXIS_SEARCH_TERMS: dict[RepoAnalysisAxis, tuple[str, ...]] = {
    "architecture": ("FastAPI", "docker", "orchestrator"),
    "tests": ("pytest", "test_", "assert "),
    "docs": ("TODO", "README", "docs"),
    "security": ("SECRET", "TOKEN", "PASSWORD"),
    "dependencies": ("dependencies", "requires-python", "image:"),
}


class RepoCapabilities:
    def __init__(
        self,
        target: RepoTarget,
        scope: AuditScope,
        memory: SharedMemory | None = None,
        role: str = "research",
    ) -> None:
        self.root_path = Path(target.root_path).resolve()
        if not self.root_path.exists() or not self.root_path.is_dir():
            raise ValueError(f"Repo root '{self.root_path}' does not exist or is not a directory.")
        self.scope = scope
        self.memory = memory
        self.role = role

    def list_files(self) -> list[str]:
        files = self._scoped_files()
        self._log(
            "repo.list_tree",
            {
                "root_path": str(self.root_path),
                "returned_files": len(files),
                "max_files": self.scope.read_limits.max_files,
            },
        )
        return files

    def read_text_file(self, relative_path: str) -> str:
        path = self._resolve_relative_path(relative_path)
        if not path.is_file():
            raise ValueError(f"Path '{relative_path}' is not a readable file.")
        if not self._is_scoped(path):
            raise ValueError(f"Path '{relative_path}' is outside the current audit scope.")

        content = self._read_text(path)
        self._log(
            "repo.read_text_file",
            {
                "path": self._relative_path(path),
                "bytes_returned": len(content.encode("utf-8", errors="ignore")),
            },
        )
        return content

    def search_code(self, term: str, max_results: int | None = None) -> list[EvidenceRef]:
        cleaned_term = term.strip()
        if not cleaned_term:
            return []

        limit = max_results if max_results is not None else self.scope.read_limits.max_matches
        results: list[EvidenceRef] = []
        needle = cleaned_term.lower()
        for relative_path in self._scoped_files():
            path = self._resolve_relative_path(relative_path)
            if not self._is_text_file(path):
                continue
            content = self._read_text(path)
            for index, line in enumerate(content.splitlines(), start=1):
                if needle in line.lower():
                    results.append(
                        EvidenceRef(
                            path=relative_path,
                            kind="search_hit",
                            reason=f"Match sur '{cleaned_term}'",
                            excerpt=line.strip()[:240],
                            line_start=index,
                            line_end=index,
                        )
                    )
                    if len(results) >= limit:
                        self._log(
                            "repo.search_code",
                            {"term": cleaned_term, "results": len(results), "truncated": True},
                        )
                        return results

        self._log(
            "repo.search_code",
            {"term": cleaned_term, "results": len(results), "truncated": False},
        )
        return results

    def build_inventory(self) -> RepoInventory:
        files = self._scoped_files()
        important_files = sorted(path for path in files if self._is_important_path(path))
        languages = sorted({self._detect_language(path) for path in files if self._detect_language(path)})
        inventory = RepoInventory(
            root_path=str(self.root_path),
            total_files_scanned=len(files),
            top_level_entries=self._top_level_entries(),
            detected_languages=languages,
            important_files=important_files[: min(len(important_files), 20)],
            scanned_paths=files,
            truncated=len(files) >= self.scope.read_limits.max_files,
        )
        self._log(
            "repo.inventory",
            {
                "total_files_scanned": inventory.total_files_scanned,
                "important_files": len(inventory.important_files),
                "languages": inventory.detected_languages,
            },
        )
        return inventory

    def collect_evidence(
        self,
        analysis_axes: Iterable[RepoAnalysisAxis],
        search_terms: Iterable[str],
    ) -> tuple[RepoInventory, list[EvidenceRef], dict[str, list[str]]]:
        axes = list(dict.fromkeys(analysis_axes))
        inventory = self.build_inventory()
        evidence: list[EvidenceRef] = []
        coverage_map: dict[str, set[str]] = {axis: set() for axis in axes}

        max_matches = self.scope.read_limits.max_matches
        relevant_files = [
            path for path in inventory.important_files if any(axis in self._axes_for_path(path, axes) for axis in axes)
        ]
        file_budget = min(len(relevant_files), max(1, min(10, max_matches // 2 or 1)))

        for relative_path in relevant_files[:file_budget]:
            path = self._resolve_relative_path(relative_path)
            excerpt = self._read_text(path)
            matched_axes = self._axes_for_path(relative_path, axes)
            evidence.append(
                EvidenceRef(
                    path=relative_path,
                    kind="important_file",
                    reason=f"Fichier pivot pour {', '.join(matched_axes)}",
                    excerpt=self._compact_excerpt(excerpt),
                    line_start=1,
                    line_end=min(len(excerpt.splitlines()), 40) or 1,
                )
            )
            for axis in matched_axes:
                coverage_map[axis].add(relative_path)

        remaining_budget = max_matches - len(evidence)
        for term in self._merged_search_terms(axes, search_terms):
            if remaining_budget <= 0:
                break
            search_hits = self.search_code(term, max_results=remaining_budget)
            for hit in search_hits:
                evidence.append(hit)
                for axis in self._axes_for_path(hit.path, axes):
                    coverage_map[axis].add(hit.path)
            remaining_budget = max_matches - len(evidence)

        return inventory, evidence, {axis: sorted(paths) for axis, paths in coverage_map.items()}

    def _merged_search_terms(
        self,
        analysis_axes: Iterable[RepoAnalysisAxis],
        search_terms: Iterable[str],
    ) -> list[str]:
        merged: list[str] = []
        for axis in analysis_axes:
            merged.extend(AXIS_SEARCH_TERMS.get(axis, ()))
        merged.extend(term for term in search_terms if term.strip())

        unique_terms: list[str] = []
        seen: set[str] = set()
        for term in merged:
            normalized = term.strip().lower()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique_terms.append(term.strip())
        return unique_terms[:10]

    def _top_level_entries(self) -> list[str]:
        entries: list[str] = []
        for child in sorted(self.root_path.iterdir(), key=lambda entry: entry.name.lower()):
            relative_name = child.name
            if self._matches_any_rule(relative_name, self.scope.exclude_paths):
                continue
            if self.scope.include_paths and not self._matches_any_rule(relative_name, self.scope.include_paths):
                continue
            entries.append(relative_name)
        return entries[:20]

    def _scoped_files(self) -> list[str]:
        files: list[str] = []
        for current_root, dirnames, filenames in os.walk(self.root_path):
            current_path = Path(current_root)
            dirnames[:] = [
                dirname
                for dirname in sorted(dirnames, key=str.lower)
                if not self._matches_any_rule(
                    (current_path / dirname).resolve().relative_to(self.root_path).as_posix(),
                    self.scope.exclude_paths,
                )
            ]
            for filename in sorted(filenames, key=str.lower):
                path = current_path / filename
                if not self._is_scoped(path):
                    continue
                files.append(self._relative_path(path))
                if len(files) >= self.scope.read_limits.max_files:
                    return files
        return files

    def _is_scoped(self, path: Path) -> bool:
        try:
            relative = self._relative_path(path)
        except ValueError:
            return False
        if self._matches_any_rule(relative, self.scope.exclude_paths):
            return False
        if self.scope.include_paths and not self._matches_any_rule(relative, self.scope.include_paths):
            return False
        return True

    def _resolve_relative_path(self, relative_path: str) -> Path:
        candidate = (self.root_path / relative_path).resolve()
        if not candidate.is_relative_to(self.root_path):
            raise ValueError(f"Path '{relative_path}' escapes the repo root.")
        return candidate

    def _relative_path(self, path: Path) -> str:
        return path.resolve().relative_to(self.root_path).as_posix()

    def _matches_any_rule(self, relative_path: str, rules: Iterable[str]) -> bool:
        normalized_path = relative_path.replace("\\", "/").strip("/")
        path_parts = normalized_path.split("/")
        for rule in rules:
            normalized_rule = rule.replace("\\", "/").strip("/")
            if not normalized_rule:
                continue
            if (
                normalized_path == normalized_rule
                or normalized_path.startswith(f"{normalized_rule}/")
                or fnmatch(normalized_path, normalized_rule)
                or fnmatch(normalized_path, f"{normalized_rule}/**")
                or normalized_rule in path_parts
            ):
                return True
        return False

    def _detect_language(self, relative_path: str) -> str | None:
        if relative_path.lower().endswith(".env.example"):
            return "dotenv"
        return LANGUAGE_BY_SUFFIX.get(Path(relative_path).suffix.lower())

    def _is_important_path(self, relative_path: str) -> bool:
        path = relative_path.lower()
        filename = Path(relative_path).name.lower()
        if filename in IMPORTANT_FILENAMES:
            return True
        return path.startswith("docs/") or path.startswith("tests/") or path.startswith("docker/")

    def _axes_for_path(
        self,
        relative_path: str,
        analysis_axes: Iterable[RepoAnalysisAxis],
    ) -> list[RepoAnalysisAxis]:
        matched_axes: list[RepoAnalysisAxis] = []
        for axis in analysis_axes:
            hints = AXIS_FILE_HINTS.get(axis, ())
            if any(
                relative_path == hint
                or relative_path.startswith(hint)
                or Path(relative_path).name == hint
                or hint in relative_path
                for hint in hints
            ):
                matched_axes.append(axis)
        return matched_axes

    def _is_text_file(self, path: Path) -> bool:
        try:
            sample = path.read_bytes()[:1024]
        except OSError:
            return False
        return b"\x00" not in sample

    def _read_text(self, path: Path) -> str:
        content = path.read_text(encoding="utf-8", errors="ignore")
        max_bytes = self.scope.read_limits.max_bytes_per_file
        encoded = content.encode("utf-8", errors="ignore")
        if len(encoded) <= max_bytes:
            return content
        return encoded[:max_bytes].decode("utf-8", errors="ignore")

    def _compact_excerpt(self, content: str) -> str:
        lines = [line.rstrip() for line in content.splitlines()[:40]]
        return "\n".join(lines).strip()

    def _log(self, action: str, data: dict[str, object]) -> None:
        if not self.memory:
            return
        self.memory.append_event(
            self.role,
            f"Capability {action} invoked.",
            data=data,
            event_type="tool",
        )
