"""Point d'entree MCP en transport **stdio** (clients qui lancent un sous-process Python).

Voir `docs/mcp.md` dans le depot racine pour la configuration Cursor / Compose / HTTP."""

from __future__ import annotations

import logging
import os

_logger = logging.getLogger(__name__)


def main() -> None:
    level_name = os.environ.get("LOGLEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level, format="%(levelname)s %(name)s %(message)s")

    from orchestrateur_mcp.app import mcp

    _logger.info(
        "Demarrage MCP stdio vers ORCHESTRATOR_API_BASE=%s",
        os.environ.get("ORCHESTRATOR_API_BASE", "http://localhost:8000"),
    )

    # Ref. SDK : mcp.server.fastmcp.FastMCP.run(transport="stdio")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
