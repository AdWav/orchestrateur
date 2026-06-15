# 03 — Évaluation (corrigé — formateur)

> Ne distribuer qu'après la passation ou en correction différée.

---

## Partie A — QCM

| # | Réponse | Justification courte |
|---|---------|----------------------|
| A1 | **b** | Définition alignée LEXICAL + cours 01 |
| A2 | **b** | Parcours = chat live + traces, pas benchmark multi-agents |
| A3 | **b** | Outputs = livrables nommés |
| A4 | **b** | `runner_role` vide → générique catalogue |
| A5 | **b** | `doc_inventory` : lecture seule, preuves citées |
| A6 | **a** | `doc_sync` : patches proposés, review humaine |
| A7 | **b** | Workflow documentation-steward |
| A8 | **b** | Sub-agent = sous-tâche déléguée, pas action atomique |
| A9 | **b** | Voir parcours-utilisateur.md flux A |
| A10 | **b** | Règle testable |
| A11 | **b** | Convention `custom-{slug}` |
| A12 | **b** | Handoff incomplet → re-travail / perte |
| A13 | **b** | docs/mcp.md |
| A14 | **b** | Niveau 3 atelier |
| A15 | **b** | Mission doc_qa |

---

## Partie B — Grilles de correction

### B1. Mission SMART (2 pts)

| Critère | 1 pt si… |
|---------|----------|
| Objectif mesurable | Verbe d'action + livrable (ex. liste d'écarts, commentaires sur fichiers `.md`) |
| Périmètre | Limité (PR doc seulement, pas tout le code) |
| Fin explicite | Critère de fin (ex. rapport structuré, N sections revues) |

**Exemple de réponse acceptable :**  
« Pour une PR donnée, comparer les fichiers `docs/` et le README touchés aux changements décrits dans la description de PR. Produire une liste d'écarts (liens cassés, service oublié, ton incohérent) avec chemin cité. S'arrêter après le rapport ; ne pas modifier les fichiers. »

### B2. Garde-fous shell (2 pts)

Attendu : **3 règles vérifiables**, par ex. :

- Périmètre répertoire (`workspaces/run-xxx/` uniquement)  
- Liste blanche de commandes (`pytest`, `git status` — pas `rm -rf`)  
- Timeout ou taille max de sortie  
- Interdiction réseau sortant  
- Escalade humaine avant toute écriture hors workspace  

**0,5 pt par garde-fou pertinent et testable** (max 2 pts pour 3+ items).

### B3. Handoff (2 pts)

Minimum attendu dans la réponse :

- Objectif / work item (changement doc à refléter)  
- Artefacts : `documentation_inventory`, `service_matrix`, `doc_file_candidates`  
- Contraintes / critères de succès  
- Pas d'invention : rappel que l'inventaire est la source pour `doc_sync`

Référence : [docs/agents.md](../docs/agents.md) § Contrat de handoff.

### B4. Refus sub-agent (2 pts)

Exemples acceptables :

- Lire un seul fichier README pour une FAQ → un agent ou chat suffit  
- Compter les lignes d'un fichier → outil `read`, pas sub-agent  
- Une seule transformation atomique  

Pénaliser si la justification confond outil et sub-agent.

### B5. Matrice faq-reader (3 pts)

| Colonne | Attendu |
|---------|---------|
| Périmètre | README racine (chemin explicite) |
| Actions | R seulement |
| Preuve | Citations section / extrait |
| Arrêt | Si info absente du README → le dire, ne pas extrapoler |

### B6. Réécriture mission (3 pts)

Doit contenir : action précise (inventorier), périmètre (`docs/`, README), livrable (liste chemins + écarts), interdiction d'écriture, citation obligatoire.

**Exemple :**  
« Produire un inventaire Markdown des fichiers `docs/*.md` et du README liés à [objectif]. Chaque entrée cite le chemin relatif. Signaler les écarts docs/arbo sans proposer de patch. Aucune modification de fichier. »

### B7. Choix de flux (3 pts)

**Réponse attendue :** Orchestrateur local → `POST /workflows/dev-team-benchmark` (ou MCP équivalent), **pas** Parcours.

| Points | Si… |
|--------|-----|
| 2 | Identifie benchmark / flux B |
| 1 | Explique que Parcours = chat seul, pas enchaînement team-tdd/classic |
| 0 | Propose uniquement Builder ou Parcours pour le benchmark |

---

## Barème récapitulatif

| Section | Points |
|---------|--------|
| A1–A15 | 15 |
| B1–B4 | 8 |
| B5–B7 | 9 |
| **Total** | **32** |

| Score | Niveau |
|-------|--------|
| 28–32 | Excellent — enchaîner atelier niveaux 5–7 |
| 24–27 | Acquis — atelier niveaux 3–6 |
| 18–23 | À consolider — refaire 01–02 et niveaux 0–2 |
| &lt; 18 | Reprise notion agent + squelette |
