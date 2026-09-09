"""Carga los datos, ejecuta el pipeline y guarda los resultados."""

import json

import pandas as pd

from project1.clinical_rules import extract_clinical_entities, extract_clinical_relations
from project1.nlp_utils import (
    clean_text,
    extract_measurements,
    extract_reference_range_candidates,
    extract_temporal_candidates,
    split_sentences,
    tokenize,
)


def load_cases(cases_path, metadata_path, case_ids):
    cases = pd.read_csv(cases_path, dtype={"article_id": "string", "case_id": "string"})
    metadata = pd.read_csv(metadata_path, dtype={"article_id": "string"})

    required_columns = {"case_id", "case_text", "article_id"}
    missing_columns = required_columns - set(cases.columns)
    if missing_columns:
        raise ValueError(f"Faltan columnas en cases.csv: {sorted(missing_columns)}")

    if cases["case_id"].duplicated().any():
        duplicates = cases.loc[cases["case_id"].duplicated(), "case_id"].tolist()
        raise ValueError(f"Hay case_id duplicados: {duplicates}")

    cases_by_id = cases.set_index("case_id", drop=False)
    missing_cases = [case_id for case_id in case_ids if case_id not in cases_by_id.index]
    if missing_cases:
        raise ValueError(f"No se encontraron estos casos: {missing_cases}")

    selected = cases_by_id.loc[case_ids].copy().reset_index(drop=True)
    empty_text = selected["case_text"].isna() | selected["case_text"].str.strip().eq("")
    missing_article = selected["article_id"].isna() | selected["article_id"].str.strip().eq("")

    if empty_text.any():
        raise ValueError(f"Casos sin texto: {selected.loc[empty_text, 'case_id'].tolist()}")
    if missing_article.any():
        raise ValueError(
            f"Casos sin article_id: {selected.loc[missing_article, 'case_id'].tolist()}"
        )

    metadata_ids = set(metadata["article_id"].dropna())
    missing_metadata = selected.loc[
        ~selected["article_id"].isin(metadata_ids), "article_id"
    ].tolist()
    validation = {
        "requested_case_count": len(case_ids),
        "selected_case_count": len(selected),
        "all_case_ids_found": True,
        "all_case_text_nonempty": True,
        "all_article_ids_available": True,
        "article_ids_missing_from_metadata": missing_metadata,
        "age_gender_modified": False,
    }
    return selected, validation


def prepare_entities_for_csv(entities):
    rows = []
    for entity in entities:
        row = entity.copy()
        row["attributes"] = json.dumps(
            row["attributes"], ensure_ascii=False, sort_keys=True
        )
        rows.append(row)
    return rows


def write_mermaid(case_id, nodes, edges, output_path):
    lines = ["flowchart TD"]
    for node in nodes:
        node_id = node["entity_id"].replace("-", "_")
        if node["type"] == "Patient":
            label = f"Patient: {case_id}"
        else:
            span = node["original_span"].replace('"', "'").replace("\n", " ")
            label = f"{node['type']}: {span}"
        lines.append(f'    {node_id}["{label}"]')
    for edge in edges:
        source = edge["source_id"].replace("-", "_")
        target = edge["target_id"].replace("-", "_")
        lines.append(f'    {source} -->|{edge["relation"]}| {target}')
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_pipeline(cases_path, metadata_path, output_dir, case_ids):
    output_dir.mkdir(parents=True, exist_ok=True)
    mermaid_dir = output_dir / "mermaid"
    mermaid_dir.mkdir(exist_ok=True)

    selected, validation = load_cases(cases_path, metadata_path, case_ids)
    selected_output = selected[["case_id", "article_id", "case_text", "age", "gender"]].copy()
    selected_output = selected_output.rename(columns={"case_text": "original_text"})
    selected_output["cleaned_text"] = selected_output["original_text"].map(clean_text)

    all_sentences = []
    all_tokens = []
    all_measurements = []
    all_temporal_candidates = []
    all_reference_candidates = []
    all_clinical_entities = []
    all_edges = []

    for case in selected_output.itertuples(index=False):
        sentences = split_sentences(case.case_id, case.original_text)
        tokens = [token for sentence in sentences for token in tokenize(sentence)]
        measurements = extract_measurements(sentences)
        temporal_candidates = extract_temporal_candidates(sentences)
        reference_candidates = extract_reference_range_candidates(sentences)
        clinical_entities = extract_clinical_entities(sentences)
        clinical_edges = extract_clinical_relations(
            case.case_id, sentences, clinical_entities
        )

        all_sentences.extend(sentences)
        all_tokens.extend(tokens)
        all_measurements.extend(measurements)
        all_temporal_candidates.extend(temporal_candidates)
        all_reference_candidates.extend(reference_candidates)
        all_clinical_entities.extend(clinical_entities)
        all_edges.extend(clinical_edges)

    patient_nodes = []
    for case_id in case_ids:
        patient_nodes.append(
            {
                "entity_id": f"{case_id}_PATIENT",
                "case_id": case_id,
                "sentence_id": None,
                "type": "Patient",
                "original_span": "",
                "normalized_label": "patient",
                "start_char": None,
                "end_char": None,
                "attributes": {},
                "rule_id": "structural_patient_per_case_v1",
            }
        )

    all_nodes = patient_nodes + all_measurements + all_clinical_entities
    for case_id in case_ids:
        case_nodes = [node for node in all_nodes if node["case_id"] == case_id]
        case_edges = [edge for edge in all_edges if edge["case_id"] == case_id]
        write_mermaid(case_id, case_nodes, case_edges, mermaid_dir / f"{case_id}.mmd")

    selected_output.to_csv(output_dir / "selected_cases.csv", index=False)
    pd.DataFrame(all_sentences).to_csv(output_dir / "sentences.csv", index=False)
    pd.DataFrame(all_tokens).to_csv(output_dir / "tokens.csv", index=False)
    pd.DataFrame(prepare_entities_for_csv(all_measurements)).to_csv(
        output_dir / "measurements.csv", index=False
    )
    pd.DataFrame(prepare_entities_for_csv(all_temporal_candidates)).to_csv(
        output_dir / "temporal_candidates.csv", index=False
    )
    pd.DataFrame(prepare_entities_for_csv(all_reference_candidates)).to_csv(
        output_dir / "reference_range_candidates.csv", index=False
    )
    pd.DataFrame(prepare_entities_for_csv(all_clinical_entities)).to_csv(
        output_dir / "clinical_entities.csv", index=False
    )
    pd.DataFrame(prepare_entities_for_csv(all_nodes)).to_csv(
        output_dir / "nodes.csv", index=False
    )
    pd.DataFrame(prepare_entities_for_csv(all_edges)).to_csv(
        output_dir / "edges.csv", index=False
    )

    (output_dir / "validation.json").write_text(
        json.dumps(validation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    summary = {
        "cases": len(selected_output),
        "sentences": len(all_sentences),
        "tokens": len(all_tokens),
        "measurements": len(all_measurements),
        "temporal_candidates": len(all_temporal_candidates),
        "reference_range_candidates": len(all_reference_candidates),
        "clinical_entities": len(all_clinical_entities),
        "clinical_entities_by_type": {},
        "nodes": len(all_nodes),
        "edges": len(all_edges),
        "edges_by_relation": {},
        "per_case": {},
    }
    for entity in all_clinical_entities:
        entity_type = entity["type"]
        summary["clinical_entities_by_type"][entity_type] = (
            summary["clinical_entities_by_type"].get(entity_type, 0) + 1
        )
    for edge in all_edges:
        relation = edge["relation"]
        summary["edges_by_relation"][relation] = (
            summary["edges_by_relation"].get(relation, 0) + 1
        )
    for case_id in case_ids:
        summary["per_case"][case_id] = {
            "sentences": sum(row["case_id"] == case_id for row in all_sentences),
            "tokens": sum(row["case_id"] == case_id for row in all_tokens),
            "measurements": sum(row["case_id"] == case_id for row in all_measurements),
            "temporal_candidates": sum(
                row["case_id"] == case_id for row in all_temporal_candidates
            ),
            "reference_range_candidates": sum(
                row["case_id"] == case_id for row in all_reference_candidates
            ),
            "clinical_entities": sum(
                row["case_id"] == case_id for row in all_clinical_entities
            ),
            "edges": sum(row["case_id"] == case_id for row in all_edges),
            "nodes": sum(row["case_id"] == case_id for row in all_nodes),
        }

    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return summary
