from __future__ import annotations

from core.contracts import UseCaseDefinition


V1_USE_CASES: list[UseCaseDefinition] = [
    UseCaseDefinition(
        id="specification-factory",
        title="Specification Factory",
        description=(
            "Transformer une demande encore floue en brief d'execution structure, "
            "verifiable et directement exploitable par une equipe d'agents."
        ),
        primary_outcome="Brief d'execution clair avec plan, hypotheses et criteres de succes.",
        inputs=["objectif", "contraintes", "contexte technique", "niveau de qualite attendu"],
        deliverables=["plan", "questions ouvertes", "ordre d'execution", "verdict de verification"],
    ),
    UseCaseDefinition(
        id="local-model-benchmark",
        title="Local Model Benchmark",
        description=(
            "Comparer plusieurs modeles locaux pour une tache cible et proposer un protocole "
            "de benchmark reproductible."
        ),
        primary_outcome="Plan de benchmark avec criteres, jeux d'essai et matrice de comparaison.",
        inputs=["tache cible", "materiel", "temps acceptable", "contraintes de confidentialite"],
        deliverables=["grille d'evaluation", "liste de modeles", "ordre de test", "risques"],
    ),
    UseCaseDefinition(
        id="dataset-readiness",
        title="Dataset Readiness",
        description=(
            "Preparer un corpus pour fine-tuning ou RAG en listant les controles de qualite, "
            "les transformations et les points de vigilance."
        ),
        primary_outcome="Runbook de preparation du corpus avant entrainement ou indexation.",
        inputs=["sources de donnees", "schema cible", "contraintes legales", "taille du corpus"],
        deliverables=["checklist qualite", "pipeline de preparation", "zones de risque", "prochaines actions"],
    ),
    UseCaseDefinition(
        id="operator-runbook",
        title="Operator Runbook",
        description=(
            "Produire un mode operatoire pas a pas pour executer localement une tache "
            "specialisee avec garde-fous, validations et plan de reprise."
        ),
        primary_outcome="Procedure operateur verifiee et auditable.",
        inputs=["objectif", "outils autorises", "seuils de securite", "definition du done"],
        deliverables=["procedure", "checks de securite", "preuves attendues", "conditions d'arret"],
    ),
    UseCaseDefinition(
        id="local-repo-audit",
        title="Local Repo Audit",
        description=(
            "Auditer un depot local en lecture seule pour produire une cartographie, "
            "des preuves traceables et des constats priorises."
        ),
        primary_outcome="Rapport d'audit de repo avec inventaire, preuves, constats et verdict.",
        inputs=["objectif", "chemin du depot", "axes d'analyse", "limites de lecture"],
        deliverables=["inventaire", "preuves", "constats", "verdict de verification"],
    ),
]
