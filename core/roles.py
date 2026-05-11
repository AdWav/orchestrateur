from __future__ import annotations

from abc import ABC, abstractmethod
import re
from typing import Any

from core.contracts import (
    AgentDescriptor,
    AgentOutput,
    EvidenceRef,
    Finding,
    RepoAuditRequest,
    RepoAuditValidationReport,
    RepoInventory,
    WorkItem,
)
from core.memory import SharedMemory
from core.model_client import DryRunModelClient, ModelClient
from core.repo_capabilities import RepoCapabilities


class SpecialistAgent(ABC):
    descriptor: AgentDescriptor

    def __init__(self, model_client: ModelClient | None = None) -> None:
        self.model_client = model_client or DryRunModelClient()

    @abstractmethod
    def run(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        raise NotImplementedError


def _repo_audit_request(item: WorkItem) -> RepoAuditRequest:
    payload = item.context.get("repo_audit")
    if not isinstance(payload, dict):
        raise ValueError("Le workflow repo audit attend un contexte 'repo_audit'.")
    return RepoAuditRequest.model_validate(payload)


def _search_terms_from_objective(objective: str) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for token in re.findall(r"[A-Za-z0-9_.-]{4,}", objective):
        normalized = token.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        terms.append(token)
    return terms[:6]


def _memory_output(memory: SharedMemory, key: str) -> dict[str, Any]:
    stored = memory.read(key, {})
    return stored if isinstance(stored, dict) else {}


def _memory_artifacts(memory: SharedMemory, key: str) -> dict[str, Any]:
    stored = _memory_output(memory, key)
    artifacts = stored.get("artifacts", {})
    return artifacts if isinstance(artifacts, dict) else {}


def _inventory_observation(inventory: RepoInventory, reason: str) -> EvidenceRef:
    important = ", ".join(inventory.important_files[:5]) or "aucun fichier pivot"
    excerpt = f"Fichiers pivots observes: {important}"
    return EvidenceRef(path=inventory.root_path, kind="inventory_observation", reason=reason, excerpt=excerpt)


class PlannerAgent(SpecialistAgent):
    descriptor = AgentDescriptor(
        role="Planner",
        responsibility="Decouper la demande en etapes, hypotheses et handoffs.",
        capabilities=[
            "decomposition de probleme",
            "construction d'un brief d'execution",
            "priorisation des risques",
        ],
        allowed_inputs=["objectif", "contraintes", "criteres de succes", "contexte"],
        produces=["plan_steps", "assumptions", "handoff_brief"],
    )

    def run(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        if item.use_case_id == "local-repo-audit":
            return self._run_repo_audit(item, memory)

        plan_steps = [
            f"Cadrer l'objectif principal: {item.objective}",
            "Identifier les inconnues bloquantes et les hypotheses de depart.",
            "Preparer le brief d'execution pour le role d'execution.",
            "Transmettre le resultat au verificateur avec les criteres de succes.",
        ]
        assumptions = [
            "Le workflow cible d'abord une execution locale auditable.",
            "Les outils autorises sont connus ou pourront etre listes explicitement.",
        ]
        if item.use_case_id:
            assumptions.append(f"Le cas d'usage prioritaire est {item.use_case_id}.")

        prompt = (
            f"Objective: {item.objective}\n"
            f"Constraints: {', '.join(item.constraints) or 'none'}\n"
            f"Success criteria: {', '.join(item.success_criteria) or 'none'}"
        )
        summary = self.model_client.generate(self.descriptor.role, prompt).content
        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={
                "plan_steps": plan_steps,
                "assumptions": assumptions,
                "handoff_brief": {
                    "expected_output": item.expected_output,
                    "constraints": item.constraints,
                    "success_criteria": item.success_criteria,
                },
            },
            next_actions=[
                "Faire confirmer les hypotheses importantes par le research agent.",
                "Verifier que les outils demandes respectent la policy.",
            ],
        )
        memory.remember("planner_output", output.model_dump(), self.descriptor.role)
        return output

    def _run_repo_audit(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        request = _repo_audit_request(item)
        search_plan = list(dict.fromkeys(
            list(request.audit_scope.analysis_axes) + _search_terms_from_objective(request.objective)
        ))
        path_policy = {
            "repo_root": request.repo_target.root_path,
            "include_paths": request.audit_scope.include_paths,
            "exclude_paths": request.audit_scope.exclude_paths,
            "allowed_tools": request.tool_policy.allowed_tools,
            "blocked_tools": request.tool_policy.blocked_tools,
            "read_limits": request.audit_scope.read_limits.model_dump(),
        }
        prompt = (
            f"Objective: {request.objective}\n"
            f"Repo root: {request.repo_target.root_path}\n"
            f"Axes: {', '.join(request.audit_scope.analysis_axes)}\n"
            f"Search plan: {', '.join(search_plan)}"
        )
        summary = self.model_client.generate(self.descriptor.role, prompt).content
        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={
                "audit_scope": request.audit_scope.model_dump(),
                "path_policy": path_policy,
                "search_plan": search_plan,
                "acceptance_criteria": request.success_criteria,
            },
            next_actions=[
                "Mapper le depot sans sortir du scope autorise.",
                "Collecter des preuves bornees avant toute conclusion.",
            ],
        )
        memory.remember("planner_output", output.model_dump(), self.descriptor.role)
        memory.append_event(
            self.descriptor.role,
            "Repo audit planning completed.",
            data={"search_plan": search_plan, "repo_root": request.repo_target.root_path},
        )
        return output


class ResearcherAgent(SpecialistAgent):
    descriptor = AgentDescriptor(
        role="Researcher",
        responsibility="Transformer le contexte brut en hypotheses testables et preuves requises.",
        capabilities=[
            "analyse de contexte",
            "identification des lacunes d'information",
            "definition des preuves attendues",
        ],
        allowed_inputs=["brief du planner", "contexte utilisateur", "cas d'usage"],
        produces=["knowledge_gaps", "evidence_plan", "decision_inputs"],
    )

    def run(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        if item.use_case_id == "local-repo-audit":
            return self._run_repo_audit(item, memory)

        planner_output = memory.read("planner_output", {})
        knowledge_gaps = [
            "Verifier la disponibilite reelle du GPU et de la VRAM.",
            "Confirmer si le workflow vise l'inference, le benchmark ou le fine-tuning.",
        ]
        evidence_plan = [
            "Collecter les contraintes materiel et systeme.",
            "Lister les outils locaux deja installes.",
            "Formaliser les criteres d'acceptation mesurables.",
        ]
        decision_inputs = {
            "planner_handoff": planner_output.get("artifacts", {}).get("handoff_brief", {}),
            "known_context_keys": sorted(item.context.keys()),
            "recommended_focus": item.use_case_id or "specification-factory",
        }
        prompt = (
            f"Objective: {item.objective}\n"
            f"Known context keys: {', '.join(sorted(item.context.keys())) or 'none'}"
        )
        summary = self.model_client.generate(self.descriptor.role, prompt).content
        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={
                "knowledge_gaps": knowledge_gaps,
                "evidence_plan": evidence_plan,
                "decision_inputs": decision_inputs,
            },
            next_actions=[
                "Faire produire une reponse actionnable a l'executor.",
                "Conserver les inconnues dans la memoire partagee.",
            ],
        )
        memory.remember("researcher_output", output.model_dump(), self.descriptor.role)
        return output

    def _run_repo_audit(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        request = _repo_audit_request(item)
        planner_artifacts = _memory_artifacts(memory, "planner_output")
        search_plan = planner_artifacts.get("search_plan", [])
        capabilities = RepoCapabilities(
            request.repo_target,
            request.audit_scope,
            memory=memory,
            role=self.descriptor.role,
        )
        inventory, evidence_refs, coverage_map = capabilities.collect_evidence(
            request.audit_scope.analysis_axes,
            search_plan if isinstance(search_plan, list) else [],
        )

        prompt = (
            f"Objective: {request.objective}\n"
            f"Scanned files: {inventory.total_files_scanned}\n"
            f"Important files: {', '.join(inventory.important_files[:5]) or 'none'}\n"
            f"Covered axes: {', '.join(axis for axis, paths in coverage_map.items() if paths) or 'none'}"
        )
        summary = self.model_client.generate(self.descriptor.role, prompt).content
        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={
                "repo_inventory": inventory.model_dump(),
                "important_files": inventory.important_files,
                "evidence_refs": [evidence.model_dump() for evidence in evidence_refs],
                "coverage_map": coverage_map,
            },
            next_actions=[
                "Synthetiser les preuves en constats priorises.",
                "Signaler explicitement les axes sans couverture suffisante.",
            ],
        )
        memory.remember("researcher_output", output.model_dump(), self.descriptor.role)
        memory.remember("repo_inventory", inventory.model_dump(), self.descriptor.role)
        memory.remember("repo_evidence_refs", [evidence.model_dump() for evidence in evidence_refs], self.descriptor.role)
        return output


class ExecutorAgent(SpecialistAgent):
    descriptor = AgentDescriptor(
        role="Executor",
        responsibility="Produire le livrable operationnel a partir du brief et des contraintes.",
        capabilities=[
            "redaction de plan d'action",
            "mise en forme d'un livrable",
            "preparation d'etapes operatoires",
        ],
        allowed_inputs=["brief du planner", "decision_inputs", "criteres de succes"],
        produces=["execution_brief", "checklist", "operator_notes"],
    )

    def run(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        if item.use_case_id == "local-repo-audit":
            return self._run_repo_audit(item, memory)

        planner_output = memory.read("planner_output", {})
        researcher_output = memory.read("researcher_output", {})
        execution_brief = {
            "objective": item.objective,
            "sequence": planner_output.get("artifacts", {}).get("plan_steps", []),
            "must_validate": item.success_criteria or ["Le livrable doit etre exploitable."],
            "research_inputs": researcher_output.get("artifacts", {}).get("decision_inputs", {}),
        }
        checklist = [
            "Verifier que le contexte d'entree est suffisant.",
            "Executer les etapes dans l'ordre defini.",
            "Tracer chaque handoff dans la memoire partagee.",
            "Soumettre le livrable au verificateur.",
        ]
        operator_notes = [
            "Ne pas elargir la mission sans nouveau cadrage.",
            "Arreter le workflow si une contrainte de securite n'est pas satisfaite.",
        ]
        prompt = (
            f"Objective: {item.objective}\n"
            f"Plan steps: {planner_output.get('artifacts', {}).get('plan_steps', [])}"
        )
        summary = self.model_client.generate(self.descriptor.role, prompt).content
        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={
                "execution_brief": execution_brief,
                "checklist": checklist,
                "operator_notes": operator_notes,
            },
            next_actions=[
                "Remettre le brief final au verifier.",
                "Conserver les hypotheses et ecarts constates.",
            ],
        )
        memory.remember("executor_output", output.model_dump(), self.descriptor.role)
        return output

    def _run_repo_audit(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        request = _repo_audit_request(item)
        researcher_artifacts = _memory_artifacts(memory, "researcher_output")
        inventory_payload = researcher_artifacts.get("repo_inventory", {})
        inventory = RepoInventory.model_validate(inventory_payload) if inventory_payload else RepoInventory(
            root_path=request.repo_target.root_path,
            total_files_scanned=0,
        )
        evidence_refs = [
            EvidenceRef.model_validate(evidence)
            for evidence in researcher_artifacts.get("evidence_refs", [])
            if isinstance(evidence, dict)
        ]
        coverage_map = {
            str(axis): list(paths)
            for axis, paths in researcher_artifacts.get("coverage_map", {}).items()
            if isinstance(paths, list)
        }
        findings = self._build_repo_findings(request, inventory, coverage_map)
        recommended_actions = sorted(
            {action for finding in findings for action in finding.recommended_actions}
        )
        unknowns = [
            f"Axe sans couverture suffisante: {axis}"
            for axis in request.audit_scope.analysis_axes
            if not coverage_map.get(axis)
        ]
        repo_summary = (
            f"Depot analyse depuis {inventory.root_path} avec {inventory.total_files_scanned} fichiers scannes, "
            f"{len(evidence_refs)} preuves collectees et {len(findings)} constats."
        )
        prompt = (
            f"Objective: {request.objective}\n"
            f"Inventory files: {inventory.total_files_scanned}\n"
            f"Findings: {len(findings)}\n"
            f"Unknowns: {', '.join(unknowns) or 'none'}"
        )
        summary = self.model_client.generate(self.descriptor.role, prompt).content
        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={
                "findings": [finding.model_dump() for finding in findings],
                "repo_summary": repo_summary,
                "risk_register": [f"{finding.severity}:{finding.title}" for finding in findings],
                "recommended_actions": recommended_actions,
                "unknowns": unknowns,
            },
            next_actions=[
                "Verifier que chaque constat reste soutenu par une preuve.",
                "Refuser toute conclusion hors du scope defini.",
            ],
        )
        memory.remember("executor_output", output.model_dump(), self.descriptor.role)
        memory.remember("repo_findings", [finding.model_dump() for finding in findings], self.descriptor.role)
        return output

    def _build_repo_findings(
        self,
        request: RepoAuditRequest,
        inventory: RepoInventory,
        coverage_map: dict[str, list[str]],
    ) -> list[Finding]:
        scanned_paths = set(inventory.scanned_paths)
        important_paths = set(inventory.important_files)
        findings: list[Finding] = []

        has_docs = any(path == "README.md" or path.startswith("docs/") for path in scanned_paths | important_paths)
        has_tests = any(path.startswith("tests/") or path.split("/")[-1].startswith("test_") for path in scanned_paths)
        has_manifest = any(
            path.split("/")[-1] in {"pyproject.toml", "requirements.txt", "package.json", "poetry.lock"}
            for path in scanned_paths | important_paths
        )
        has_env = any(path.split("/")[-1] == ".env" for path in scanned_paths)
        has_env_example = any(path.split("/")[-1] == ".env.example" for path in scanned_paths | important_paths)

        if inventory.truncated:
            findings.append(
                Finding(
                    id="partial-coverage",
                    category="coverage",
                    severity="medium",
                    title="Couverture de depot partielle",
                    summary="Le depot a ete tronque par les limites de lecture; certains constats peuvent manquer de couverture.",
                    impacted_paths=[inventory.root_path],
                    evidence_refs=[
                        _inventory_observation(
                            inventory,
                            "L'inventaire a atteint la limite max_files du workflow.",
                        )
                    ],
                    recommended_actions=[
                        "Relancer l'audit avec un scope plus etroit ou une limite max_files plus haute."
                    ],
                )
            )

        if "docs" in request.audit_scope.analysis_axes and not has_docs:
            findings.append(
                Finding(
                    id="missing-docs-surface",
                    category="documentation",
                    severity="medium",
                    title="Surface documentaire limitee",
                    summary="Aucun README ni repertoire docs n'a ete detecte dans le scope analyse.",
                    impacted_paths=[inventory.root_path],
                    evidence_refs=[
                        _inventory_observation(inventory, "Aucun support de documentation visible dans l'inventaire.")
                    ],
                    recommended_actions=["Ajouter un README ou des docs minimales pour cadrer le depot."],
                )
            )

        if "tests" in request.audit_scope.analysis_axes and not has_tests:
            findings.append(
                Finding(
                    id="missing-tests",
                    category="tests",
                    severity="high",
                    title="Absence de tests visibles",
                    summary="Le scope audite ne montre ni repertoire tests ni fichiers de tests explicites.",
                    impacted_paths=[inventory.root_path],
                    evidence_refs=[
                        _inventory_observation(inventory, "Aucun fichier de test n'a ete trouve dans les chemins scannes.")
                    ],
                    recommended_actions=["Ajouter au moins un jeu de tests smoke ou unitaires dans le repo."],
                )
            )

        if "dependencies" in request.audit_scope.analysis_axes and not has_manifest:
            findings.append(
                Finding(
                    id="missing-manifest",
                    category="dependencies",
                    severity="medium",
                    title="Manifest de dependances introuvable",
                    summary="Le workflow n'a detecte aucun manifest standard de dependances dans le scope.",
                    impacted_paths=[inventory.root_path],
                    evidence_refs=[
                        _inventory_observation(inventory, "Aucun pyproject, requirements ou package manifest observe.")
                    ],
                    recommended_actions=["Documenter et versionner explicitement les dependances du projet."],
                )
            )

        if "security" in request.audit_scope.analysis_axes and has_env and not has_env_example:
            findings.append(
                Finding(
                    id="missing-env-example",
                    category="security",
                    severity="high",
                    title="Configuration sensible peu documentee",
                    summary="Un fichier .env a ete detecte sans equivalent .env.example dans le scope analyse.",
                    impacted_paths=[".env"],
                    evidence_refs=[
                        _inventory_observation(
                            inventory,
                            "Presence de .env sans gabarit public .env.example pour documenter les variables attendues.",
                        )
                    ],
                    recommended_actions=["Ajouter un .env.example et retirer toute valeur sensible du versionnement."],
                )
            )

        if "architecture" in request.audit_scope.analysis_axes and not coverage_map.get("architecture"):
            findings.append(
                Finding(
                    id="weak-architecture-coverage",
                    category="architecture",
                    severity="medium",
                    title="Peu de signaux d'architecture visibles",
                    summary="Le scope ne montre pas assez de fichiers pivots pour caracteriser clairement l'architecture.",
                    impacted_paths=[inventory.root_path],
                    evidence_refs=[
                        _inventory_observation(
                            inventory,
                            "Les fichiers pivots detectes ne couvrent pas clairement l'axe architecture.",
                        )
                    ],
                    recommended_actions=["Elargir le scope ou ajouter une documentation d'architecture minimale."],
                )
            )

        return findings


class VerifierAgent(SpecialistAgent):
    descriptor = AgentDescriptor(
        role="Verifier",
        responsibility="Controler la qualite du livrable, les garde-fous et la completude.",
        capabilities=[
            "verification de contrat",
            "controle des criteres de succes",
            "decision go/no-go",
        ],
        allowed_inputs=["sorties planner/researcher/executor", "criteres de succes", "guardrails"],
        produces=["verification_report", "approval", "missing_items"],
    )

    def run(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        if item.use_case_id == "local-repo-audit":
            return self._run_repo_audit(item, memory)

        planner_output = memory.read("planner_output", {})
        researcher_output = memory.read("researcher_output", {})
        executor_output = memory.read("executor_output", {})
        has_required_outputs = all(
            bool(output)
            for output in (planner_output, researcher_output, executor_output)
        )
        missing_items = []
        if not item.success_criteria:
            missing_items.append("Aucun critere de succes n'a ete fourni.")
        if not has_required_outputs:
            missing_items.append("Une ou plusieurs sorties d'agents manquent.")
        if item.guardrails.max_iterations != 1:
            missing_items.append("Ce squelette gere une seule iteration de workflow.")

        approved = not missing_items
        verification_report = {
            "approved": approved,
            "checked_roles": ["Planner", "Researcher", "Executor"],
            "missing_items": missing_items,
            "stop_conditions": item.guardrails.stop_conditions,
        }
        prompt = (
            f"Objective: {item.objective}\n"
            f"Approved: {approved}\n"
            f"Missing items: {missing_items}"
        )
        summary = self.model_client.generate(self.descriptor.role, prompt).content
        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={"verification_report": verification_report},
            next_actions=[
                "Valider le workflow si aucun manque n'est detecte.",
                "Sinon renvoyer vers le planner avec un ecart qualifie.",
            ],
            approved=approved,
        )
        memory.remember("verifier_output", output.model_dump(), self.descriptor.role)
        return output

    def _run_repo_audit(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        request = _repo_audit_request(item)
        researcher_artifacts = _memory_artifacts(memory, "researcher_output")
        executor_artifacts = _memory_artifacts(memory, "executor_output")
        evidence_refs = [
            EvidenceRef.model_validate(evidence)
            for evidence in researcher_artifacts.get("evidence_refs", [])
            if isinstance(evidence, dict)
        ]
        findings = [
            Finding.model_validate(finding)
            for finding in executor_artifacts.get("findings", [])
            if isinstance(finding, dict)
        ]
        coverage_map = {
            str(axis): list(paths)
            for axis, paths in researcher_artifacts.get("coverage_map", {}).items()
            if isinstance(paths, list)
        }
        events = memory.snapshot().get("events", [])

        unsupported_claims = [
            f"Le constat '{finding.title}' n'est pas rattache a une preuve."
            for finding in findings
            if not finding.evidence_refs
        ]
        missing_requirements = [
            f"Axe non couvert: {axis}"
            for axis in request.audit_scope.analysis_axes
            if not coverage_map.get(axis)
        ]
        blocked_tool_hits = [
            event.get("message", "")
            for event in events
            if isinstance(event, dict)
            and any(blocked in event.get("message", "") for blocked in request.tool_policy.blocked_tools)
        ]
        policy_compliance = [
            "Les outils autorises restent limites a la lecture du repo."
            if not blocked_tool_hits
            else "Des outils bloques apparaissent dans la trace d'execution."
        ]
        covered_axes = sorted(axis for axis, paths in coverage_map.items() if paths)
        validation_report = RepoAuditValidationReport(
            approved=not unsupported_claims and not missing_requirements and not blocked_tool_hits,
            covered_axes=covered_axes,
            unsupported_claims=unsupported_claims,
            policy_compliance=policy_compliance,
            missing_requirements=missing_requirements,
            evidence_count=len(evidence_refs),
        )
        prompt = (
            f"Objective: {request.objective}\n"
            f"Evidence count: {len(evidence_refs)}\n"
            f"Covered axes: {', '.join(covered_axes) or 'none'}\n"
            f"Missing requirements: {', '.join(missing_requirements) or 'none'}"
        )
        summary = self.model_client.generate(self.descriptor.role, prompt).content
        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={"validation_report": validation_report.model_dump()},
            next_actions=[
                "Accepter le rapport seulement si chaque constat reste justifie.",
                "Relancer un audit plus cible si un axe reste sans couverture.",
            ],
            approved=validation_report.approved,
        )
        memory.remember("verifier_output", output.model_dump(), self.descriptor.role)
        memory.remember("repo_validation_report", validation_report.model_dump(), self.descriptor.role)
        return output
