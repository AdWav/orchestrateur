# 03 — Évaluation (énoncé)

Répondez sans consulter [03-evaluation-corrige.md](./03-evaluation-corrige.md).  
Durée indicative : 45 minutes (QCM 20 min + questions libres 25 min).

---

## Partie A — QCM (une seule bonne réponse par question)

### A1. Définition

Un **agent**, au sens de ce cours, c'est principalement :

- a) Un modèle de langage avec un nom de fichier `.json`  
- b) Un système qui poursuit un objectif, raisonne en étapes et peut appeler des outils dans un cadre explicite  
- c) N'importe quel chatbot accessible dans un navigateur  
- d) Un workflow complet avec au moins quatre étapes  

### A2. Distinction

Laquelle est **fausse** ?

- a) Un agent catalogue a une mission, des inputs et des outputs  
- b) L'onglet Parcours exécute l'orchestrateur multi-agents du benchmark dev  
- c) Un garde-fou doit être vérifiable, pas seulement « sois gentil »  
- d) Un handoff transporte objectif, contraintes et artefacts  

### A3. Fiche agent

Le champ `outputs` sert surtout à :

- a) Lister les modèles Ollama autorisés  
- b) Nommer les livrables attendus, vérifiables par l'étape suivante ou un humain  
- c) Décrire l'historique de conversation  
- d) Remplacer les `guardrails`  

### A4. Runner

`runner_role` vide (`""`) signifie en général :

- a) L'agent ne peut pas être exécuté  
- b) Agent générique catalogue (`CatalogGenericAgent`) piloté par la fiche JSON  
- c) L'agent n'a pas besoin de mission  
- d) L'agent est réservé à l'administrateur  

### A5. Lecture seule

Quel agent catalogue illustre le mieux la **lecture seule** stricte ?

- a) `run_fix`  
- b) `doc_inventory`  
- c) `code_backend`  
- d) `doc_sync`  

### A6. Proposition vs application

`doc_sync` produit typiquement :

- a) Des patches proposés, pas une application automatique sans revue  
- b) Des suppressions massives de `docs/`  
- c) Un déploiement Docker  
- d) Uniquement du PlantUML  

### A7. Workflow

Le workflow `documentation-steward` enchaîne :

- a) `write_tests` → `code_backend` → `document`  
- b) `doc_inventory` → `doc_sync` → `doc_qa`  
- c) `plan` → `research` → `execute` → `verify`  
- d) Un seul agent sans étapes  

### A8. Sub-agent

Un **sub-agent** se distingue d'un simple **outil** parce que :

- a) Il est toujours plus rapide  
- b) Il délègue une sous-tâche avec objectif et périmètre propres, pas une action atomique unique  
- c) Il ne utilise jamais de modèle  
- d) Il remplace le workflow entier  

### A9. Chat vs orchestration

Dans ce projet, poser une question dans l'onglet **Parcours** :

- a) Lance `POST /workflows/dev-team-benchmark`  
- b) Appelle Ollama en profil live via le backend, sans orchestrateur multi-agents catalogue  
- c) Publie automatiquement un agent dans le Builder  
- d) Exécute `team-tdd` puis `team-classic`  

### A10. Garde-fous

Lequel est un **bon** garde-fou ?

- a) « Fais de ton mieux »  
- b) « Pas de fait sans chemin de fichier cité dans le dépôt »  
- c) « Sois créatif »  
- d) « Réponds longuement »  

### A11. Builder

Après publication d'un agent custom avec le slug `mon-agent`, l'id runtime est :

- a) `mon-agent`  
- b) `custom-mon-agent`  
- c) `builder-mon-agent`  
- d) `catalog/mon-agent`  

### A12. Handoff

Un handoff **mal défini** entre deux étapes provoque surtout :

- a) Une augmentation automatique de la context window  
- b) Perte d'artefacts, objectif flou ou re-travail inutile  
- c) Le passage automatique en lecture seule  
- d) La suppression du workspace  

### A13. MCP

Le serveur MCP de ce projet sert surtout à :

- a) Remplacer Ollama  
- b) Exposer des outils (équivalents API) à un client MCP distant  
- c) Stocker les traces SQLite  
- d) Compiler le frontend React  

### A14. Niveau atelier

Quel niveau correspond à « proposer des diffs Markdown sans les appliquer » ?

- a) Niveau 1 — Chat seul  
- b) Niveau 3 — Proposition d'écriture  
- c) Niveau 5 — Exécution shell  
- d) Niveau 7 — Sub-agent obligatoire  

### A15. QA documentation

L'agent `doc_qa` doit produire en priorité :

- a) Un nouveau schéma SQL  
- b) Un verdict explicite (ex. APPROVED / NEEDS_REVISION) et une checklist humaine  
- c) Un pull request mergé automatiquement  
- d) Un benchmark TDD vs classique  

---

## Partie B — Questions libres

Répondez en 5 à 15 lignes chacune (sauf B6).

### B1. Mission SMART

Rédigez une **mission** pour un agent « relecteur de PR documentation » : objectif clair, périmètre, critère de fin. Pas de JSON complet — texte seul.

### B2. Garde-fous shell

Vous concevez un agent avec accès **exécution shell** limité. Listez **trois** garde-fous concrets et vérifiables.

### B3. Handoff

Décrivez le contenu d'un handoff de `doc_inventory` vers `doc_sync` : quels champs / artefacts minimum ?

### B4. Refus de sub-agent

Donnez **un** cas métier où un sub-agent est **inutile** et un simple outil ou une seule étape suffit. Justifiez en 3 phrases.

### B5. Matrice

Pour l'agent `faq-reader` ([templates/agent-exemple-minimal.json](./templates/agent-exemple-minimal.json)), remplissez la [matrice d'autorisations](./templates/matrice-autorisations.md) (tableau complet).

### B6. Critique de fiche

Voici une mission faible :

> « Aide l'utilisateur avec son projet de A à Z. »

Réécrivez-la en mission **bornée** pour un agent niveau 2 (inventaire lecture seule documentation).

### B7. Choix de flux

Un utilisateur veut « comparer TDD et classique sur une feature API ». Quel **flux UI ou API** choisissez-vous (Parcours, Orchestrateur local, Builder, workflow catalogue) ? Pourquoi ?

---

## Auto-notation (optionnel)

| Partie | Score max | Votre score |
|--------|-----------|-------------|
| QCM (1 pt / question) | 15 | |
| B1–B4 (2 pts chacun) | 8 | |
| B5–B7 (3 pts chacun) | 9 | |
| **Total** | **32** | |

Seuil indicatif : ≥ 24/32 = acquis ; sinon relire [01-notion-agent.md](./01-notion-agent.md) et refaire les niveaux 0–2 de l'atelier.
