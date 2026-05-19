from __future__ import annotations

from typing import Any

from core.contracts import AuditScope, RepoAuditRequest, RepoReadLimits, RepoTarget, WorkItem


DEMO_SCENARIOS = ("delivery-mission", "tech-due-diligence")


def _scenario_payload(
    scenario: str,
    company_name: str,
    client_name: str,
) -> dict[str, Any]:
    if scenario == "delivery-mission":
        return {
            "scenario": scenario,
            "company": {
                "name": company_name,
                "activity": "cabinet de conseil technique et delivery logiciel",
                "goal": "industrialiser un cadrage client rapide, lisible et auditable",
            },
            "client": {
                "name": client_name,
                "need": "obtenir un diagnostic rapide de son depot avant lancement de mission",
            },
            "mission": {
                "title": "Comite projet de pre-audit technique",
                "brief": (
                    f"{company_name} doit analyser le depot de {client_name}, preparer un plan de mission "
                    "et produire un go/no-go argumente pour la direction de delivery."
                ),
            },
            "role_projection": [
                {
                    "engine_role": "plan",
                    "business_role": "Directeur de mission",
                    "responsibility": "cadre la mission, fixe les priorites et les criteres de succes",
                },
                {
                    "engine_role": "research",
                    "business_role": "Analyste senior",
                    "responsibility": "collecte les signaux du depot, les risques et les zones d'incertitude",
                },
                {
                    "engine_role": "execute",
                    "business_role": "Responsable delivery",
                    "responsibility": "transforme l'analyse en plan d'action operable par l'equipe projet",
                },
                {
                    "engine_role": "verify",
                    "business_role": "Controle qualite",
                    "responsibility": "valide que le dossier est defendable, trace et exploitable",
                },
            ],
            "expected_deliverables": [
                "brief de mission",
                "liste des risques et zones floues",
                "plan d'action operatoire",
                "verdict final exploitable par le management",
            ],
            "specification": {
                "objective": (
                    f"Pour {company_name}, produire un dossier de mission clair pour auditer le depot de "
                    f"{client_name}, cadrer les priorites et organiser la reponse de l'equipe projet."
                ),
                "context": {
                    "company_name": company_name,
                    "client_name": client_name,
                    "business_context": "pre-audit technique avant engagement commercial",
                    "decision_for_management": "go/no-go et niveau de risque de la mission",
                    "delivery_mode": "cellule projet structuree avec handoffs explicites",
                },
                "constraints": [
                    "Le dossier doit etre lisible par un directeur de mission et une equipe delivery.",
                    "Conserver des handoffs traces entre cadrage, analyse, delivery et controle qualite.",
                    "Produire un livrable exploitable sans connaissance implicite du dossier client.",
                ],
                "success_criteria": [
                    "Le plan doit etre actionnable sans etape cachee.",
                    "Les risques et zones d'incertitude doivent etre explicites.",
                    "Le livrable final doit pouvoir etre valide par un controle qualite.",
                ],
                "expected_output": "mission-brief",
                "use_case_id": "operator-runbook",
            },
            "repo_audit": {
                "objective": (
                    f"Pour {company_name}, auditer le depot de {client_name} afin de confirmer sa structure, "
                    "sa documentation, ses tests, sa posture securite et la maturite de ses dependances."
                ),
                "constraints": [
                    "Ne pas modifier le depot cible.",
                    "Rester strictement en lecture seule.",
                    "Ne conclure qu'a partir de preuves observees.",
                    "Produire un dossier defendable devant un client et un management interne.",
                ],
                "success_criteria": [
                    "Le rapport doit citer des preuves traceables.",
                    "Les zones non couvertes doivent etre explicites.",
                    "Le verdict final doit rester verifiable.",
                    "Les constats doivent aider a preparer un go/no-go de mission.",
                ],
            },
        }

    if scenario == "tech-due-diligence":
        return {
            "scenario": scenario,
            "company": {
                "name": company_name,
                "activity": "fonds ou groupe strategique en evaluation d'acquisition",
                "goal": "decider rapidement si un actif logiciel vaut une acquisition ou une integration",
            },
            "client": {
                "name": client_name,
                "need": "etre evalue comme cible potentielle a partir de son depot et de sa maturite technique",
            },
            "mission": {
                "title": "Comite d'investissement technique",
                "brief": (
                    f"{company_name} doit examiner l'actif logiciel de {client_name}, identifier les red flags, "
                    "estimer l'effort d'integration et produire une recommandation pour le comite d'investissement."
                ),
            },
            "role_projection": [
                {
                    "engine_role": "plan",
                    "business_role": "Partner investissement tech",
                    "responsibility": "cadre la these, fixe les questions critiques et la barre de decision",
                },
                {
                    "engine_role": "research",
                    "business_role": "Analyste due diligence",
                    "responsibility": "collecte les preuves techniques, les angles morts et les red flags",
                },
                {
                    "engine_role": "execute",
                    "business_role": "Operating partner integration",
                    "responsibility": "convertit l'analyse en plan de remediations et feuille de route 90 jours",
                },
                {
                    "engine_role": "verify",
                    "business_role": "Risk officer",
                    "responsibility": "valide que la recommandation est defendable devant le comite",
                },
            ],
            "expected_deliverables": [
                "note d'investissement technique",
                "liste de red flags priorises",
                "plan d'integration sur 90 jours",
                "recommandation go, no-go ou go sous conditions",
            ],
            "specification": {
                "objective": (
                    f"Pour {company_name}, produire une note de cadrage permettant d'evaluer {client_name} "
                    "comme cible d'acquisition ou d'integration logicielle."
                ),
                "context": {
                    "company_name": company_name,
                    "client_name": client_name,
                    "business_context": "due diligence technique avant acquisition",
                    "decision_for_management": "recommandation d'investissement et effort d'integration",
                    "delivery_mode": "cellule d'analyse investissement avec handoffs traces",
                },
                "constraints": [
                    "Le dossier doit etre lisible par un comite d'investissement non purement technique.",
                    "Les risques doivent etre classes entre dette, securite, dependance et execution.",
                    "Le livrable doit deboucher sur une recommandation exploitable en reunion de decision.",
                ],
                "success_criteria": [
                    "Les red flags majeurs doivent etre explicitement mis en avant.",
                    "Le plan d'integration 90 jours doit etre esquisse.",
                    "La recommandation finale doit etre defendable devant un risk officer.",
                ],
                "expected_output": "investment-memo",
                "use_case_id": "operator-runbook",
            },
            "repo_audit": {
                "objective": (
                    f"Pour {company_name}, auditer le depot de {client_name} afin d'estimer les red flags, "
                    "la dette technique, la posture securite et l'effort probable d'integration."
                ),
                "constraints": [
                    "Ne pas modifier le depot cible.",
                    "Rester strictement en lecture seule.",
                    "Ne conclure qu'a partir de preuves observees.",
                    "Produire des constats exploitables dans une decision d'acquisition.",
                ],
                "success_criteria": [
                    "Le rapport doit citer des preuves traceables.",
                    "Les red flags doivent etre hierarchises.",
                    "Les zones non couvertes doivent etre explicites.",
                    "Le verdict final doit pouvoir nourrir une decision go/no-go.",
                ],
            },
        }

    known = ", ".join(DEMO_SCENARIOS)
    raise ValueError(f"Unknown demo scenario '{scenario}'. Available scenarios: {known}")


def build_demo_business_story(
    scenario: str = "delivery-mission",
    company_name: str = "Atlas Conseil",
    client_name: str = "Maison Orion",
) -> dict[str, Any]:
    payload = _scenario_payload(scenario, company_name, client_name)
    return {
        "scenario": payload["scenario"],
        "company": payload["company"],
        "client": payload["client"],
        "mission": payload["mission"],
        "role_projection": payload["role_projection"],
        "expected_deliverables": payload["expected_deliverables"],
    }


def build_demo_specification_request(
    scenario: str = "delivery-mission",
    company_name: str = "Atlas Conseil",
    client_name: str = "Maison Orion",
) -> WorkItem:
    payload = _scenario_payload(scenario, company_name, client_name)["specification"]
    return WorkItem(
        objective=payload["objective"],
        context=payload["context"],
        constraints=payload["constraints"],
        success_criteria=payload["success_criteria"],
        expected_output=payload["expected_output"],
        use_case_id=payload["use_case_id"],
    )


def build_demo_repo_audit_request(
    repo_path: str = ".",
    scenario: str = "delivery-mission",
    company_name: str = "Atlas Conseil",
    client_name: str = "Maison Orion",
) -> RepoAuditRequest:
    payload = _scenario_payload(scenario, company_name, client_name)["repo_audit"]
    return RepoAuditRequest(
        objective=payload["objective"],
        repo_target=RepoTarget(root_path=repo_path),
        audit_scope=AuditScope(
            analysis_axes=["architecture", "tests", "docs", "security", "dependencies"],
            read_limits=RepoReadLimits(max_files=60, max_bytes_per_file=16000, max_matches=60),
        ),
        constraints=payload["constraints"],
        success_criteria=payload["success_criteria"],
    )
