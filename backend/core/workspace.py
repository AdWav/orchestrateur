from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from core.contracts import AgentOutput, WorkflowRun, WorkspaceInfo
from core.workspace_templates import detect_scaffold_kind, scaffold_files, slugify_objective


def workspace_root() -> Path:
    configured = os.environ.get("WORKSPACE_ROOT", "workspaces").strip()
    root = Path(configured)
    if not root.is_absolute():
        # Project root = parent of backend package
        project_root = Path(__file__).resolve().parents[2]
        root = project_root / root
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


@dataclass(frozen=True)
class BenchmarkWorkspaceRun:
    run_id: str
    root: Path

    def team_dir(self, team_id: str) -> Path:
        return self.root / team_id


def create_benchmark_workspace(objective: str) -> BenchmarkWorkspaceRun:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    slug = slugify_objective(objective)
    run_id = f"{stamp}-{slug}"
    root = workspace_root() / run_id
    root.mkdir(parents=True, exist_ok=False)
    return BenchmarkWorkspaceRun(run_id=run_id, root=root)


def _safe_relative_path(relative: str) -> Path:
    cleaned = relative.replace("\\", "/").strip().lstrip("/")
    if not cleaned or cleaned in {".", ".."}:
        raise ValueError(f"Invalid relative path: {relative!r}")
    parts = Path(cleaned).parts
    if ".." in parts:
        raise ValueError(f"Path traversal rejected: {relative!r}")
    return Path(*parts)


def write_file(base_dir: Path, relative_path: str, content: str) -> Path:
    base = base_dir.resolve()
    target = (base / _safe_relative_path(relative_path)).resolve()
    if not str(target).startswith(str(base)):
        raise ValueError(f"Path escapes workspace: {relative_path}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def _collect_artifact_paths(outputs: list[AgentOutput]) -> list[str]:
    path_keys = (
        "source_files",
        "test_files",
        "documentation",
        "backend_source_files",
        "frontend_source_files",
        "migration_files",
    )
    collected: list[str] = []
    seen: set[str] = set()
    for output in outputs:
        artifacts = output.artifacts if isinstance(output.artifacts, dict) else {}
        for key in path_keys:
            value = artifacts.get(key)
            if not isinstance(value, list):
                continue
            for entry in value:
                if isinstance(entry, str) and entry not in seen:
                    seen.add(entry)
                    collected.append(entry)
    return collected


def _pipeline_notes(outputs: list[AgentOutput]) -> str:
    lines = ["# Trace pipeline\n"]
    for output in outputs:
        lines.append(f"## {output.role}\n")
        summary = (output.summary or "").strip()
        if summary:
            lines.append(summary)
        else:
            lines.append("_Pas de resume._")
        lines.append("\n")
    return "\n".join(lines)


def _placeholder_for_artifact_path(relative: str, objective: str) -> str:
    if relative.endswith(".md"):
        return f"# {relative}\n\nObjectif : {objective.strip()}\n\n_Contenu genere par le pipeline (placeholder)._ \n"
    if relative.endswith(".py"):
        return f'"""Placeholder for {relative}."""\n\n# Objectif: {objective.strip()[:200]}\n'
    if relative.endswith((".ts", ".tsx")):
        return f"// Placeholder for {relative}\n// Objective: {objective.strip()[:200]}\nexport {{}};\n"
    return f"Artifact placeholder for {relative}\n"


def materialize_team_workspace(
    team_dir: Path,
    run: WorkflowRun,
    *,
    execute_tests: bool = True,
) -> WorkspaceInfo:
    team_dir.mkdir(parents=True, exist_ok=True)
    objective = run.request.objective
    kind = detect_scaffold_kind(objective)
    files_written: list[str] = []

    for relative, content in scaffold_files(kind, objective).items():
        write_file(team_dir, relative, content)
        files_written.append(relative)

    write_file(team_dir, "docs/PIPELINE.md", _pipeline_notes(run.outputs))

    for artifact_path in _collect_artifact_paths(run.outputs):
        normalized = artifact_path.replace("\\", "/")
        if normalized in files_written:
            continue
        if not re.search(r"\.(py|md|ts|tsx|sql|json|txt)$", normalized, re.I):
            continue
        try:
            write_file(
                team_dir,
                normalized,
                _placeholder_for_artifact_path(normalized, objective),
            )
            files_written.append(normalized)
        except ValueError:
            continue

    test_command = "pytest -q"
    runner_exec_command = build_runner_exec_command(team_dir)
    tests_passed: bool | None = None
    test_output: str | None = None

    if execute_tests:
        tests_passed, test_output = _run_pytest(team_dir)

    files_written.sort()
    return WorkspaceInfo(
        path=str(team_dir),
        files=files_written,
        test_command=test_command,
        runner_exec_command=runner_exec_command,
        tests_passed=tests_passed,
        test_output=test_output,
    )


def build_runner_exec_command(team_dir: Path) -> str | None:
    """Commande pour relancer les tests dans le conteneur workspace-runner (mode Compose)."""
    if os.environ.get("ORCHESTRATOR_MODE") != "compose":
        return None
    root = workspace_root()
    try:
        relative = team_dir.resolve().relative_to(root)
    except ValueError:
        return None
    container_path = f"/workspaces/{relative.as_posix()}"
    return (
        "docker compose exec workspace-runner bash -lc "
        f'"cd {container_path} && pytest -q"'
    )


def _run_pytest(team_dir: Path) -> tuple[bool | None, str | None]:
    if not (team_dir / "tests").is_dir():
        return None, None
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=team_dir,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)

    output = (completed.stdout or "") + (completed.stderr or "")
    output = output.strip() or f"exit code {completed.returncode}"
    return completed.returncode == 0, output[:8000]
