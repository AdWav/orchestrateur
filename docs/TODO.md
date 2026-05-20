# TODO

## Liste de tâches à mettre en place pour le projet IA

### 1.1. Mettre en place une documentation complète

→ Lexique
→ Qu'est ce qu'un model ?
→ Quels limites pour "cadrer" un model ?
→ Quantité de paramètre LLM/SLM
→ Agentic IA ?
→ Workflow critères

### 1.2. Evaluer la nénessité de mettre en place une BD (json ?)

→ Objectif : avoir une BD pour génèrer à la volée des agents / les stocker, etc...
→ Utilité : avoir une trace de chaque rôle/mission


- Température : Contrôle le niveau de hasard.  Une valeur basse rend le texte plus déterministe et factuel, une valeur élevée augmente la créativité et le risque d'erreur.
- Top-k : Limite le choix du prochain token aux k tokens les plus probables.  Restreint le vocabulaire à un ensemble fixe.
- Top-p (Nucleus Sampling) : Sélectionne dynamiquement les tokens dont la probabilité cumulée atteint un seuil p.  Plus adaptatif que Top-k.
- Mirostat : Contrôle la perplexité (stabilité) du texte généré.  Mirostat=1 ou 2 ajuste dynamiquement la température pour maintenir un niveau de surprise constant.
- Mirostat Eta : Taux d'apprentissage pour l'ajustement de la température dans Mirostat (valeur typique : 0.1). 
- Mirostat Tau : Niveau cible de perplexité pour Mirostat (valeur typique : 5.0). 
- Presence Penalty : Augmente la probabilité d'utiliser des tokens nouveaux, réduisant la répétition de sujets. 
- Frequency Penalty : Diminue la probabilité d'utiliser des tokens fréquemment utilisés, réduisant la répétition de mots. 
- Repeat Penalty : Pénalise directement la répétition de tokens ou de séquences. 
- Repeat Last N : Nombre de tokens précédents à considérer pour appliquer la pénalité de répétition. 
- Logit Bias : Ajuste manuellement la probabilité d'apparition de tokens spécifiques (positif pour favoriser, négatif pour pénaliser). 
- Stop Sequences : Définit une ou plusieurs séquences de tokens qui arrêtent la génération de texte. 
- Max Tokens : Limite le nombre maximum de tokens générés. 
- Min P : Seuil de probabilité minimale pour qu'un token soit considéré (par exemple, min_p=0.05 inclut uniquement les tokens avec au moins 5% de probabilité). 

→ je veux mettre en place un service où on peut (extemporannement) modifier les parametre de décodage d'un modèle
→ **fait** : profil live + `PUT /v1/runtime/sampling/settings/live` + UI (voir [`sampling-runtime.md`](./sampling-runtime.md))
→ Je veux suivre le cheminement complet d'une question utilisateur jusqu'a la reponse (trace par phases : intention, contexte, raisonnement, generation, etc.)
→ **amorce** : service HTTP dedie + doc [`conversation-trace-service.md`](./conversation-trace-service.md) (`trace-service/`, port local 8090) ; integration backend / UI et persistance a brancher
→ **partiel** : stats fin de stream (prompt/output, tok/s) + calque tokens Flux/BPE en UI ; doc comptabilisation détaillée : à enrichir
→ 