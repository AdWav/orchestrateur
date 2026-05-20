from __future__ import annotations

from pathlib import Path

from core.code_structure_extractor import extract_structure
from core.contracts import WorkItem
from core.definition_catalog import FileDefinitionCatalog
from core.diagram_emitters import emit_drawio_xml, emit_mermaid_flow, emit_plantuml, validate_diagram_bundle
from core.orchestrator import MultiAgentOrchestrator


def _repo_catalog() -> Path:
    return Path(__file__).resolve().parents[1] / "catalog"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_extract_structure_from_orchestrateur_repo() -> None:
    root = _repo_root()
    backend_files = [
        p.relative_to(root).as_posix()
        for p in (root / "backend" / "core").glob("*.py")
    ]
    structure = extract_structure(
        root_path=str(root),
        file_paths=backend_files,
        read_text=lambda rel: (root / rel).read_text(encoding="utf-8"),
        max_files=10,
    )
    assert structure["stats"]["component_count"] > 0
    assert "python" in structure["languages"]
    assert any("core" in c["path"] for c in structure["components"])


def test_diagram_emitters_produce_valid_markers() -> None:
    structure = {
        "root_path": "/demo",
        "layers": ["backend"],
        "components": [
            {
                "id": "backend.api",
                "path": "backend/api.py",
                "layer": "backend",
                "classes": ["Api"],
                "functions": ["run"],
                "imports": ["backend.core"],
            }
        ],
        "relations": [{"from": "backend.api", "to": "backend.core", "kind": "imports"}],
        "entry_points": ["backend/main.py"],
    }
    plantuml = emit_plantuml(structure)
    drawio = emit_drawio_xml(structure)
    mermaid = emit_mermaid_flow(structure)
    report = validate_diagram_bundle(
        structure=structure,
        plantuml=plantuml,
        drawio_xml=drawio,
        mermaid=mermaid,
    )
    assert "@startuml" in plantuml
    assert "<mxfile" in drawio
    assert "flowchart" in mermaid
    assert report["approved"] is True


def test_team_code_viz_workflow_in_catalog() -> None:
    catalog = FileDefinitionCatalog(_repo_catalog())
    wf = catalog.get_workflow("team-code-viz")
    assert [step.agent_definition_id for step in wf.steps] == [
        "viz_code_scan",
        "viz_structure",
        "viz_uml",
        "viz_drawio",
        "viz_mermaid",
        "viz_qa",
    ]


def test_run_team_code_viz_on_local_repo() -> None:
    catalog = FileDefinitionCatalog(_repo_catalog())
    orchestrator = MultiAgentOrchestrator(catalog=catalog)
    item = WorkItem(
        objective="Visualiser l'architecture du depot orchestrateur",
        use_case_id="code-visualization",
        context={
            "code_visualization": {
                "repo_target": {"root_path": str(_repo_root())},
                "audit_scope": {
                    "analysis_axes": ["architecture"],
                    "read_limits": {"max_files": 40, "max_bytes_per_file": 12000, "max_matches": 40},
                },
            }
        },
        success_criteria=[
            "PlantUML genere",
            "draw.io XML genere",
            "Mermaid flowchart genere",
        ],
    )
    result = orchestrator.run_catalog_workflow("team-code-viz", item)
    assert result.team_id == "team-code-viz"
    assert len(result.outputs) == 6
    assert [out.role for out in result.outputs] == [
        "diagram_code_scan",
        "diagram_structure",
        "diagram_uml",
        "diagram_drawio",
        "diagram_mermaid",
        "diagram_qa",
    ]
    assert result.verification_passed is True
    qa_artifacts = result.outputs[-1].artifacts
    deliverables = qa_artifacts.get("deliverables", {})
    assert "@startuml" in str(deliverables.get("plantuml", ""))
    assert "<mxfile" in str(deliverables.get("drawio_xml", ""))
    assert "flowchart" in str(deliverables.get("mermaid_flow", ""))
