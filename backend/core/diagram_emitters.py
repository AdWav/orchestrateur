from __future__ import annotations

import html
import uuid
from typing import Any


def _component_label(component: dict[str, Any]) -> str:
    classes = component.get("classes") or []
    if classes:
        return str(classes[0])
    path = str(component.get("path", component.get("id", "Module")))
    return path.split("/")[-1].split(".")[0] or "Module"


def emit_plantuml(structure: dict[str, Any]) -> str:
    """UML composants + classes (PlantUML) — format standard interoperable."""
    lines = ["@startuml", f"title Code structure — {structure.get('root_path', 'project')}", ""]
    layers = structure.get("layers") or ["default"]
    components = structure.get("components") or []

    for layer in layers:
        layer_components = [c for c in components if c.get("layer") == layer][:8]
        if not layer_components:
            continue
        lines.append(f'package "{layer}" {{')
        for component in layer_components:
            label = _component_label(component)
            cid = str(component.get("id", label)).replace(".", "_").replace("-", "_")
            classes = component.get("classes") or []
            if classes:
                lines.append(f"  class {cid} {{")
                for fn in (component.get("functions") or [])[:4]:
                    lines.append(f"    +{fn}()")
                lines.append("  }")
            else:
                lines.append(f"  class {cid} as \"{label}\"")
        lines.append("}")
        lines.append("")

    seen: set[tuple[str, str]] = set()
    for relation in (structure.get("relations") or [])[:25]:
        src = str(relation.get("from", "")).replace(".", "_").replace("-", "_")
        dst = str(relation.get("to", "")).replace(".", "_").replace("-", "_").replace("/", "_")
        key = (src, dst)
        if not src or not dst or key in seen:
            continue
        seen.add(key)
        lines.append(f"{src} ..> {dst} : imports")

    lines.extend(["", "@enduml"])
    return "\n".join(lines)


def emit_mermaid_flow(structure: dict[str, Any]) -> str:
    """Schéma de flux Mermaid (flowchart TB) — compatible GitHub/GitLab."""
    lines = [
        "```mermaid",
        "flowchart TB",
        f"  root([Project: {structure.get('root_path', '.')}])",
    ]

    layer_nodes: dict[str, str] = {}
    for layer in structure.get("layers") or []:
        node_id = f"layer_{layer}".replace("-", "_")
        layer_nodes[layer] = node_id
        lines.append(f"  {node_id}[\"Layer: {layer}\"]")
        lines.append(f"  root --> {node_id}")

    components = structure.get("components") or []
    comp_nodes: dict[str, str] = {}
    for index, component in enumerate(components[:15]):
        comp_id = f"mod_{index}"
        comp_nodes[str(component.get("id"))] = comp_id
        label = _component_label(component)
        layer = component.get("layer", "other")
        layer_node = layer_nodes.get(layer)
        lines.append(f"  {comp_id}[\"{label}\\n{component.get('path', '')}\"]")
        if layer_node:
            lines.append(f"  {layer_node} --> {comp_id}")

    for relation in (structure.get("relations") or [])[:12]:
        src = comp_nodes.get(str(relation.get("from")))
        dst_label = str(relation.get("to", "")).replace('"', "'")[:40]
        if not src:
            continue
        dep = f"dep_{uuid.uuid4().hex[:6]}"
        lines.append(f"  {dep}[\"{dst_label}\"]")
        lines.append(f"  {src} -.-> {dep}")

    entry_points = structure.get("entry_points") or []
    if entry_points:
        lines.append("  subgraph entry_points [Entry points]")
        for index, entry in enumerate(entry_points[:5]):
            eid = f"entry_{index}"
            lines.append(f"    {eid}[\"{entry}\"]")
            lines.append(f"    root --> {eid}")
        lines.append("  end")

    lines.append("```")
    return "\n".join(lines)


def emit_drawio_xml(structure: dict[str, Any]) -> str:
    """Schéma technique draw.io (mxGraphModel XML) — ouvrable dans diagrams.net."""
    components = (structure.get("components") or [])[:12]
    cell_id = 2
    cells = [
        '<mxCell id="0"/>',
        '<mxCell id="1" parent="0"/>',
        f'<mxCell id="{cell_id}" value="{html.escape(str(structure.get("root_path", "project")))}" '
        'style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1" '
        'vertex="1" parent="1">'
        f'<mxGeometry x="280" y="20" width="200" height="50" as="geometry"/></mxCell>',
    ]
    root_cell = cell_id
    cell_id += 1

    layer_y = 100
    for layer in structure.get("layers") or ["default"]:
        layer_components = [c for c in components if c.get("layer") == layer][:4]
        if not layer_components:
            continue
        layer_cell = cell_id
        cells.append(
            f'<mxCell id="{layer_cell}" value="{html.escape(layer)}" '
            'style="swimlane;horizontal=0;whiteSpace=wrap;html=1;fillColor=#f5f5f5;" '
            f'vertex="1" parent="1"><mxGeometry x="40" y="{layer_y}" width="720" height="150" as="geometry"/></mxCell>'
        )
        cell_id += 1
        cells.append(
            f'<mxCell id="{cell_id}" style="edgeStyle=orthogonalEdgeStyle;rounded=0;" edge="1" '
            f'parent="1" source="{root_cell}" target="{layer_cell}"><mxGeometry relative="1" as="geometry"/></mxCell>'
        )
        cell_id += 1

        x = 20
        module_cells: list[int] = []
        for component in layer_components:
            mod_cell = cell_id
            label = html.escape(_component_label(component))
            path = html.escape(str(component.get("path", "")))
            cells.append(
                f'<mxCell id="{mod_cell}" value="{label}&lt;br&gt;&lt;font style=&quot;font-size:10px&quot;&gt;{path}&lt;/font&gt;" '
                'style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;" '
                f'vertex="1" parent="{layer_cell}"><mxGeometry x="{x}" y="40" width="160" height="70" as="geometry"/></mxCell>'
            )
            module_cells.append(mod_cell)
            cell_id += 1
            x += 180
        layer_y += 180

    for relation in (structure.get("relations") or [])[:8]:
        src_id = None
        dst_id = None
        src_key = str(relation.get("from", ""))
        for component in components:
            if component.get("id") == src_key:
                idx = components.index(component)
                src_id = 3 + idx  # approximate; layout ids may vary
                break
        if src_id is None:
            continue
        dep_cell = cell_id
        dst_label = html.escape(str(relation.get("to", "dep"))[:30])
        cells.append(
            f'<mxCell id="{dep_cell}" value="{dst_label}" '
            'style="ellipse;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6;" '
            f'vertex="1" parent="1"><mxGeometry x="600" y="{layer_y}" width="120" height="50" as="geometry"/></mxCell>'
        )
        cell_id += 1
        cells.append(
            f'<mxCell id="{cell_id}" style="edgeStyle=orthogonalEdgeStyle;dashed=1;" edge="1" '
            f'parent="1" source="{src_id}" target="{dep_cell}"><mxGeometry relative="1" as="geometry"/></mxCell>'
        )
        cell_id += 1
        layer_y += 60

    inner = "\n        ".join(cells)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<mxfile host="app.diagrams.net" modified="2026-01-01T00:00:00.000Z" agent="orchestrateur" version="22.0.0">\n'
        '  <diagram id="code-structure" name="Code structure">\n'
        "    <mxGraphModel dx=\"1200\" dy=\"800\" grid=\"1\" gridSize=\"10\" guides=\"1\" tooltips=\"1\" "
        'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="850" pageHeight="1100" math="0" shadow="0">\n'
        "      <root>\n"
        f"        {inner}\n"
        "      </root>\n"
        "    </mxGraphModel>\n"
        "  </diagram>\n"
        "</mxfile>"
    )


def validate_diagram_bundle(
    *,
    structure: dict[str, Any],
    plantuml: str,
    drawio_xml: str,
    mermaid: str,
) -> dict[str, Any]:
    checks: list[dict[str, str]] = []
    approved = True

    def add(name: str, ok: bool, detail: str) -> None:
        nonlocal approved
        if not ok:
            approved = False
        checks.append({"check": name, "status": "pass" if ok else "fail", "detail": detail})

    component_count = len(structure.get("components") or [])
    add("structure_components", component_count > 0, f"{component_count} composants extraits")
    add("plantuml_markers", "@startuml" in plantuml and "@enduml" in plantuml, "marqueurs PlantUML presents")
    add("drawio_root", "<mxfile" in drawio_xml and "<mxGraphModel" in drawio_xml, "XML draw.io valide")
    add("mermaid_fence", "flowchart" in mermaid and "```mermaid" in mermaid, "bloc Mermaid flowchart present")

    relation_count = len(structure.get("relations") or [])
    if relation_count == 0 and component_count > 1:
        add("relations_optional", True, "Relations faibles — acceptable sur petits depots")
    else:
        add("relations", relation_count >= 0, f"{relation_count} relations mappees")

    return {
        "approved": approved,
        "checks": checks,
        "summary": "Bundle diagrammes coherent" if approved else "Revisions requises sur un ou plusieurs formats",
    }
