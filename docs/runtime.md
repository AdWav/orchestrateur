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
- modele par defaut `qwen2.5:0.5b`
- cible: validation fonctionnelle sur machine legere

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

Deux profils sont a distinguer:

### Profil validation

Si tu veux juste valider le fonctionnement sur un laptop de `16 Go` de RAM:

- garder `Ollama`
- utiliser `qwen2.5:0.5b`
- rester en `num_parallel=1`
- ne pas juger la qualite metier sur ce modele

Ce profil sert uniquement a verifier:

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

Par defaut, `compose.yaml` utilise:

- `OLLAMA_DEFAULT_MODEL=qwen2.5:0.5b`

Tu pourras ensuite remplacer cette valeur par exemple par:

- un modele global plus grand
- un modele different par role via `OLLAMA_MODEL_PLANNER`, `OLLAMA_MODEL_RESEARCHER`, `OLLAMA_MODEL_EXECUTOR`, `OLLAMA_MODEL_VERIFIER`

Une valeur de reference est egalement fournie dans `.env.example`.

## Ce que fait deja le code

L'endpoint `POST /runtime/recommendation` produit une recommandation selon:

- systeme d'exploitation
- RAM
- VRAM
- objectif principal
- besoin de fine-tuning
- niveau de concurrence attendu

Les agents utilisent maintenant un vrai client `Ollama` quand `MODEL_BACKEND=ollama`.
