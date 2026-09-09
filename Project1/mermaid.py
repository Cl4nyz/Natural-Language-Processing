from pathlib import Path

from .models import Entity


def _escape(label: str) -> str:
    return label.replace('"', "'").replace("\n", " ")


def write_case_mermaid(case_id: str, entities: list[Entity], output_path: Path) -> None:
    lines = ["flowchart TD", f'    PATIENT["Patient: {_escape(case_id)}"]']
    for entity in entities:
        node_name = entity.entity_id.replace("-", "_")
        label = _escape(f"Measurement: {entity.original_span}")
        lines.append(f'    {node_name}["{label}"]')
    lines.append("    %% No edges: clinical/structural relations were not approved in Iteration 1.")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
