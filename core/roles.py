from __future__ import annotations

from abc import ABC, abstractmethod

from core.contracts import AgentDescriptor, AgentOutput, WorkItem
from core.memory import SharedMemory
from core.model_client import DryRunModelClient, ModelClient


class SpecialistAgent(ABC):
    descriptor: AgentDescriptor

    def __init__(self, model_client: ModelClient | None = None) -> None:
        self.model_client = model_client or DryRunModelClient()

    @abstractmethod
    def run(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        raise NotImplementedError


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
