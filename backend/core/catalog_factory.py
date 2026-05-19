from __future__ import annotations

import os
from pathlib import Path

from core.definition_catalog import DefinitionCatalog, FileDefinitionCatalog
from core.mariadb_catalog import MariadbDefinitionCatalog


def build_definition_catalog() -> DefinitionCatalog:
    backend = os.getenv("CATALOG_BACKEND", "file").lower()
    if backend == "mariadb":
        return MariadbDefinitionCatalog()
    root_path = os.getenv("ORCHESTRATOR_CATALOG_ROOT")
    if root_path:
        return FileDefinitionCatalog(root_path)
    default_root = Path(__file__).resolve().parents[2] / "catalog"
    return FileDefinitionCatalog(default_root)
