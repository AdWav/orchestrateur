# Equipes d'agents

## Equipes de developpement (benchmark)

Deux pipelines de **4 roles** sont disponibles pour comparer des methodologies sur la **meme fonctionnalite**. Les equipes s'executent **l'une apres l'autre** via `POST /workflows/dev-team-benchmark`.

### Team 1 — `team-tdd` (Test-Driven Development)

Enchainement tel que `catalog/workflows/team-tdd.json` (ids d'etape du workflow) :

| Etape (id) | Agent catalogue | Mission |
|------------|-----------------|---------|
| `tests-first` | `write_tests` | Tests et criteres d'acceptation avant implementation |
| `backend` | `code_backend` | API et logique serveur |
| `frontend` | `code_frontend` | Interface et app au backend |
| `e2e` | `integration` | Parcours complet UI + API |
| `run-fix` | `run_fix` | Executer les suites et corriger |
| `document` | `document` | Documentation du livrable et des preuves |

### Team 2 — `team-classic` (Plan → contrat → code → tests → livraison)

Enchainement tel que `catalog/workflows/team-classic.json` :

| Etape (id) | Agent catalogue | Mission |
|------------|-----------------|---------|
| `schematic` | `schematic` | Schema et plan d'implementation |
| `contract` | `api_contract` | Contrat d'API (routes, schemas) |
| `database` | `database` | Schema et migrations |
| `backend` | `code_backend` | Serveur selon le contrat |
| `frontend` | `code_frontend` | UI selon le contrat |
| `test` | `test_and_verify` | Tests automatises par couche |
| `e2e` | `integration` | E2E sur parcours reel |
| `run-fix` | `run_fix` | Correctifs jusqu'au passage des suites |
| `review` | `review` | Revue de code |
| `security` | `security` | Revue risques securite |
| `document` | `document` | Documentation du livrable final |

Les dependances exactes entre etapes sont dans `depends_on` de chaque fichier `catalog/workflows/*.json`.

### Comparaison

Le rapport `DevTeamBenchmarkReport` contient :

- `runs` : un `WorkflowRun` par equipe (`team_id`, `outputs`, `step_timings`, `total_duration_ms`, `verification_passed`)
- `comparison` : `success_by_team`, `duration_ms_by_team`, `fastest_team_id`, `winner_by_success`, `notes`

Ordre par defaut : `team-tdd` puis `team-classic` (surcharge via `team_order` dans le payload).

Exemple :

```json
{
  "objective": "Ajouter un endpoint POST /items avec validation",
  "team_order": ["team-tdd", "team-classic"]
}
```

API : `GET /teams`, `GET /team?team_id=team-tdd`, `POST /workflows/dev-team-benchmark`.

Cas d'usage : `dev-team-benchmark`.

## Equipe legacy — `specification-team`

L'equipe initiale reste disponible pour specification, audit repo et cas d'usage historiques.

| Etape | Role |
|-------|------|
| `plan` | Planner |
| `research` | Researcher |
| `execute` | Executor |
| `verify` | Verifier |

`GET /team` sans parametre renvoie cette equipe.

## Workflow catalogue — Documentation steward (`documentation-steward`)

Pipeline en **trois etapes** (fichiers `catalog/workflows/documentation-steward.json` et agents `doc_inventory`, `doc_sync`, `doc_qa`). Chaque agent utilise le runner catalogue generique (`CatalogGenericAgent`) : la fiche JSON pilote mission, capacites et garde-fous.

| Etape (id) | Agent catalogue | Role |
|------------|-----------------|------|
| `doc_inventory` | `doc_inventory` | Inventaire factuel du depot (services, `docs/`, Docker, API) avec sources citees |
| `doc_sync` | `doc_sync` | Propositions de mises a jour Markdown minimales + rappel synthetique pour la QA |
| `doc_qa` | `doc_qa` | Verification de coherence et verdict (approbation ou revisions) |

**API** : `POST /workflows/catalog/documentation-steward` avec un corps `CatalogWorkflowRunRequest` / objectif decrivant le changement a refleter (nouveau service, retrait, refonte, etc.).

**Handoff** : entre etapes, les resumes des sorties precedentes sont ajoutes au prompt via les entrees memoire `catalog_step_output_<step_id>` (voir `core/catalog_runtime.py` et `CatalogGenericAgent`).

## Equipe catalogue — Visualisation code (`team-code-viz`)

Pipeline en **six etapes** pour lire un depot (multi-langages) et produire **UML PlantUML**, **draw.io XML** et **flux Mermaid** a partir d'un modele structurel unique.

| Etape (id) | Agent catalogue | Runner | Livrable |
|------------|-----------------|--------|----------|
| `code_scan` | `viz_code_scan` | `diagram_code_scan` | inventaire + `structure_seed` |
| `structure` | `viz_structure` | `diagram_structure` | `code_structure_model` |
| `uml` | `viz_uml` | `diagram_uml` | `@startuml` … `@enduml` |
| `drawio` | `viz_drawio` | `diagram_drawio` | `drawio_xml` (mxGraphModel) |
| `mermaid` | `viz_mermaid` | `diagram_mermaid` | `mermaid_flow` (flowchart) |
| `qa` | `viz_qa` | `diagram_qa` | verdict + bundle final |

**Inspirations** : analyse statique + abstraction (CodeBoarding), generation Mermaid depuis repo (Swark, RepoArchitectAgent), multi-formats (diagram-architect).

**API** : `POST /workflows/catalog/team-code-viz`

Exemple de payload (racine du projet a analyser) :

```json
{
  "objective": "Diagrammer l'architecture de mon application",
  "use_case_id": "code-visualization",
  "context": {
    "code_visualization": {
      "repo_target": { "root_path": "/chemin/vers/projet" },
      "audit_scope": {
        "analysis_axes": ["architecture"],
        "read_limits": { "max_files": 40, "max_bytes_per_file": 12000, "max_matches": 40 }
      }
    }
  },
  "success_criteria": ["PlantUML genere", "draw.io XML genere", "Mermaid flowchart genere"]
}
```

Modules runtime : `core/code_structure_extractor.py`, `core/diagram_emitters.py`, `core/roles_diagram.py`.

## Contrat de handoff

Chaque handoff doit transporter :

- l'objectif de travail
- les contraintes explicites
- les criteres de succes
- les artefacts produits
- les actions suivantes

## Garde-fous actuels

- une seule iteration de workflow par run
- aucun elargissement implicite du scope
- tous les handoffs sont traces
- le workflow s'arrete si une sortie attendue manque
- le workflow `local-repo-audit` reste strictement en lecture seule
- chaque constat d'audit doit rester soutenu par une preuve

## Cas d'usage couverts

1. `specification-factory`
2. `local-model-benchmark`
3. `dataset-readiness`
4. `operator-runbook`
5. `dev-team-benchmark`
6. `local-repo-audit`
7. `documentation-steward` (workflow catalogue — maintenance documentaire)
8. `code-visualization` (workflow catalogue — UML, draw.io, Mermaid)
