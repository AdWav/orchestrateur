# Equipes d'agents

## Equipes de developpement (benchmark)

Deux pipelines de **4 roles** sont disponibles pour comparer des methodologies sur la **meme fonctionnalite**. Les equipes s'executent **l'une apres l'autre** via `POST /workflows/dev-team-benchmark`.

### Team 1 — `team-tdd` (Test-Driven Development)

| Etape | Role | Mission |
|-------|------|---------|
| `write_tests` | Test Author | Creer les tests avant toute implementation |
| `code` | Developer | Coder le minimum pour faire passer les tests |
| `run_fix` | Runner | Executer la suite et corriger si necessaire |
| `document` | Tech Writer | Documenter le livrable et les preuves d'execution |

Handoffs : tests → code → execution/correctifs → documentation.

### Team 2 — `team-classic` (Plan → Code → Test → Document)

| Etape | Role | Mission |
|-------|------|---------|
| `schematic` | Planner | Planifier et schematiser (modules, flux) |
| `code` | Developer | Implementer selon le schema |
| `test_and_verify` | QA | Creer les tests puis executer et valider |
| `document` | Tech Writer | Documenter selon le verdict des tests |

Handoffs : schema → code → tests + execution → documentation.

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
