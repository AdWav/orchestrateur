from __future__ import annotations

import re
from typing import Literal

ScaffoldKind = Literal["fizzbuzz", "generic_python"]


def detect_scaffold_kind(objective: str) -> ScaffoldKind:
    normalized = objective.lower()
    if "fizzbuzz" in normalized or "fizz buzz" in normalized:
        return "fizzbuzz"
    return "generic_python"


def slugify_objective(objective: str, *, max_length: int = 48) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", objective.lower()).strip("-")
    if not slug:
        return "feature"
    return slug[:max_length].strip("-") or "feature"


def scaffold_files(kind: ScaffoldKind, objective: str) -> dict[str, str]:
    if kind == "fizzbuzz":
        return _fizzbuzz_files(objective)
    return _generic_python_files(objective)


def _fizzbuzz_files(objective: str) -> dict[str, str]:
    return {
        "README.md": f"""# FizzBuzz

Objectif du benchmark : {objective.strip()}

## Executer

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
pytest -q
python -m src.fizzbuzz
```

Le script affiche la sequence 1..100 sur la sortie standard.
""",
        "requirements.txt": "pytest>=8.0\n",
        "pyproject.toml": """[project]
name = "benchmark-fizzbuzz"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
""",
        "src/__init__.py": "",
        "src/fizzbuzz.py": '''"""Implementation FizzBuzz 1..100."""

from __future__ import annotations


def fizzbuzz(n: int) -> str:
    if n <= 0:
        raise ValueError("n must be positive")
    if n % 15 == 0:
        return "FizzBuzz"
    if n % 3 == 0:
        return "Fizz"
    if n % 5 == 0:
        return "Buzz"
    return str(n)


def fizzbuzz_sequence(limit: int = 100) -> list[str]:
    if limit < 1:
        raise ValueError("limit must be >= 1")
    return [fizzbuzz(i) for i in range(1, limit + 1)]


def main() -> None:
    for value in fizzbuzz_sequence(100):
        print(value)


if __name__ == "__main__":
    main()
''',
        "tests/__init__.py": "",
        "tests/test_fizzbuzz.py": '''import pytest

from src.fizzbuzz import fizzbuzz, fizzbuzz_sequence


@pytest.mark.parametrize(
    ("n", "expected"),
    [
        (1, "1"),
        (3, "Fizz"),
        (5, "Buzz"),
        (15, "FizzBuzz"),
        (30, "FizzBuzz"),
    ],
)
def test_fizzbuzz_unit(n: int, expected: str) -> None:
    assert fizzbuzz(n) == expected


def test_fizzbuzz_rejects_non_positive() -> None:
    with pytest.raises(ValueError):
        fizzbuzz(0)


def test_sequence_length_and_sample() -> None:
    seq = fizzbuzz_sequence(100)
    assert len(seq) == 100
    assert seq[0] == "1"
    assert seq[2] == "Fizz"
    assert seq[4] == "Buzz"
    assert seq[14] == "FizzBuzz"
''',
        "docs/feature.md": f"""# Documentation

## Objectif

{objective.strip()}

## Comportement

- Multiples de 3 : `Fizz`
- Multiples de 5 : `Buzz`
- Multiples de 15 : `FizzBuzz`
- Sinon : le nombre en texte
""",
    }


def _generic_python_files(objective: str) -> dict[str, str]:
    return {
        "README.md": f"""# Benchmark feature

Objectif : {objective.strip()}

## Executer

```bash
python -m venv .venv
pip install -r requirements.txt
pytest -q
```
""",
        "requirements.txt": "pytest>=8.0\n",
        "pyproject.toml": """[project]
name = "benchmark-feature"
version = "0.1.0"
requires-python = ">=3.10"

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
""",
        "src/__init__.py": "",
        "src/feature.py": f'''"""Implementation minimale — objectif: {objective.strip()[:120]}"""

from __future__ import annotations


def solve(input_value: str) -> str:
    """Point d'entree metier — a enrichir selon l'objectif."""
    return input_value.strip() or "ok"
''',
        "tests/__init__.py": "",
        "tests/test_feature.py": """from src.feature import solve


def test_solve_returns_trimmed_value() -> None:
    assert solve("  hello  ") == "hello"


def test_solve_default_ok() -> None:
    assert solve("") == "ok"
""",
        "docs/feature.md": f"# Feature\n\n{objective.strip()}\n",
    }
