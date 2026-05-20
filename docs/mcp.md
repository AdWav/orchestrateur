# MCP (Model Context Protocol) — Orchestrateur

Ce depot expose un **bridge MCP** vers l’API FastAPI du backend (`/definitions/*`, `/workflows/*`). L’implementation s’appuie sur le **SDK Python officiel** du Model Context Protocol (package PyPI [`mcp`](https://pypi.org/project/mcp/), projet [`modelcontextprotocol/python-sdk`](https://github.com/modelcontextprotocol/python-sdk)) et la couche ergonomique **`FastMCP`** documentée ici : [Building MCP Servers](https://modelcontextprotocol.github.io/python-sdk/).

## Deux transports (choisir celui qui matche votre client)

| Transport | Usage typique | URL / commande |
|-----------|---------------|----------------|
| **stdio** | Cursor, Claude Desktop, IDE qui spawn un process MCP | `python -m orchestrateur_mcp` (ou `orchestrateur-mcp`) |
| **Streamable HTTP** | Client distant (`http://`), inspector HTTP, autres outils MCP « remote » | `http://localhost:8010/mcp` (avec Docker Compose par defaut) |

Le protocole est le meme ; seul **le canal** change. Cursor est en general plus simple avec **stdio** (moins de friction sur DNS / en-tete `Accept` / port).

## Flux HTTP Docker (Compose)

Apres `docker compose up --build` :

- Sonde infra (hors MCP) : `GET http://localhost:8010/healthz`
- Sessions MCP (**Streamable HTTP**) : **`http://localhost:8010/mcp`**

Le SDK verifie des en‑tetes **`Accept`** stricts (`application/json`, `text/event-stream` selon methode et mode). Pour limiter les `406`, le bridge active par defaut le middleware **`MCP_RELAX_ACCEPT_HEADERS=true`** qui complete `Accept` sur les chemins se terminant par `/mcp`.

### Variables principales (`compose.yaml`)

- `ORCHESTRATOR_API_BASE` : dans Compose, **`http://backend:8000`**
- `ORCHESTRATOR_HTTP_TIMEOUT_SECONDS` : delai avant echec des appels outils (`900` dans Compose pour workflows longs)
- `MCP_RELAX_ACCEPT_HEADERS` : passer a `false` pour le comportement strict du SDK uniquement

## Flux stdio — recommande avec Cursor sur la meme machine

1. Backend Orchestrateur joignable (Docker `backend` expose `localhost:8000`, ou fichier `CATALOG_BACKEND=file`).
2. Depuis **`mcp-server/`** : installer les deps et le paquet en editable avec **`pip install -e .`**
3. Lancer :

```powershell
cd mcp-server
pip install -e .
$env:ORCHESTRATOR_API_BASE='http://127.0.0.1:8000'
python -m orchestrateur_mcp
```

Exemple **`mcp.json`** (fragment ; chemins adaptes a votre machine Windows) :

```json
{
  "mcpServers": {
    "orchestrateur": {
      "command": "python",
      "args": ["-m", "orchestrateur_mcp"],
      "cwd": "C:/Users/Vous/Documents/Projets/orchestrateur/mcp-server",
      "env": {
        "ORCHESTRATOR_API_BASE": "http://127.0.0.1:8000",
        "LOGLEVEL": "INFO"
      }
    }
  }
}
```

Astuce : utilisez **`127.0.0.1`**, pas **`localhost`**, si vous voyez une resolution IPv6 incompatible avec Uvicorn cote backend.

## Travailler sur le MCP **sans rebuild Docker** a repetition

Les images Dockerfile sont optimisees ainsi :

1. `requirements-container.txt` est installe **avant** le `COPY` du code Python.
2. Ajouter/modifier **`orchestrateur_mcp/*.py`** invalide uniquement **la derniere** couche d’image (rapide si deps inchangées).

Pour iterer encore plus vite : surcharge Compose avec **`compose.dev-mcp.yml`** (**`--reload` + volume**) pour recharger les `.py` **sans aucun rebuild** tant que vous ne touchez pas aux dependances :

```bash
docker compose -f compose.yaml -f compose.dev-mcp.yml up mcp-server backend db ollama ...
```

Une seule fois, construire l’image (deps) :

```bash
docker compose build mcp-server
```

Puis iterations quotidiennes sur le code MCP avec uniquement **`docker compose ... up`** (override dev), sans `--build`.

## Outils MCP exposes au modele

| Outil MCP | Equivalent API |
|-----------|----------------|
| `orchestrateur_health` | `GET /health` |
| `orchestrateur_services_status` | `GET /services/status` |
| `list_catalog_agents` | `GET /definitions/agents` |
| `list_catalog_workflows` | `GET /definitions/workflows` |
| `run_catalog_workflow` | `POST /workflows/catalog/{workflow_id}` |
| `run_dev_team_benchmark` | `POST /workflows/dev-team-benchmark` |

Les reponses sont des chaines JSON (texte formate lisible dans le transcript).

## Depannage

- **`406` / Client must accept `text/event-stream`** : passer par **stdio**, ou verifier que `MCP_RELAX_ACCEPT_HEADERS` n’est pas a `false` sans adapter le client, ou corriger les en‑tetes `Accept` dans le client.
- **Outils MCP qui echouent en timeout** : augmenter `ORCHESTRATOR_HTTP_TIMEOUT_SECONDS`.
- **`Connection refused`** : `ORCHESTRATOR_API_BASE` incorrect pour le runtime (reseau Docker `backend:8000` vs machine hote `127.0.0.1:8000`).

## References

- [Model Context Protocol — specification](https://modelcontextprotocol.io/)
- [python-sdk — Building Servers](https://modelcontextprotocol.github.io/python-sdk/server/)
- Fichiers du projet : `mcp-server/orchestrateur_mcp/app.py`, `mcp-server/Dockerfile`, `compose.yaml`, `compose.dev-mcp.yml`
