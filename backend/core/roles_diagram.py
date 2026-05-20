from __future__ import annotations

from typing import Any

from core.catalog_runtime import enrich_work_item_prompt
from core.code_structure_extractor import extract_structure
from core.contracts import AgentDescriptor, AgentOutput, AuditScope, RepoAuditRequest, RepoTarget, WorkItem
from core.diagram_emitters import (
    emit_drawio_xml,
    emit_mermaid_flow,
    emit_plantuml,
    validate_diagram_bundle,
)
from core.memory import SharedMemory
from core.model_client import DryRunModelClient, ModelClient
from core.repo_capabilities import RepoCapabilities
from core.roles import SpecialistAgent, _memory_artifacts


def _resolve_repo_context(item: WorkItem) -> tuple[RepoTarget, AuditScope]:
    payload = item.context.get("code_visualization") or item.context.get("repo_audit")
    if isinstance(payload, dict):
        if "repo_target" in payload or "audit_scope" in payload:
            target = RepoTarget.model_validate(payload.get("repo_target", {}))
            scope = AuditScope.model_validate(payload.get("audit_scope", {}))
            if not scope.analysis_axes:
                scope = scope.model_copy(update={"analysis_axes": ["architecture"]})
            return target, scope
        request = RepoAuditRequest.model_validate(payload)
        return request.repo_target, request.audit_scope

    workspace = item.context.get("workspace_path")
    if workspace:
        return RepoTarget(root_path=str(workspace)), AuditScope(analysis_axes=["architecture"])

    return RepoTarget(root_path="."), AuditScope(analysis_axes=["architecture"])


def _diagram_descriptor(
    role: str,
    responsibility: str,
    *,
    capabilities: list[str],
    produces: list[str],
) -> AgentDescriptor:
    return AgentDescriptor(
        role=role,
        responsibility=responsibility,
        capabilities=capabilities,
        allowed_inputs=["objectif", "contexte depot", "handoff etapes precedentes"],
        produces=produces,
    )


def _build_prompt(item: WorkItem, role_label: str, extra: str = "", memory: SharedMemory | None = None) -> str:
    lines = [
        f"Role: {role_label}",
        f"Objective: {item.objective}",
        f"Constraints: {', '.join(item.constraints) or 'none'}",
        f"Success criteria: {', '.join(item.success_criteria) or 'none'}",
    ]
    if extra:
        lines.append(extra)
    base = "\n".join(lines)
    if memory is None:
        return base
    return enrich_work_item_prompt(base, memory)


def _remember_output(memory: SharedMemory, role: str, output: AgentOutput, step_id: str | None = None) -> None:
    dumped = output.model_dump()
    memory.remember(f"{role}_output", dumped, role)
    if step_id:
        memory.remember(f"catalog_step_output_{step_id}", dumped, role)


class DiagramCodeScanAgent(SpecialistAgent):
    descriptor = _diagram_descriptor(
        "diagram_code_scan",
        "Scanner un depot de code quelconque et collecter inventaire + signaux structurels.",
        capabilities=["repo.list_tree", "repo.read_text_file", "multi-language scan"],
        produces=["repo_inventory", "scanned_paths", "structure_seed"],
    )

    def run(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        target, scope = _resolve_repo_context(item)
        capabilities = RepoCapabilities(target, scope, memory=memory, role=self.descriptor.role)
        inventory = capabilities.build_inventory()
        structure_seed = extract_structure(
            root_path=inventory.root_path,
            file_paths=inventory.scanned_paths,
            read_text=capabilities.read_text_file,
            max_files=min(25, scope.read_limits.max_files),
        )

        prompt = _build_prompt(
            item,
            "Code scanner — inventory and structural seed",
            extra=(
                f"Repo: {inventory.root_path}\n"
                f"Languages: {', '.join(inventory.detected_languages) or 'unknown'}\n"
                f"Components seeded: {structure_seed['stats']['component_count']}"
            ),
            memory=memory,
        )
        summary = self.model_client.generate(self.descriptor.role, prompt).content

        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={
                "repo_inventory": inventory.model_dump(),
                "structure_seed": structure_seed,
                "detected_languages": inventory.detected_languages,
                "important_files": inventory.important_files,
            },
            next_actions=["Construire le modele structurel canonique pour les emitters de diagrammes."],
            approved=True,
        )
        memory.remember("repo_inventory", inventory.model_dump(), self.descriptor.role)
        memory.remember("structure_seed", structure_seed, self.descriptor.role)
        _remember_output(memory, self.descriptor.role, output, "code_scan")
        return output


class DiagramStructureAgent(SpecialistAgent):
    descriptor = _diagram_descriptor(
        "diagram_structure",
        "Consolider le modele structurel (composants, relations, couches, points d'entree).",
        capabilities=["component graph", "dependency edges", "layered view"],
        produces=["code_structure_model"],
    )

    def run(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        seed = memory.read("structure_seed", {})
        if not isinstance(seed, dict) or not seed.get("components"):
            prior = _memory_artifacts(memory, "diagram_code_scan_output")
            seed = prior.get("structure_seed", {})

        if not isinstance(seed, dict):
            seed = {}

        structure_model = {
            **seed,
            "objective": item.objective,
            "diagram_targets": ["plantuml", "drawio", "mermaid"],
        }

        prompt = _build_prompt(
            item,
            "Structure modeler — canonical graph",
            extra=f"Components: {len(structure_model.get('components', []))}, "
            f"Relations: {len(structure_model.get('relations', []))}",
            memory=memory,
        )
        summary = self.model_client.generate(self.descriptor.role, prompt).content

        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={"code_structure_model": structure_model},
            next_actions=["Emettre UML PlantUML, XML draw.io et flux Mermaid a partir du modele."],
            approved=bool(structure_model.get("components")),
        )
        memory.remember("code_structure_model", structure_model, self.descriptor.role)
        _remember_output(memory, self.descriptor.role, output, "structure")
        return output


class DiagramUmlAgent(SpecialistAgent):
    descriptor = _diagram_descriptor(
        "diagram_uml",
        "Produire un diagramme UML (PlantUML) aligne sur le modele structurel.",
        capabilities=["PlantUML", "class diagram", "component diagram"],
        produces=["plantuml", "uml_notes"],
    )

    def run(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        structure = memory.read("code_structure_model", {})
        if not isinstance(structure, dict):
            structure = {}

        plantuml = emit_plantuml(structure)
        prompt = _build_prompt(
            item,
            "UML emitter — PlantUML",
            extra=f"Generated lines: {len(plantuml.splitlines())}",
            memory=memory,
        )
        summary = self.model_client.generate(self.descriptor.role, prompt).content

        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={
                "plantuml": plantuml,
                "format": "plantuml",
                "uml_notes": [
                    "Ouvrir avec PlantUML, IntelliJ ou extensions VS Code.",
                    "Diagramme derive du modele structurel; ajuster manuellement si besoin.",
                ],
            },
            next_actions=["Generer l'equivalent draw.io (mxGraphModel XML)."],
            approved="@startuml" in plantuml,
        )
        memory.remember("plantuml_diagram", plantuml, self.descriptor.role)
        _remember_output(memory, self.descriptor.role, output, "uml")
        return output


class DiagramDrawioAgent(SpecialistAgent):
    descriptor = _diagram_descriptor(
        "diagram_drawio",
        "Produire un schema technique draw.io (XML mxGraphModel) editable dans diagrams.net.",
        capabilities=["draw.io", "mxGraphModel", "layered layout"],
        produces=["drawio_xml", "drawio_notes"],
    )

    def run(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        structure = memory.read("code_structure_model", {})
        if not isinstance(structure, dict):
            structure = {}

        drawio_xml = emit_drawio_xml(structure)
        prompt = _build_prompt(
            item,
            "Draw.io emitter — mxGraphModel XML",
            extra=f"XML bytes: {len(drawio_xml)}",
            memory=memory,
        )
        summary = self.model_client.generate(self.descriptor.role, prompt).content

        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={
                "drawio_xml": drawio_xml,
                "format": "drawio",
                "drawio_notes": [
                    "Importer dans https://app.diagrams.net/ via Fichier > Ouvrir.",
                    "Les swimlanes representent les couches detectees dans le depot.",
                ],
            },
            next_actions=["Generer le schema de flux Mermaid."],
            approved="<mxfile" in drawio_xml,
        )
        memory.remember("drawio_diagram", drawio_xml, self.descriptor.role)
        _remember_output(memory, self.descriptor.role, output, "drawio")
        return output


class DiagramMermaidAgent(SpecialistAgent):
    descriptor = _diagram_descriptor(
        "diagram_mermaid",
        "Produire un schema de flux Mermaid (flowchart) pour documentation Markdown.",
        capabilities=["Mermaid flowchart", "GitHub rendering", "layer flow"],
        produces=["mermaid_flow", "mermaid_notes"],
    )

    def run(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        structure = memory.read("code_structure_model", {})
        if not isinstance(structure, dict):
            structure = {}

        mermaid = emit_mermaid_flow(structure)
        prompt = _build_prompt(
            item,
            "Mermaid emitter — flowchart",
            extra=f"Mermaid lines: {len(mermaid.splitlines())}",
            memory=memory,
        )
        summary = self.model_client.generate(self.descriptor.role, prompt).content

        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={
                "mermaid_flow": mermaid,
                "format": "mermaid",
                "mermaid_notes": [
                    "Coller dans un Markdown compatible Mermaid (GitHub, GitLab, docs/).",
                    "Preferer flowchart TB pour la vue architecture; sequenceDiagram en complement si besoin.",
                ],
            },
            next_actions=["Lancer le controle qualite cross-format."],
            approved="flowchart" in mermaid,
        )
        memory.remember("mermaid_diagram", mermaid, self.descriptor.role)
        _remember_output(memory, self.descriptor.role, output, "mermaid")
        return output


class DiagramQaAgent(SpecialistAgent):
    descriptor = _diagram_descriptor(
        "diagram_qa",
        "Verifier la coherence entre inventaire, modele structurel et trois formats de diagrammes.",
        capabilities=["cross-format QA", "syntax checks", "approval verdict"],
        produces=["diagram_qa_report", "human_checklist"],
    )

    def run(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        structure = memory.read("code_structure_model", {})
        if not isinstance(structure, dict):
            structure = {}

        plantuml = memory.read("plantuml_diagram", "")
        drawio_xml = memory.read("drawio_diagram", "")
        mermaid = memory.read("mermaid_diagram", "")

        if not plantuml:
            plantuml = _memory_artifacts(memory, "diagram_uml_output").get("plantuml", "")
        if not drawio_xml:
            drawio_xml = _memory_artifacts(memory, "diagram_drawio_output").get("drawio_xml", "")
        if not mermaid:
            mermaid = _memory_artifacts(memory, "diagram_mermaid_output").get("mermaid_flow", "")

        report = validate_diagram_bundle(
            structure=structure,
            plantuml=str(plantuml),
            drawio_xml=str(drawio_xml),
            mermaid=str(mermaid),
        )

        prompt = _build_prompt(
            item,
            "Diagram QA — cross-format validation",
            extra=f"Approved: {report['approved']}; checks: {len(report['checks'])}",
            memory=memory,
        )
        summary = self.model_client.generate(self.descriptor.role, prompt).content

        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={
                "diagram_qa_report": report,
                "human_checklist": [
                    "Verifier manuellement les noms de modules sensibles.",
                    "Ajuster le layout draw.io si superposition de noeuds.",
                    "Committer plantuml / mermaid dans docs/ si validation OK.",
                ],
                "deliverables": {
                    "plantuml": plantuml,
                    "drawio_xml": drawio_xml,
                    "mermaid_flow": mermaid,
                },
            },
            next_actions=["Integrer les diagrammes dans la documentation ou une PR dediee."],
            approved=bool(report.get("approved")),
        )
        _remember_output(memory, self.descriptor.role, output, "qa")
        return output


from core.dev_teams import DIAGRAM_RUNNER_STEP_IDS

DIAGRAM_AGENT_BY_STEP: dict[str, type[SpecialistAgent]] = {
    "diagram_code_scan": DiagramCodeScanAgent,
    "diagram_structure": DiagramStructureAgent,
    "diagram_uml": DiagramUmlAgent,
    "diagram_drawio": DiagramDrawioAgent,
    "diagram_mermaid": DiagramMermaidAgent,
    "diagram_qa": DiagramQaAgent,
}


def diagram_agent_for_step(step_id: str, model_client: ModelClient | None = None) -> SpecialistAgent:
    agent_cls = DIAGRAM_AGENT_BY_STEP.get(step_id)
    if agent_cls is None:
        raise ValueError(f"Unknown diagram runner step '{step_id}'.")
    return agent_cls(model_client=model_client or DryRunModelClient())
