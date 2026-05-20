# Runtime local et GPU

## Principe

Le projet separe explicitement:

- l'orchestration multi-agents
- le runtime d'inference
- la stack de fine-tuning

Cette separation est importante pour ne pas melanger:

- pilotage des agents
- serving de modeles
- jobs d'entrainement

## Runtime d'inference recommande

### `Ollama`

A privilegier si tu veux:

- une mise en route simple
- une API HTTP pratique
- un point d'entree unique pour plusieurs agents

Bon choix de depart pour:

- prototypage local
- usages mono-utilisateur
- orchestration multi-agents sur ce socle technique

Profil actuellement implemente:

- service `ollama` partage dans `compose`
- modele par defaut **`qwen2.5-coder:1.5b`**
- cible: laptop **16 Go RAM**, workflows orientes code / audit repo
- catalogue detaille : [`models.md`](models.md)

### `vLLM`

A privilegier si tu veux:

- plus de debit
- plus de parallelisme
- une machine Linux bien equipee en GPU

Bon choix pour:

- evaluation a plus grande echelle
- benchmark plus intensif
- plusieurs requetes concurrentes

### `llama.cpp`

A privilegier si tu veux:

- compatibilite large
- modeles quantises
- execution robuste sur materiel heterogene

Bon choix pour:

- petits agents auxiliaires
- machines modestes
- scenarios de compatibilite maximum

## Fine-tuning

Le fine-tuning ne doit pas etre heberge dans les memes conteneurs que les agents.

La stack recommandee reste:

- `PyTorch`
- `Transformers`
- `PEFT`
- `bitsandbytes`

## Recommandation pour ta machine

Deux profils sont a distinguer sur **16 Go RAM** :

### Profil usage quotidien (actuel)

- garder `Ollama`
- utiliser **`qwen2.5-coder:1.5b`** comme `OLLAMA_DEFAULT_MODEL`
- rester en `num_parallel=1` et `max_loaded_models=1`
- optionnel : `OLLAMA_MODEL_PLAN` / `OLLAMA_MODEL_VERIFY` en `qwen2.5:1.5b` pour des handoffs plus generiques

Ce profil convient pour:

- specifications et checklists
- audit de repo en lecture seule
- livrables avec extraits de code ou commandes

### Profil validation plumbing

Si tu veux uniquement valider la stack sans juger la qualite metier:

- utiliser `qwen2.5:0.5b`
- ne pas conclure sur la pertinence des sorties agents

Ce profil sert a verifier:

- le demarrage de la stack
- les appels reels au modele
- les handoffs inter-agents
- le comportement global de l'orchestrateur

### Profil machine principale

Avec `128 Go` de RAM, la RAM systeme n'est probablement pas le premier facteur limitant.

Les vraies questions sont:

- quel GPU exact
- quelle VRAM
- inference, benchmark, fine-tuning ou les trois
- Windows natif, WSL2 ou Linux

## Strategie conseillee

1. demarrer avec l'orchestrateur en conteneurs
2. brancher `Ollama` en premier si tu veux avancer vite
3. mesurer les limites reelles
4. migrer certains usages vers `vLLM` ou `llama.cpp` selon les resultats

## Changement de modele

Le changement de modele se fait sans modifier le code metier.

Par defaut, `compose.yaml` et `.env.example` utilisent:

- `OLLAMA_DEFAULT_MODEL=qwen2.5-coder:1.5b`

Tu pourras ensuite remplacer cette valeur par exemple par:

- un modele global plus grand (voir [`models.md`](models.md))
- un modele different par etape via `OLLAMA_MODEL_PLAN`, `OLLAMA_MODEL_RESEARCH`, `OLLAMA_MODEL_EXECUTE`, `OLLAMA_MODEL_VERIFY`
- ou via `PUT /v1/runtime/ollama/settings`

## Ce que fait deja le code

L'endpoint `POST /runtime/recommendation` produit une recommandation selon:

- systeme d'exploitation
- RAM
- VRAM
- objectif principal
- besoin de fine-tuning
- niveau de concurrence attendu

Les agents utilisent un client `Ollama` quand `MODEL_BACKEND=ollama`.

## Echantillonnage live et tokenisation BPE

En plus de l'inference des agents, le backend expose un **profil live** modifiable a la volee et un **essai streamé** (UI Echantillonnage).

Pour une **tokenisation BPE alignee sur le GGUF** du modele charge (visualisation « un token, une couleur » en mode BPE) :

- priorite future : `POST /api/tokenize` cote Ollama (quand disponible) ;
- aujourd'hui : `llama-cpp-python` en `vocab_only` sur le blob GGUF, avec `OLLAMA_MODELS_DIR` pointant vers le store Ollama (monte en lecture seule sur le conteneur `backend` dans `compose.yaml`).

Documentation : [`sampling-runtime.md`](sampling-runtime.md).
