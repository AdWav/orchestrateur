# Equipe d'agents

## Equipe V1

L'equipe initiale est volontairement limitee a quatre agents ultra specialises.

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

## `Researcher`

Mission:

- convertir le contexte en hypotheses testables
- signaler les manques d'information
- preparer les preuves attendues

Entrees attendues:

- brief du `Planner`
- contexte utilisateur
- cas d'usage

Sorties:

- `knowledge_gaps`
- `evidence_plan`
- `decision_inputs`

## `Executor`

Mission:

- produire le livrable exploitable
- structurer une checklist d'execution
- preparer les notes operateur

Entrees attendues:

- brief du `Planner`
- resultats du `Researcher`
- criteres de succes

Sorties:

- `execution_brief`
- `checklist`
- `operator_notes`

## `Verifier`

Mission:

- controler la conformite du livrable
- verifier les garde-fous
- emettre un verdict final

Entrees attendues:

- sorties des trois autres roles
- criteres de succes
- stop conditions

Sorties:

- `verification_report`
- `approval`
- `missing_items`

## Contrat de handoff

Chaque handoff doit transporter:

- l'objectif de travail
- les contraintes explicites
- les criteres de succes
- les artefacts produits
- les actions suivantes

## Garde-fous V1

- une seule iteration de workflow
- aucun elargissement implicite du scope
- tous les handoffs sont traces
- le workflow s'arrete si une sortie attendue manque

## Cas d'usage couverts

1. `specification-factory`
2. `local-model-benchmark`
3. `dataset-readiness`
4. `operator-runbook`
