from __future__ import annotations

from core.contracts import UseCaseDefinition


USE_CASES: list[UseCaseDefinition] = [
    UseCaseDefinition(
        id="dev-team-benchmark",
        title="Dev Team Benchmark",
        description=(
            "Comparer deux equipes de developpement (TDD vs plan-code-test-document) "
            "sur la meme fonctionnalite, avec metriques de succes et de duree."
        ),
        primary_outcome="Rapport comparatif avec runs sequentiels team-tdd puis team-classic.",
        inputs=["objectif fonctionnel", "contraintes techniques", "criteres de succes"],
        deliverables=[
            "artefacts par etape",
            "verification_passed par equipe",
            "step_timings et total_duration_ms",
            "comparison (fastest, winners)",
        ],
    ),
]
