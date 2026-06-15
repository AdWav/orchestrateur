# 04 — Atelier progressif

Fil rouge : **maintenir la documentation du dépôt après un changement technique**.

Exemple d'objectif utilisateur pour tous les niveaux :

> « Nous avons ajouté le service `trace-service` (port 8090). Mettre à jour la documentation pour qu'elle reflète la stack réelle, sans inventer de ports ou de routes. »

---

## Vue d'ensemble des niveaux

| Niv. | Titre | Contrainte ajoutée | Livrable principal |
|------|-------|-------------------|-------------------|
| 0 | Fiche seule | Aucune exécution | JSON ou brouillon Builder |
| 1 | Chat | Dialogue direct, pas d'orchestration | Transcript + limites constatées |
| 2 | Lecture | Inventaire factuel, preuves | `documentation_inventory` |
| 3 | Proposition | Diffs / patches non appliqués | `proposed_doc_patches` |
| 4 | Écriture | Modifications matérialisées (périmètre) | Fichiers modifiés dans workspace |
| 5 | Exécution | Commandes / tests | Rapport exec + garde-fous respectés |
| 6 | Workflow | 2–3 agents + handoffs | Run workflow + artefacts chaînés |
| 7 | Délégation (option) | Sub-agent ou étape isolée | Design délégation + périmètre réduit |

Ne passez au niveau suivant que si les **critères de réussite** du niveau courant sont cochés.

---

## Niveau 0 — Fiche seule

### Objectif pédagogique

Comprendre le **contrat agent** sans toucher à l'infrastructure.

### Consigne

1. Copier [templates/agent-vide.json](./templates/agent-vide.json) vers `IA-xercice/reponses/niveau-0-mon-agent.json` (créez le dossier `reponses/` si besoin).
2. Remplir tous les champs pour un agent nommé **« Cartographe doc exercice »** aligné sur le fil rouge.
3. Remplir la [matrice d'autorisations](./templates/matrice-autorisations.md) (lecture seule prévue au niveau 2).

### Critères de réussite

- [ ] Checklist [02-squelette-et-exemples.md](./02-squelette-et-exemples.md) validée
- [ ] Au moins 2 `guardrails` testables
- [ ] `outputs` nommés (pas de formulations vagues)

### Référence solution

Comparer avec `catalog/agents/doc_inventory.json` — ne pas copier mot pour mot : adapter au fil rouge.

### Durée indicative

30 minutes.

---

## Niveau 1 — Chat

### Objectif pédagogique

Distinguer **chat** (modèle seul) et **agent structuré**.

### Prérequis

Stack Docker ou backend + Ollama local (voir [README](../README.md)).

### Consigne

1. Ouvrir l'UI → onglet **Parcours** (ou Échantillonnage pour un essai isolé).
2. Poser la question du fil rouge en une seule phrase.
3. Noter dans `IA-xercice/reponses/niveau-1-chat.md` :
   - la question exacte ;
   - 3 affirmations de la réponse ;
   - pour chaque affirmation : **vérifiée** / **non vérifiée** / **inventée** (avec chemin fichier si vérifiée).

### Critères de réussite

- [ ] Au moins une affirmation **inventée ou non vérifiable** identifiée (pédagogique : le chat n'a pas de garde-fous catalogue)
- [ ] Explication écrite (5 lignes) : pourquoi ce flux **ne remplace pas** un agent `doc_inventory`

### Point d'attention

Le Parcours n'exécute pas `documentation-steward`. Voir [parcours-utilisateur.md](../docs/parcours-utilisateur.md).

### Durée indicative

20 minutes.

---

## Niveau 2 — Lecture

### Objectif pédagogique

Agent **lecture seule** avec preuves citées.

### Consigne

1. Finaliser la fiche niveau 0 (ou utiliser `doc_inventory` comme modèle).
2. **Option A — Sans stack :** parcourir manuellement `docs/`, `README.md`, `compose.yaml` et produire un inventaire JSON/Markdown avec chemins cités.
3. **Option B — Avec stack :**  
   ```powershell
   curl -X POST http://localhost:8000/workflows/catalog/documentation-steward `
     -H "Content-Type: application/json" `
     -d '{"objective": "Ajout trace-service port 8090 — inventaire doc uniquement", "success_criteria": ["Inventaire avec chemins cites"]}'
   ```
   (Workflow complet = niveau 6 ; ici vous pouvez vous limiter à analyser la sortie de la première étape si disponible.)

4. Livrable : `documentation_inventory` (liste fichiers + écarts docs/réalité).

### Matrice d'autorisations

| Actions autorisées | R uniquement |
|--------------------|--------------|
| Interdit | W, D, exec |

### Critères de réussite

- [ ] Chaque service/port mentionné a un **chemin source**
- [ ] Aucune proposition de patch (réservé niveau 3)
- [ ] Matrice remplie et cohérente avec la fiche

### Durée indicative

45 minutes.

---

## Niveau 3 — Proposition d'écriture

### Objectif pédagogique

Séparer **proposer** et **appliquer**.

### Consigne

1. Partir de l'inventaire niveau 2.
2. Rédiger la fiche agent « proposeur » (voir exemple dans [02-squelette-et-exemples.md](./02-squelette-et-exemples.md)).
3. Produire `proposed_doc_patches` :
   - liste `files_to_touch` ;
   - pour chaque fichier : sections à modifier ou diff Markdown **sans** commit ni écriture disque (sauf si vous simulez sur copie locale hors prod).

### Critères de réussite

- [ ] Patches **petits** (pas de réécriture complète de `docs/architecture.md` sans justification)
- [ ] `inventory_echo` en tête : rappel synthétique pour la QA (comme `doc_sync`)
- [ ] Garde-fou « pas d'application automatique » explicite

### Référence catalogue

`catalog/agents/doc_sync.json`

### Durée indicative

45 minutes.

---

## Niveau 4 — Écriture matérialisée

### Objectif pédagogique

Écriture dans un **périmètre** contrôlé (workspace ou branche dédiée).

### Consigne

1. Définir le périmètre : ex. uniquement `docs/docker-stack.md` et `README.md`.
2. Mettre à jour la matrice : **W** autorisé sur ces chemins seulement.
3. Appliquer les patches niveau 3 **à la main** ou via workflow avec `materialize_workspace` si vous utilisez le benchmark dev (hors fil rouge doc pur).
4. Livrable : diff git ou liste des fichiers modifiés.

### Critères de réussite

- [ ] Aucun fichier hors périmètre modifié
- [ ] `git diff` (ou équivalent) reviewable
- [ ] Garde-fous documentés avant écriture

### Durée indicative

1 heure.

---

## Niveau 5 — Exécution

### Objectif pédagogique

Agent avec **exec** (tests, validation) sous contraintes.

### Consigne

1. Concevoir une fiche agent « vérifieur liens » ou réutiliser l'esprit de `doc_qa` + une commande autorisée (ex. linter markdown, `pytest` sur un sous-ensemble, **pas** de commandes destructrices).
2. Liste blanche de commandes dans les `guardrails`.
3. Exécuter **une** commande de vérification et joindre la sortie (tronquée si longue).

Exemple de garde-fous :

- « Autoriser uniquement `python -m pytest tests/test_xxx.py` depuis la racine du workspace. »
- « Interdire `rm`, `curl` vers l'extérieur, modification hors `workspaces/`. »

### Critères de réussite

- [ ] Commande dans la liste blanche
- [ ] Sortie interprétée dans un court rapport
- [ ] Échec documenté si la commande échoue (pas de contournement silencieux)

### Référence catalogue

`run_fix` (benchmark dev) — inspiration pour exec, pas pour copier la mission doc.

### Durée indicative

1 heure.

---

## Niveau 6 — Workflow

### Objectif pédagogique

Enchaîner agents avec **handoffs** explicites.

### Consigne

1. Dessiner (papier ou Mermaid) un workflow à **3 étapes** : Inventaire → Sync → QA (même logique que `documentation-steward`).
2. Pour chaque transition, remplir un tableau handoff :

| Élément | Étape 1→2 | Étape 2→3 |
|---------|-----------|-----------|
| Objectif | | |
| Artefacts | | |
| Contraintes | | |
| Critères succès | | |
| Actions suivantes | | |

3. **Option stack :** exécuter le workflow catalogue :

   ```json
   POST /workflows/catalog/documentation-steward
   {
     "objective": "Refleter trace-service (8090) dans la documentation",
     "success_criteria": [
       "Inventaire avec chemins",
       "Patches proposes",
       "Verdict QA explicite"
     ]
   }
   ```

4. Livrable : `IA-xercice/reponses/niveau-6-workflow.md` + captures ou extraits de sorties.

### Critères de réussite

- [ ] Les 3 fiches (ou références catalogue) sont cohérentes entre `inputs` / `outputs`
- [ ] Handoffs documentés (tableau complet)
- [ ] Verdict QA lisible (APPROVED / NEEDS_REVISION)

### Référence

[docs/agents.md](../docs/agents.md) § Documentation steward.

### Durée indicative

1 h 30.

---

## Niveau 7 — Délégation (option avancé)

### Objectif pédagogique

Décider quand un **sub-agent** (ou une étape dédiée) est justifié.

### Consigne

1. Scénario : le dépôt est volumineux ; l'inventaire doc doit scanner **uniquement** `docs/` pendant qu'un autre agent vérifie **uniquement** `compose.yaml`.
2. Rédiger :
   - **Option A** : un workflow à 2 agents parallèles puis fusion (conceptuel — la plateforme actuelle enchaîne surtout en séquentiel : justifier le choix séquentiel si besoin) ;
   - **Option B** : une étape « sub-agent » avec mission et périmètre **plus petits** que l'agent parent.
3. Répondre par écrit :
   - Pourquoi ce n'est **pas** un simple outil `read_file` ?
   - Quel risque si le périmètre du sub-agent n'est pas borné ?

### Critères de réussite

- [ ] Deux missions distinctes, deux périmètres disjoints
- [ ] Handoff de fusion défini (qui agrège les inventaires ?)
- [ ] Argumentation sub-agent vs outil (≥ 5 lignes)

### Référence conceptuelle

[LEXICAL.md](../LEXICAL.md) § Subagent.  
Pour déclenchement externe : [docs/mcp.md](../docs/mcp.md) (outils MCP ≠ sub-agent, mais peuvent lancer des workflows).

### Durée indicative

1 heure.

---

## Dossier de rendu suggéré

```
IA-xercice/reponses/
  niveau-0-mon-agent.json
  niveau-1-chat.md
  niveau-2-inventaire.md
  niveau-3-patches.md
  niveau-4-diff/
  niveau-5-exec-log.txt
  niveau-6-workflow.md
  niveau-7-delegation.md
```

Créez `reponses/.gitkeep` si vous versionnez les travaux — les réponses restent **locales** par défaut (non commitées sauf choix formateur).

---

## Synthèse compétences

| Compétence | Niveaux concernés |
|------------|-------------------|
| Rédiger une fiche agent | 0, 2, 3, 5 |
| Matrice d'autorisations | 2–5 |
| Distinguer chat / agent / workflow | 1, 6 |
| Handoff | 3, 6, 7 |
| Sub-agent (concept) | 7 |

---

## Aller plus loin

- Publier votre fiche via le **Builder** : [guide-builder-utilisation.md](../docs/guide-builder-utilisation.md)
- Comparer deux méthodologies dev : benchmark `dev-team-benchmark`
- Enrichir le lexique : proposer une entrée dans [LEXICAL.md](../LEXICAL.md)
