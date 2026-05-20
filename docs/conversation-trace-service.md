# Service de traçage « potentiel d’action » (conversation → réponse)

Document de cadrage pour un **nouveau service** qui enregistre et expose le cheminement d’une interaction utilisateur, **du message entrant jusqu’à la réponse affichée**, sur le modèle des traces distribuées (proche d’OpenTelemetry : `trace` + `spans`).

## Objectif produit

Permettre une **timeline** ou un **graphe** dans l’UI : voir les états et transitions mesurables (durées, statuts, résumés d’entrée/sortie), sans prétendre exposer l’intégralité des mécanismes internes d’un LLM.

## Déroulé métier (phases 1 → 6)

Cartographie recommandée vers des **paliers de span** (un ou plusieurs spans par phase si besoin) :

| Phase | `stage` API | Rôle |
|------|-------------|------|
| 1 Entrée question | `user_input` | Message brut, métadonnées session |
| 2 Analyse intention | `intent` | Classification / objectif utilisateur |
| 3 Extraction contexte | `context` | Historique, RAG, outils, fichiers |
| 4 Raisonnement / plan | `reasoning` | Plan, décomposition, choix d’outils |
| 5 Génération | `generation` | Appels modèle, tokens, streaming |
| 6 Retour utilisateur | `response` | Assemblage final, formatage UI |

Les noms exacts sont figés dans le code (`TraceStage` dans `trace-service/`) pour garder une convention stable entre orchestrateur, agents et UI.

## Modèle de données (conceptuel)

- **Trace** : un identifiant (`trace_id`), horodatage de création, métadonnées libres (ex. `conversation_id`, `tenant`).
- **Span** : une unité de travail dans la trace :
  - `stage` (voir tableau ci-dessus)
  - `name` optionnel (ex. `planner`, `retrieve_docs`)
  - `started_at` / `ended_at` (UTC)
  - `status` : `pending` | `ok` | `error`
  - `summary_in` / `summary_out` : textes **courts**, éventuellement **redactés** (pas de secrets)
  - `attributes` : JSON arbitraire (IDs, compteurs, modèle utilisé, etc.)
  - `parent_span_id` : pour sous-étapes (arbre)

Évolution possible : exporter vers **OpenTelemetry** (OTLP) en parallèle du stockage maison, pour Grafana / Tempo.

## API HTTP (contrat MVP)

Préfixe suggéré : `/v1/traces`.

| Méthode | Chemin | Usage |
|---------|--------|--------|
| `POST` | `/v1/traces` | Ouvre une trace (retourne `trace_id`) |
| `POST` | `/v1/traces/{trace_id}/spans` | Démarre un span (retourne `span_id`) |
| `PATCH` | `/v1/traces/{trace_id}/spans/{span_id}` | Termine le span (`ended_at`, `status`, résumés) |
| `GET` | `/v1/traces/{trace_id}` | Lit la trace complète (ordonnée) pour la timeline UI |
| `GET` | `/v1/conversations/{conversation_id}/traces` | Liste les traces d'une conversation (sans spans ; `limit` query, défaut 100) |
| `PATCH` | `/v1/traces/{trace_id}` | Fusionne des clés dans `metadata` (ex. `user_text`, `assistant_text` pour l'historique UI) |
| `GET` | `/health` | Santé du service |

L’**orchestrateur** (ou chaque agent HTTP) appelle ce service **au fil de l’eau** : création de trace au début de la requête utilisateur, puis un span par phase au fur et à mesure.

## Intégration avec l’orchestrateur actuel

- **Processus unique** : le gateway / `catalog_workflow_executor` peut tenir un client HTTP vers `trace-service` (localhost ou réseau Docker).
- **Headers** : propager `X-Trace-Id` (et optionnellement `X-Parent-Span-Id`) des requêtes entrantes pour corréler avec les logs existants.
- **Frontend** (`frontend/` ou image Docker) : onglet **Parcours** — conversation (gauche) + timeline des spans (« potentiel d'action », droite). `conversation_id` stable dans `localStorage` ; rechargement via `GET /v1/conversations/{id}/traces` ; textes des tours dans `metadata.user_text` / `metadata.assistant_text`. Génération : `POST /v1/runtime/sampling/preview/stream` avec champ `history` (tours précédents) → Ollama `/api/chat` ; métadonnées de trace `context_mode`, `history_messages`, `history_chars`. Appels au trace-service (`VITE_TRACE_SERVICE_URL`, defaut `http://127.0.0.1:8090`). CORS : `TRACE_CORS_ORIGINS` cote trace-service si l'origine du navigateur change. **Compose** : le service `trace-service` est inclus dans `compose.yaml` (image `trace-service/Dockerfile`, port hôte **8090**).

Voir le squelette exécutable : répertoire [`trace-service/`](../trace-service/) (local `pip install -e .` ou conteneur).

## Stockage

- **MVP mémoire** : sans `TRACE_SQLITE_PATH`, le processus garde les traces en RAM (redémarrage = perte), suffisant pour prototyper la timeline.
- **SQLite + volume** : avec `TRACE_SQLITE_PATH` (fichier `.sqlite`), les traces et spans survivent aux redémarrages ; `compose.yaml` monte `trace_sqlite_data:/data` et définit `/data/traces.sqlite`.
- **Ensuite** : Postgres, rétention TTL, index sur `conversation_id`, export OTLP (voir ci-dessous).

## Sécurité et conformité

- Ne jamais stocker de secrets ni prompts complets en production sans politique ; préférer **hashes**, **longueurs**, **extraits courts**.
- Tracer seulement ce que la gouvernance accepte (RGPD, données métier).

## Références

- [Architecture actuelle](./architecture.md)
- OpenTelemetry : [Traces](https://opentelemetry.io/docs/concepts/signals/traces/)
