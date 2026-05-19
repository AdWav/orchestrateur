# Littérature : maintenir la capacité opérationnelle d'un modèle

Notes de recherche sur les cadres **formels** (équations, boucles de contrôle, bornes) qui traitent de « garder un modèle en régime de fonctionnement » — hors recommandations pratiques de tuning (voir [`EXPLAIN.md`](../EXPLAIN.md) pour l’UI Ollama).

## Fichiers

| Fichier | Périmètre |
|---------|-----------|
| [01-decodage-et-regulation.md](./01-decodage-et-regulation.md) | **Couche 1** — À chaque token : dégénérescence, nucleus, Mirostat, contrastive search, controlled decoding, unlikelihood, inférence active |
| [02-drift-temps-collapse-et-entropie.md](./02-drift-temps-collapse-et-entropie.md) | **Couche 2** — Dans le temps : model collapse, EWC, alignement KL, contrôle par entropie à l’inférence, liens avec l’orchestrateur |

## Lecture conseillée

1. Commencer par la **couche 1** si la question porte sur le **décodage live** (paramètres d’échantillonnage).
2. Passer à la **couche 2** si la question porte sur la **dérive du modèle**, les **boucles données↔modèle**, ou le **maintien des poids / de la distribution** sur plusieurs sessions.

## Limite commune

Aucun de ces travaux ne définit une **théorie unique** « capacité opérationnelle = f(…) » pour les LLM. Chaque papier formalise une **variable d’état** ou un **risque** différent (perplexité de sortie, erreur de test, distance de Wasserstein, KL au prior, entropie des logits, etc.).
