# Modeles Ollama supportes

Cette page liste les modeles **≤ 4B** adaptes a un laptop **16 Go RAM** avec la stack Docker complete (MariaDB, backend, frontend, Ollama).

## Modele par defaut du projet

- **`qwen2.5-coder:1.5b`** — configure dans `.env.example` et utilise par `ollama-init` si `OLLAMA_DEFAULT_MODEL` n'est pas surcharge.

Convient surtout aux etapes **execute** (livrables, code) et aux workflows **`local-repo-audit`**. Les etapes **plan** / **verify** peuvent beneficier d'un modele generaliste leger en surcharge (voir ci-dessous).

## Catalogue recommande

| Tag Ollama | Parametres | Taille disque ~ (Q4) | Profil | Etapes pipeline suggerees |
|------------|------------|----------------------|--------|---------------------------|
| `qwen2.5-coder:1.5b` | 1,5B | ~1 Go | Code, scripts, audit technique | `execute` (defaut global) |
| `qwen2.5-coder:3b` | 3B | ~2 Go | Code plus exigeant | `execute` |
| `qwen2.5:1.5b` | 1,5B | ~1 Go | General, handoffs JSON | `plan`, `verify` |
| `qwen2.5:3b` | 3B | ~2 Go | General, meilleure qualite | toutes (modele unique) |
| `qwen2.5:0.5b` | 0,5B | ~0,4 Go | Plumbing / CI local uniquement | validation stack |
| `llama3.2:3b` | 3B | ~2 Go | General (surtout EN) | toutes |
| `gemma3:4b` | 4B | ~2,5 Go | Qualite max ≤ 4B | `plan`, `research` |
| `phi4-mini` | ~3,8B | ~2,3 Go | Raisonnement, decomposition | `plan` |
| `nemotron-mini:4b` | 4B | ~2,7 Go | Tools, function calling | `execute`, `verify` |
| `smollm2:1.7b` | 1,7B | ~1 Go | Reponses rapides, taches simples | `research` (brouillon) |

## Variables d'environnement

Le backend resout un modele par etape du pipeline (`plan`, `research`, `execute`, `verify`) :

| Variable | Etape |
|----------|-------|
| `OLLAMA_DEFAULT_MODEL` | Repli pour toutes les etapes |
| `OLLAMA_MODEL_PLAN` | `plan` |
| `OLLAMA_MODEL_RESEARCH` | `research` |
| `OLLAMA_MODEL_EXECUTE` | `execute` |
| `OLLAMA_MODEL_VERIFY` | `verify` |

Alias legacy encore acceptes : `OLLAMA_MODEL_PLANNER`, `OLLAMA_MODEL_RESEARCHER`, `OLLAMA_MODEL_EXECUTOR`, `OLLAMA_MODEL_VERIFIER`.

Alternative : persistance via `PUT /v1/runtime/ollama/settings` (`default_model` + `runner_models`).

## Profils machine

### Usage quotidien (16 Go) — profil actuel

- `OLLAMA_DEFAULT_MODEL=qwen2.5-coder:1.5b`
- `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_LOADED_MODELS=1` (deja dans `compose.yaml`)
- Contexte conseille : 4k–8k tokens

### Validation plumbing uniquement

- `OLLAMA_DEFAULT_MODEL=qwen2.5:0.5b`
- Objectif : demarrage stack, handoffs, appels Ollama — pas la qualite des livrables

### Montee en qualite (RAM juste)

```env
OLLAMA_DEFAULT_MODEL=qwen2.5-coder:1.5b
OLLAMA_MODEL_PLAN=qwen2.5:1.5b
OLLAMA_MODEL_VERIFY=qwen2.5:1.5b
```

Un seul modele reste charge a la fois ; Ollama recharge au changement d'etape si les tags different.

## Commandes

```bash
ollama pull qwen2.5-coder:1.5b
ollama pull qwen2.5:1.5b
ollama list
```

Voir aussi [`runtime.md`](runtime.md) et [`agents.md`](agents.md).
