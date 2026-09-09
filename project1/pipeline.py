"""Carga los datos, ejecuta el pipeline y guarda los resultados."""

import json

import pandas as pd

from project1.nlp_utils import clean_text, extract_measurements, split_sentences, tokenize


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


def write_mermaid(case_id, measurements, output_path):
    lines = ["flowchart TD", f'    PATIENT["Patient: {case_id}"]']
    for measurement in measurements:
        node_id = measurement["entity_id"].replace("-", "_")
        label = measurement["original_span"].replace('"', "'").replace("\n", " ")
        lines.append(f'    {node_id}["Measurement: {label}"]')
    lines.append(
        "    %% No edges: clinical/structural relations were not approved in Iteration 1."
    )
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

    for case in selected_output.itertuples(index=False):
        sentences = split_sentences(case.case_id, case.original_text)
        tokens = [token for sentence in sentences for token in tokenize(sentence)]
        measurements = extract_measurements(sentences)

        all_sentences.extend(sentences)
        all_tokens.extend(tokens)
        all_measurements.extend(measurements)
        write_mermaid(case.case_id, measurements, mermaid_dir / f"{case.case_id}.mmd")

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

    selected_output.to_csv(output_dir / "selected_cases.csv", index=False)
    pd.DataFrame(all_sentences).to_csv(output_dir / "sentences.csv", index=False)
    pd.DataFrame(all_tokens).to_csv(output_dir / "tokens.csv", index=False)
    pd.DataFrame(prepare_entities_for_csv(all_measurements)).to_csv(
        output_dir / "measurements.csv", index=False
    )
    pd.DataFrame(prepare_entities_for_csv(patient_nodes + all_measurements)).to_csv(
        output_dir / "nodes.csv", index=False
    )
    pd.DataFrame(
        columns=[
            "case_id", "edge_id", "source_id", "target_id", "relation",
            "attributes", "evidence", "sentence_id", "rule_id",
        ]
    ).to_csv(output_dir / "edges.csv", index=False)

    (output_dir / "validation.json").write_text(
        json.dumps(validation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    summary = {
        "cases": len(selected_output),
        "sentences": len(all_sentences),
        "tokens": len(all_tokens),
        "measurements": len(all_measurements),
        "edges": 0,
        "per_case": {},
    }
    for case_id in case_ids:
        summary["per_case"][case_id] = {
            "sentences": sum(row["case_id"] == case_id for row in all_sentences),
            "tokens": sum(row["case_id"] == case_id for row in all_tokens),
            "measurements": sum(row["case_id"] == case_id for row in all_measurements),
        }

    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return summary
