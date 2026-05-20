# Échantillonnage live — prévisualisation, streaming et tokenisation

Guide de l’écran **Échantillonnage** (onglet réglages / modal) : essai du profil live, génération en flux, calque de tokens et tokenisation BPE alignée sur le modèle.

Voir aussi : [`EXPLAIN.md`](./EXPLAIN.md) (rôle des réglages d’échantillonnage), [`cours-echantillonnage.md`](./cours-echantillonnage.md) (théorie ↔ UI).

---

## 1. Deux profils de paramètres

| Profil | Modifiable via API | Usage |
|--------|-------------------|--------|
| **Orchestration** | Non (lecture seule dans l’UI) | Workflows, agents, benchmark |
| **Live** | Oui (`PUT /v1/runtime/sampling/settings/live`) | Essai immédiat, réglages expérimentaux |

Les valeurs live sont converties en options Ollama (`to_ollama_options`) avant chaque appel `/api/generate`.

---

## 2. Essai du profil live (UI)

1. Onglet **Échantillonnage** → section **Essayer le profil live**
2. Saisir un prompt d’essai → lancer la génération

Comportement :

- **Streaming** : le texte s’affiche au fil de l’eau (NDJSON).
- **Statistiques** en fin de run : tokens prompt / générés, débit approximatif (`eval_count`, `eval_duration` Ollama).

Prérequis : `MODEL_BACKEND=ollama`, modèle présent dans `ollama list`.

---

## 3. Calque de tokens (UI)

Visible dès que la zone de prévisualisation contient du texte.

| Contrôle | Description |
|----------|-------------|
| **Tokens** (toggle) | Active ou désactive le surlignage |
| **Flux** | Un fragment = un morceau renvoyé par le stream HTTP Ollama (souvent un sous-mot, pas un token BPE exact) |
| **BPE** | Un fragment = un token du vocabulaire du modèle (voir § 4) |

Chaque fragment a une **couleur cyclique** (12 teintes) ; survol → index et, en mode BPE, **id** du token.

---

## 4. Tokenisation BPE stricte (modèle)

### Objectif

Afficher la découpe **réelle** du texte selon le tokenizer embarqué dans le **GGUF** chargé par Ollama (ex. SentencePiece / BPE Qwen), et non les seuls morceaux du flux réseau.

### Chaîne technique (backend)

```
POST /v1/runtime/sampling/tokenize
        │
        ├─► Ollama ≥ version avec /api/tokenize  → priorité (futur)
        │
        └─► llama-cpp-python (vocab_only) sur le GGUF Ollama
                └─ résolution du blob via GET /api/show (FROM …)
```

| Route | Rôle |
|-------|------|
| `GET /v1/runtime/sampling/tokenize/capabilities` | `source` : `ollama`, `llama_cpp` ou `unavailable` |
| `POST /v1/runtime/sampling/tokenize` | Corps : `{ "text": "…", "model": "…" }` → `{ tokens: [{ id, text }, …], token_count, source }` |

Implémentation : `backend/app/services/ollama_tokenize.py`.

### Docker Compose

Le service `backend` monte le volume Ollama en lecture seule :

```yaml
environment:
  OLLAMA_MODELS_DIR: /ollama-models
volumes:
  - ollama_data:/ollama-models:ro
```

Sans ce montage (ou sans `/api/tokenize` côté Ollama), le mode **BPE** de l’UI reste indisponible.

### Dev local (hors Docker)

1. Installer le projet : `pip install -e ".[dev]"` (inclut `llama-cpp-python`).
2. Pointer vers les blobs Ollama sur la machine hôte, par exemple :
   - Windows : `OLLAMA_MODELS_DIR=%USERPROFILE%\.ollama`
   - Linux : `OLLAMA_MODELS_DIR=~/.ollama`

Le chemin doit contenir `models/blobs/` (structure standard Ollama).

### Exemple API

```bash
curl -s http://localhost:8000/v1/runtime/sampling/tokenize/capabilities

curl -s -X POST http://localhost:8000/v1/runtime/sampling/tokenize \
  -H "Content-Type: application/json" \
  -d '{"text":"Le top-p est une technique."}'
```

Réponse typique (`source: llama_cpp`) : liste de morceaux avec `id` entier et `text` (souvent un espace en tête sur les sous-mots, conforme au tokenizer).

---

## 5. Streaming API (développeurs)

| Route | Type | Description |
|-------|------|-------------|
| `POST /v1/runtime/sampling/preview` | JSON | Réponse complète (bloquant) |
| `POST /v1/runtime/sampling/preview/stream` | `application/x-ndjson` | Événements ligne par ligne |

Événements stream :

```json
{"event":"token","content":"…"}
{"event":"done","model":"…","profile":"live","backend":"ollama:…","content":"…","stats":{…}}
```

Le client frontend consomme ce flux via `streamSamplingPreview()` (`frontend/src/lib/api.ts`).

---

## 6. Limites connues

| Sujet | Détail |
|-------|--------|
| Orchestration / benchmark | Génération toujours **non streamée** côté agents (`stream: false` dans `model_client.py`) |
| Ollama 0.23.x | Pas de `/api/tokenize` → repli **llama_cpp** sur le backend |
| Image backend | Nécessite `libgomp1` + compilation de `llama-cpp-python` (voir `backend/Dockerfile`) |
| Probabilites par token | Non exposées par Ollama dans l’API standard |
| Mode BPE pendant le stream | Re-tokenisation du texte accumulé (debounce ~280 ms), pas token-par-token en temps réel côté vocabulaire |

---

## 7. Fichiers utiles

| Fichier | Rôle |
|---------|------|
| `backend/app/controllers/sampling_controller.py` | Preview, stream, tokenize |
| `backend/app/services/ollama_ops.py` | Appels Ollama generate |
| `backend/app/services/ollama_tokenize.py` | BPE / détection capabilities |
| `frontend/src/components/PreviewTokenOutput.tsx` | Toggle Tokens, segment Flux/BPE |
| `frontend/src/components/SamplingSettingsModal.tsx` | Modal / panneau échantillonnage |
| `compose.yaml` | Volume `ollama_data` → backend |

---

*Dernière mise à jour : streaming preview, calque tokens, tokenisation BPE via llama.cpp.*
