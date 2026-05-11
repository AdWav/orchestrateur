# Equipe d'agents

## Equipe actuelle

L'equipe initiale est volontairement limitee a quatre agents ultra specialises.

Depuis la V2 `local-repo-audit`, ces roles gardent la meme topologie mais produisent des artefacts plus structures et relies a des preuves.

## `Planner`

Mission:

- transformer l'objectif utilisateur en plan de travail
- identifier les hypotheses
- preparer les handoffs

Entrees attendues:

- objectif
- contraintes
- criteres de succes
- contexte

Sorties:

- `plan_steps`
- `assumptions`
- `handoff_brief`
- `audit_scope`
- `search_plan`

## `Researcher`

Mission:

- convertir le contexte en hypotheses testables
- signaler les manques d'information
- preparer les preuves attendues
- mapper le depot en lecture seule pour l'audit de repo

Entrees attendues:

- brief du `Planner`
- contexte utilisateur
- cas d'usage

Sorties:

- `knowledge_gaps`
- `evidence_plan`
- `decision_inputs`
- `repo_inventory`
- `evidence_refs`
- `coverage_map`

## `Executor`

Mission:

- produire le livrable exploitable
- structurer une checklist d'execution
- preparer les notes operateur
- transformer les preuves repo en constats priorises

Entrees attendues:

- brief du `Planner`
- resultats du `Researcher`
- criteres de succes

Sorties:

- `execution_brief`
- `checklist`
- `operator_notes`
- `findings`
- `repo_summary`
- `recommended_actions`

## `Verifier`

Mission:

- controler la conformite du livrable
- verifier les garde-fous
- emettre un verdict final
- refuser un audit sans preuve ou hors du scope

Entrees attendues:

- sorties des trois autres roles
- criteres de succes
- stop conditions

Sorties:

- `verification_report`
- `approval`
- `missing_items`
- `validation_report`

## Contrat de handoff

Chaque handoff doit transporter:

- l'objectif de travail
- les contraintes explicites
- les criteres de succes
- les artefacts produits
- les actions suivantes

## Garde-fous actuels

- une seule iteration de workflow
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
5. `local-repo-audit`
