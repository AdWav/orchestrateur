# orchestrateur-trace-service

Service FastAPI minimal pour enregistrer une **trace** (parcours utilisateur → réponse) découpée en **spans** alignés sur les phases métier (entrée, intention, contexte, raisonnement, génération, retour).

Variables utiles :

- **`TRACE_CORS_ORIGINS`** : liste separee par des virgules (defaut : `localhost` / `127.0.0.1` ports **3000** et **5173**) pour les requetes du navigateur vers ce service.
- **`TRACE_SQLITE_PATH`** : si défini (ex. `./data/traces.sqlite` en local ou `/data/traces.sqlite` dans Docker), les traces sont persistées dans un fichier **SQLite** (mode WAL). Sans cette variable, stockage **en mémoire** (redémarrage = perte).

## Démarrage local

```bash
cd trace-service
pip install -e .
orchestrateur-trace
```

Par défaut : `http://127.0.0.1:8090` — documentation OpenAPI : `/docs`.

Variables d’écoute (utile en conteneur) :

- **`TRACE_BIND_HOST`** : hôte d’écoute Uvicorn (défaut `127.0.0.1` ; utiliser `0.0.0.0` dans Docker).
- **`TRACE_PORT`** : port (défaut `8090`).

## Docker (stack projet)

À la racine du dépôt :

```bash
docker compose up --build
```

Le service **`trace-service`** est construit depuis `trace-service/Dockerfile`, publié sur le port hôte **8090**. Le frontend est compilé avec `VITE_TRACE_SERVICE_URL=http://127.0.0.1:8090` : le navigateur appelle l’API trace sur la machine hôte (mapping du port du conteneur).

## Documentation projet

[`docs/conversation-trace-service.md`](../docs/conversation-trace-service.md)

## Exemple rapide

```bash
# Créer une trace
curl -s -X POST http://127.0.0.1:8090/v1/traces -H "Content-Type: application/json" \
  -d '{"conversation_id":"conv-1","metadata":{"source":"demo"}}'

# Démarr puis clôturer un span (remplacer TRACE_ID et utiliser le span_id retourné)
curl -s -X POST http://127.0.0.1:8090/v1/traces/TRACE_ID/spans -H "Content-Type: application/json" \
  -d '{"stage":"intent","name":"classify","summary_in":"message utilisateur"}'

curl -s -X PATCH http://127.0.0.1:8090/v1/traces/TRACE_ID/spans/SPAN_ID -H "Content-Type: application/json" \
  -d '{"status":"ok","summary_out":"intention: question_technique"}'

curl -s http://127.0.0.1:8090/v1/traces/TRACE_ID

# Historique par conversation
curl -s "http://127.0.0.1:8090/v1/conversations/CONV_ID/traces?limit=50"

# Enregistrer les textes du tour (fusion metadata)
curl -s -X PATCH http://127.0.0.1:8090/v1/traces/TRACE_ID -H "Content-Type: application/json" \
  -d '{"metadata":{"user_text":"Bonjour","assistant_text":"Salut"}}'
```

## Stockage

- **Par défaut** : mémoire (redémarrage du processus = perte des traces).
- **Persistant** : définir `TRACE_SQLITE_PATH` vers un chemin de fichier accessible en écriture. Sous `docker compose`, le service monte le volume nommé `trace_sqlite_data` sur `/data` et utilise `/data/traces.sqlite` (voir `compose.yaml`).
