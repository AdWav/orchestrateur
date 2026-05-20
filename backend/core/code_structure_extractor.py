from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any, Callable

SOURCE_SUFFIXES = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
    ".java": "java",
    ".rs": "rust",
    ".cs": "csharp",
    ".php": "php",
    ".rb": "ruby",
}

CLASS_PATTERNS: dict[str, re.Pattern[str]] = {
    "python": re.compile(r"^\s*class\s+([A-Za-z_]\w*)", re.MULTILINE),
    "typescript": re.compile(r"^\s*(?:export\s+)?(?:abstract\s+)?class\s+([A-Za-z_]\w*)", re.MULTILINE),
    "javascript": re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z_]\w*)", re.MULTILINE),
    "go": re.compile(r"^\s*type\s+([A-Za-z_]\w*)\s+struct\b", re.MULTILINE),
    "java": re.compile(r"^\s*(?:public\s+|private\s+|protected\s+)?(?:abstract\s+)?class\s+([A-Za-z_]\w*)", re.MULTILINE),
    "rust": re.compile(r"^\s*(?:pub\s+)?struct\s+([A-Za-z_]\w*)", re.MULTILINE),
    "csharp": re.compile(r"^\s*(?:public\s+|internal\s+)?(?:partial\s+)?class\s+([A-Za-z_]\w*)", re.MULTILINE),
    "php": re.compile(r"^\s*(?:abstract\s+)?class\s+([A-Za-z_]\w*)", re.MULTILINE),
    "ruby": re.compile(r"^\s*class\s+([A-Za-z_]\w*)", re.MULTILINE),
}

FUNCTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "python": re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)", re.MULTILINE),
    "typescript": re.compile(
        r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_]\w*)",
        re.MULTILINE,
    ),
    "javascript": re.compile(
        r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_]\w*)",
        re.MULTILINE,
    ),
    "go": re.compile(r"^\s*func\s+(?:\([^)]+\)\s+)?([A-Za-z_]\w*)\s*\(", re.MULTILINE),
    "java": re.compile(
        r"^\s*(?:public|private|protected).+\s+([A-Za-z_]\w*)\s*\(",
        re.MULTILINE,
    ),
    "rust": re.compile(r"^\s*(?:pub\s+)?fn\s+([A-Za-z_]\w*)", re.MULTILINE),
    "csharp": re.compile(r"^\s*(?:public|private|protected|internal).+\s+([A-Za-z_]\w*)\s*\(", re.MULTILINE),
    "php": re.compile(r"^\s*(?:public|private|protected)?\s*function\s+([A-Za-z_]\w*)", re.MULTILINE),
    "ruby": re.compile(r"^\s*def\s+([A-Za-z_]\w*)", re.MULTILINE),
}

IMPORT_PATTERNS: dict[str, re.Pattern[str]] = {
    "python": re.compile(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.MULTILINE),
    "typescript": re.compile(r"^\s*import\s+.+from\s+['\"]([^'\"]+)['\"]", re.MULTILINE),
    "javascript": re.compile(r"^\s*import\s+.+from\s+['\"]([^'\"]+)['\"]", re.MULTILINE),
    "go": re.compile(r'^\s*import\s+(?:\(\s*)?["\']([^"\']+)["\']', re.MULTILINE),
    "java": re.compile(r"^\s*import\s+([\w.]+)\s*;", re.MULTILINE),
    "rust": re.compile(r"^\s*use\s+([\w:]+(?:::\*)?)", re.MULTILINE),
    "csharp": re.compile(r"^\s*using\s+([\w.]+)\s*;", re.MULTILINE),
    "php": re.compile(r"^\s*(?:use|require(?:_once)?|include(?:_once)?)\s+([^;]+)", re.MULTILINE),
    "ruby": re.compile(r"^\s*(?:require|require_relative)\s+['\"]([^'\"]+)['\"]", re.MULTILINE),
}

ENTRY_HINTS = (
    "main.py",
    "main.ts",
    "main.js",
    "index.ts",
    "index.js",
    "app.py",
    "cli.py",
    "server.py",
    "manage.py",
)


def _language_for_path(relative_path: str) -> str | None:
    suffix = PurePosixPath(relative_path).suffix.lower()
    return SOURCE_SUFFIXES.get(suffix)


def _module_id(relative_path: str) -> str:
    path = PurePosixPath(relative_path)
    if path.suffix:
        path = path.with_suffix("")
    return ".".join(part for part in path.parts if part)


def _layer_for_path(relative_path: str) -> str:
    parts = PurePosixPath(relative_path).parts
    if not parts:
        return "root"
    top = parts[0].lower()
    if top in {"frontend", "client", "ui", "web"}:
        return "frontend"
    if top in {"backend", "server", "api", "core"}:
        return "backend"
    if top in {"tests", "test", "__tests__"}:
        return "tests"
    if top in {"docs", "doc"}:
        return "docs"
    if top in {"catalog", "config", "infra", "deploy", "docker"}:
        return "infra"
    return top


def _extract_imports(language: str, content: str) -> list[str]:
    pattern = IMPORT_PATTERNS.get(language)
    if not pattern:
        return []
    imports: list[str] = []
    for match in pattern.finditer(content):
        groups = [group for group in match.groups() if group]
        if not groups:
            continue
        token = groups[0].strip().strip("\"'")
        if token and token not in imports:
            imports.append(token)
    return imports[:20]


def extract_structure(
    *,
    root_path: str,
    file_paths: list[str],
    read_text: Callable[[str], str],
    max_files: int = 25,
) -> dict[str, Any]:
    """Construit un modele structurel portable a partir d'une liste de fichiers sources."""
    components: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    entry_points: list[str] = []
    languages: set[str] = set()
    scanned = 0

    prioritized = sorted(
        file_paths,
        key=lambda path: (
            0 if PurePosixPath(path).name.lower() in ENTRY_HINTS else 1,
            0 if "test" not in path.lower() else 2,
            path.lower(),
        ),
    )

    for relative_path in prioritized:
        language = _language_for_path(relative_path)
        if not language:
            continue
        if scanned >= max_files:
            break
        try:
            content = read_text(relative_path)
        except (OSError, ValueError):
            continue

        scanned += 1
        languages.add(language)
        module_id = _module_id(relative_path)
        layer = _layer_for_path(relative_path)

        classes = CLASS_PATTERNS.get(language).findall(content)[:12] if language in CLASS_PATTERNS else []
        functions = (
            FUNCTION_PATTERNS.get(language).findall(content)[:15] if language in FUNCTION_PATTERNS else []
        )
        imports = _extract_imports(language, content)

        components.append(
            {
                "id": module_id,
                "kind": "module",
                "path": relative_path,
                "language": language,
                "layer": layer,
                "classes": classes,
                "functions": functions[:10],
                "imports": imports,
            }
        )

        if PurePosixPath(relative_path).name.lower() in ENTRY_HINTS:
            entry_points.append(relative_path)

        for imported in imports:
            relations.append(
                {
                    "from": module_id,
                    "to": imported,
                    "kind": "imports",
                    "source_path": relative_path,
                }
            )

    layers = sorted({component["layer"] for component in components})
    return {
        "root_path": root_path,
        "languages": sorted(languages),
        "layers": layers,
        "components": components,
        "relations": relations[:80],
        "entry_points": entry_points[:10],
        "stats": {
            "files_analyzed": scanned,
            "component_count": len(components),
            "relation_count": len(relations),
        },
    }
