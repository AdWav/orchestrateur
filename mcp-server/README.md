# Serveur MCP — Orchestrateur

Documentation complete (transports **stdio** / **Streamable HTTP**, Cursor, Compose, caches Docker, depannage) : **[`docs/mcp.md`](../docs/mcp.md)**.

Resume rapide :

| Mode | Endpoint / commande |
|------|---------------------|
| **HTTP** (Compose) | `GET /healthz` ; MCP sur **`http://localhost:8010/mcp`** |
| **stdio** (Cursor…) | depuis ce dossier : `pip install -e .` puis `python -m orchestrateur_mcp` avec `ORCHESTRATOR_API_BASE` |

Iterations **sans rebuild** sur le code MCP : depuis la racine du depot  
`docker compose -f compose.yaml -f compose.dev-mcp.yml up mcp-server` (volume + `--reload`). Voir `docs/mcp.md`.

Dependencies image Docker liste dans **`requirements-container.txt`** (couche mise en cache avant le code Python).
