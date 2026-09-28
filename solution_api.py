import json
import re
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"


def _load_module(module_path: Path):
    module_name = f"nlp_{module_path.stem}_{abs(hash(module_path))}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _normalize_summary(solution_id, text, nodes, edges):
    return {
        "solution_id": int(solution_id),
        "title": {
            1: "Approach 1 – BPE / PMI co-occurrence",
            2: "Approach 2 – POS tagging graph",
            3: "Approach 3 – Rule-based clinical graph",
            4: "Approach 4 – Controlled gazetteer graph",
        }[int(solution_id)],
        "input_length": len(text or ""),
        "node_count": len(nodes),
        "edge_count": len(edges),
    }


def _clean_text(text):
    return (text or "").strip()


def _dedupe_preserve_order(items):
    seen = set()
    out = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _tokenize_approach_one(text):
    module = _load_module(SRC / "01_bpe_subword_pipeline.py")
    tokens = module.regex_tokenize(text)
    tokens = [t for t in tokens if t and len(t) > 1]
    return _dedupe_preserve_order(tokens)


def _classify_approach_one(token):
    lower = token.lower()
    if re.search(r"\d", lower):
        return "measurement"
    for key, values in {
        "symptom": ["pain", "nausea", "constipation", "fever", "vomiting", "fatigue", "dyspnea", "edema", "cough"],
        "anatomy": ["pancreas", "stomach", "bowel", "liver", "lung", "colon", "kidney", "brain"],
        "exam": ["ct", "scan", "mri", "ultrasound", "biopsy", "endoscopy", "scopy", "tomography"],
        "diagnosis": ["cyst", "tumor", "mass", "lesion", "adenocarcinoma", "carcinoma"],
        "treatment": ["surgery", "resection", "chemotherapy", "drainage", "stent"],
    }.items():
        if any(value in lower for value in values):
            return key
    return "unknown"


def build_approach_1(text):
    text = _clean_text(text)
    tokens = _tokenize_approach_one(text)
    nodes = [{"id": "patient", "label": "Patient", "type": "patient"}]
    edges = []
    seen_nodes = {"patient"}
    for index, token in enumerate(tokens):
        token_type = _classify_approach_one(token)
        node_id = f"token_{index}_{token.replace(' ', '_')}"
        if token_type != "unknown":
            nodes.append({"id": node_id, "label": token, "type": token_type})
            seen_nodes.add(node_id)
            edges.append({"from": "patient", "to": node_id, "label": "mentions", "weight": 1})
        for j in range(max(0, index - 2), min(len(tokens), index + 3)):
            if j == index:
                continue
            other_token = tokens[j]
            other_type = _classify_approach_one(other_token)
            if other_type == "unknown":
                continue
            other_id = f"token_{j}_{other_token.replace(' ', '_')}"
            if other_id not in seen_nodes:
                nodes.append({"id": other_id, "label": other_token, "type": other_type})
                seen_nodes.add(other_id)
            edges.append({"from": node_id, "to": other_id, "label": "co_occurs", "weight": 1})
    summary = _normalize_summary(1, text, nodes, edges)
    return {"nodes": nodes, "edges": edges, "summary": summary}


def build_approach_2(text):
    text = _clean_text(text)
    module = _load_module(SRC / "02_pos_tagging_pipeline.py")
    graph = module.build_generic_graph(text)
    node_df, node_map = module.generate_node_table(graph)
    edge_df = module.generate_edge_table(graph, node_map)

    nodes = []
    for _, row in node_df.iterrows():
        nodes.append({
            "id": str(row["node_id"]),
            "label": str(row["label"]),
            "type": str(row["type"]),
            "attributes": row["attributes"],
        })

    edges = []
    for _, row in edge_df.iterrows():
        edges.append({
            "from": str(row["source_id"]),
            "to": str(row["target_id"]),
            "label": str(row["relation"]),
            "weight": 1,
        })

    summary = _normalize_summary(2, text, nodes, edges)
    return {"nodes": nodes, "edges": edges, "summary": summary}


def build_approach_3(text):
    text = _clean_text(text)
    module = _load_module(SRC / "03_rule_based_pipeline.py")
    tokens = re.findall(r"[A-Za-z][A-Za-z-]+", text)
    patient_id = "patient"
    nodes = [{"id": patient_id, "label": "Patient", "type": "patient"}]
    edges = []

    for token in _dedupe_preserve_order(tokens):
        clean = module.clean_term(token)
        if not clean or len(clean) < 3:
            continue
        category = module.categorise_term(clean)
        node_id = f"entity_{clean.replace(' ', '_')}"
        nodes.append({"id": node_id, "label": clean.title(), "type": category})
        relation = "PRESENTS_WITH" if category in {"Symptom", "Diagnosis"} else "ASSOCIATED_WITH"
        if category == "Exam":
            relation = "UNDERWENT_EXAM"
        edges.append({"from": patient_id, "to": node_id, "label": relation, "weight": 1})

    summary = _normalize_summary(3, text, nodes, edges)
    return {"nodes": nodes, "edges": edges, "summary": summary}


def build_approach_4(text):
    text = _clean_text(text)
    module_utils = _load_module(SRC / "approach_04_controlled_gazetteer" / "nlp_utils.py")
    module_rules = _load_module(SRC / "approach_04_controlled_gazetteer" / "clinical_rules.py")

    sentences = module_utils.split_sentences("DEMO_CASE", text)
    entities = module_rules.extract_clinical_entities(sentences)
    edges = module_rules.extract_clinical_relations("DEMO_CASE", sentences, entities)

    nodes = [{"id": "patient", "label": "Patient", "type": "patient"}]
    node_ids = {"patient"}

    for entity in entities:
        entity_id = str(entity["entity_id"])
        if entity_id not in node_ids:
            nodes.append({
                "id": entity_id,
                "label": entity.get("normalized_label") or entity.get("original_span"),
                "type": entity.get("type", "Unknown"),
                "attributes": entity.get("attributes", {}),
            })
            node_ids.add(entity_id)

    normalized_edges = []
    for edge in edges:
        normalized_edges.append({
            "from": str(edge["source_id"]),
            "to": str(edge["target_id"]),
            "label": str(edge["relation"]),
            "weight": 1,
        })

    summary = _normalize_summary(4, text, nodes, normalized_edges)
    return {"nodes": nodes, "edges": normalized_edges, "summary": summary}


SOLUTIONS = {
    1: build_approach_1,
    2: build_approach_2,
    3: build_approach_3,
    4: build_approach_4,
}


def build_solution_graph(solution_id, text):
    solution_id = int(solution_id)
    if solution_id not in SOLUTIONS:
        raise ValueError(f"Unsupported solution id: {solution_id}")
    return SOLUTIONS[solution_id](text)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build a clinical graph for one NLP approach")
    parser.add_argument("--solution", type=int, required=True)
    parser.add_argument("--text", type=str, default="")
    args = parser.parse_args()
    payload = build_solution_graph(args.solution, args.text)
    print(json.dumps(payload, ensure_ascii=False))
