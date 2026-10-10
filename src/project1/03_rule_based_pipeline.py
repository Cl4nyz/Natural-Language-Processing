import ast
import os
import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path.cwd().resolve()
if not (PROJECT_ROOT / "data").exists():
    PROJECT_ROOT = PROJECT_ROOT.parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

METADATA_PATH = DATA_RAW / "metadata.csv"
CASES_PATH = DATA_RAW / "cases.csv"

BLACKLIST = {
    "medical", "complication", "complications", "history", "case", "reports", "report",
    "review", "differential", "uninvolved", "diagnoses", "diagnosis", "family",
    "physical", "examination", "present", "presented", "presence", "absence",
    "findings", "finding", "pathology", "pathologies", "outcome", "outcomes",
    "year", "years", "old", "age", "gender", "male", "female", "patient", "patients",
    "follow-up", "followup", "day", "days", "month", "months", "week", "weeks",
    "time", "study", "studies", "treatment", "treatments", "result", "results",
    "test", "tests", "normal", "abnormal", "abnormalities", "evidence", "showed",
    "revealed", "demonstrated", "associated", "association", "presenting", "past",
    "past history", "clinical", "unremarkable", "without", "underwent", "history of",
    "status", "period", "follow-up period", "postoperative", "uncontributory",
    "discharge", "admission", "hospital", "primary", "secondary", "acute", "chronic",
    "resection"
}

SYMPTOM_KEYWORDS = [
    "pain", "nausea", "constipation", "fever", "chills", "vomiting", "diarrhea",
    "fatigue", "headache", "cough", "breathlessness", "dyspnea", "edema", "weakness",
    "swelling", "prickling", "erosion", "blisters", "maculopapules", "obstruction",
    "emptying", "gastroparesis", "bleeding", "leak", "infection", "abscess", "lesion",
    "nodules", "shadows", "effusion", "necrosis", "ache", "algia", "pnea", "vomit",
    "nauseous", "constipated", "feverish", "coughing", "diarrheal"
]

EXAM_KEYWORDS = [
    "scopy", "tomy", "ectomy", "graphy", "ultrasound", "tomography", "mri", "ct",
    "ekg", "biopsy", "resection", "drainage", "stent", "x-ray", "xray", "exploration",
    "aspiration", "fnac", "fna", "pathology", "colonoscopy", "endoscopy",
    "laparoscopy", "pancreatectomy", "ultrasonography"
]

ANATOMY_KEYWORDS = [
    "stomach", "pancreas", "bowel", "heart", "lung", "kidney", "liver", "spleen",
    "chest", "brain", "colon", "gastric", "hepatic", "pancreatic", "splenic",
    "pulmonary", "abdominal", "artery", "vein", "appendix", "ovary", "uterus",
    "alveoli", "bronchus", "flank", "coeliac", "duodenum", "duodenal", "esophagus",
    "oesophagus", "rectum", "rectal", "cardiac", "renal", "ventricular", "atrium",
    "atrial", "thoracic", "mesenteric", "tissue", "mucosa", "mucosal", "vesicle"
]

DIAGNOSIS_KEYWORDS = [
    "cyst", "adenocarcinoma", "neoplasm", "zoster", "herpes", "cancer", "tumor",
    "sarcoma", "lymphoma", "melanoma", "leukemia", "carcinoma", "ulcer", "fistula",
    "hernia", "diverticulitis", "pancreatitis", "cholecystitis", "appendicitis",
    "gastritis", "colitis", "duodeni", "diseases", "disease", "aneurysm",
    "thrombosis", "stenosis", "adenoma", "endometriosis", "cardiomyopathy",
    "tuberculosis", "endocarditis", "abscess"
]

NEGATION_WORDS = [
    "no", "denied", "without", "negative", "normal", "unremarkable",
    "free of", "no evidence of", "absence of", "ruled out", "denies",
    "resolved", "resolution of"
]

VALUE_UNIT_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(mg/L|ng/ml|iu/ml|mmHg|cm|g/dl|%|U/L|mg/kg|g|mg|ml|fL|IU/L|k/mm3|gm/dL|meq/liter|ms)\b",
    re.IGNORECASE,
)
MEDICAL_SUFFIXES_PATTERN = re.compile(
    r"\b\w+(?:itis|osis|asis|ectomy|scopy|pathy|oma|algia|pnea|cardia|tomy)\b",
    re.IGNORECASE,
)


def parse_list_string(val):
    if pd.isna(val):
        return []
    val = str(val).strip()
    if not val:
        return []
    try:
        parsed = ast.literal_eval(val)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed]
    except Exception:
        pass
    if val.startswith("[") and val.endswith("]"):
        val = val[1:-1]
    return [term.strip() for term in val.split(",") if term.strip()]


def clean_term(term):
    if "/" in term:
        term = term.split("/")[0]
    term = re.sub(r"^[^\w\s]+|[^\w\s]+$", "", term)
    return term.strip().lower()


def categorise_term(term):
    term_lower = term.lower()
    if any(k in term_lower for k in SYMPTOM_KEYWORDS):
        return "Symptom"
    if any(k in term_lower for k in EXAM_KEYWORDS):
        return "Exam"
    if any(k in term_lower for k in ANATOMY_KEYWORDS):
        return "Anatomy"
    if any(k in term_lower for k in DIAGNOSIS_KEYWORDS) or "cystic" in term_lower:
        return "Diagnosis"
    return "Diagnosis"


def build_reference_vocabulary():
    raw_mesh_terms = []
    raw_keywords = []

    if os.path.exists(METADATA_PATH):
        df_meta = pd.read_csv(METADATA_PATH)
        for _, row in df_meta.iterrows():
            raw_mesh_terms.extend(parse_list_string(row.get("mesh_terms", "")))
            raw_mesh_terms.extend(parse_list_string(row.get("major_mesh_terms", "")))
            raw_keywords.extend(parse_list_string(row.get("keywords", "")))

    cleaned_mesh = [clean_term(t) for t in raw_mesh_terms if t]
    cleaned_keywords = [clean_term(t) for t in raw_keywords if t]

    medical_mesh = {t for t in cleaned_mesh if t and t not in BLACKLIST and len(t) > 3}
    medical_keywords = {t for t in cleaned_keywords if t and t not in BLACKLIST and len(t) > 3}

    suffix_terms = set()
    if os.path.exists(CASES_PATH):
        df_cases = pd.read_csv(CASES_PATH)
        for text in df_cases["case_text"].dropna():
            matches = MEDICAL_SUFFIXES_PATTERN.findall(text)
            for m in matches:
                term = m.lower()
                if len(term) > 3 and term not in BLACKLIST:
                    suffix_terms.add(term)

    return medical_mesh.union(medical_keywords).union(suffix_terms)


def process_cases_to_graph(all_discovered_terms):
    all_nodes = []
    all_edges = []
    node_ids_global = set()

    if not os.path.exists(CASES_PATH):
        return pd.DataFrame(), pd.DataFrame()

    df_cases = pd.read_csv(CASES_PATH)

    for _, row in df_cases.iterrows():
        case_id = row["case_id"]
        age = row["age"]
        gender = row["gender"]
        text = row["case_text"]

        if pd.isna(text):
            continue

        patient_node_id = f"Patient_{case_id}"
        all_nodes.append({
            "node_id": patient_node_id,
            "type": "Patient",
            "label": f"Patient ({case_id})",
            "attributes": f"age={age}; gender={gender}"
        })

        sentences = [s.strip() for s in re.split(r"\. |\n", text) if s.strip()]

        for s_idx, sentence in enumerate(sentences):
            found_results = []
            for val_match in VALUE_UNIT_PATTERN.finditer(sentence):
                value_str = val_match.group()
                num_val = val_match.group(1)
                unit_val = val_match.group(2)

                result_node_id = f"Result_{case_id}_{num_val}_{unit_val.replace('/', '_')}"
                if result_node_id not in node_ids_global:
                    all_nodes.append({
                        "node_id": result_node_id,
                        "type": "ExamResult",
                        "label": value_str,
                        "attributes": f"value={num_val}; unit={unit_val}"
                    })
                    node_ids_global.add(result_node_id)
                found_results.append((result_node_id, value_str))

            found_entities = []
            for term in all_discovered_terms:
                pattern = re.compile(rf"\b{re.escape(term)}s?\b", re.IGNORECASE)
                match = pattern.search(sentence)
                if match:
                    snippet_before = sentence[max(0, match.start() - 30):match.start()].lower()
                    negated = any(neg in snippet_before for neg in NEGATION_WORDS)

                    category = categorise_term(term)
                    entity_node_id = f"Entity_{term.replace(' ', '_').lower()}"

                    if entity_node_id not in node_ids_global:
                        all_nodes.append({
                            "node_id": entity_node_id,
                            "type": category,
                            "label": term.title(),
                            "attributes": f"category={category}"
                        })
                        node_ids_global.add(entity_node_id)

                    found_entities.append({
                        "id": entity_node_id,
                        "term": term,
                        "category": category,
                        "negated": negated,
                        "snippet": sentence[max(0, match.start() - 20):min(len(sentence), match.end() + 20)].strip()
                    })

            for ent in found_entities:
                if ent["category"] == "Symptom":
                    rel = "DENIES_SYMPTOM" if ent["negated"] else "PRESENTS_WITH"
                elif ent["category"] == "Diagnosis":
                    rel = "RULED_OUT" if ent["negated"] else "DIAGNOSED_WITH"
                elif ent["category"] == "Exam":
                    rel = "UNDERWENT_EXAM"
                else:
                    rel = "ASSOCIATED_WITH"

                all_edges.append({
                    "edge_id": f"Edge_{case_id}_{ent['id']}_{s_idx}",
                    "source_id": patient_node_id,
                    "target_id": ent["id"],
                    "relation": rel,
                    "attributes": f"evidence='...{ent['snippet']}...'"
                })

            for res_id, res_str in found_results:
                for ent in found_entities:
                    if ent["category"] == "Exam":
                        all_edges.append({
                            "edge_id": f"Edge_Res_{case_id}_{ent['id']}_{res_id}",
                            "source_id": ent["id"],
                            "target_id": res_id,
                            "relation": "HAS_RESULT",
                            "attributes": "measured_value"
                        })
                    elif ent["category"] == "Diagnosis":
                        all_edges.append({
                            "edge_id": f"Edge_Res_{case_id}_{ent['id']}_{res_id}",
                            "source_id": ent["id"],
                            "target_id": res_id,
                            "relation": "HAS_SIZE" if ("cm" in res_str or "mm" in res_str) else "HAS_LAB_VALUE",
                            "attributes": "measured_attribute"
                        })

            anatomies_in_sentence = [e for e in found_entities if e["category"] == "Anatomy"]
            problems_in_sentence = [e for e in found_entities if e["category"] in ["Symptom", "Diagnosis"]]
            for prob in problems_in_sentence:
                for anat in anatomies_in_sentence:
                    all_edges.append({
                        "edge_id": f"Edge_Loc_{case_id}_{prob['id']}_{anat['id']}",
                        "source_id": prob["id"],
                        "target_id": anat["id"],
                        "relation": "LOCATED_IN",
                        "attributes": "anatomical_localization"
                    })

    df_out_nodes = pd.DataFrame(all_nodes).drop_duplicates(subset=["node_id"])
    df_out_edges = pd.DataFrame(all_edges).drop_duplicates(subset=["edge_id"])
    return df_out_nodes, df_out_edges


import html
import json
import os
import random
from pathlib import Path

import pandas as pd
from pyvis.network import Network

PROJECT_ROOT = Path.cwd().resolve()
if not (PROJECT_ROOT / "data").exists():
    PROJECT_ROOT = PROJECT_ROOT.parent.parent
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DEFAULT_NODES_PATH = DATA_PROCESSED / "03_nodes.csv"
DEFAULT_EDGES_PATH = DATA_PROCESSED / "03_edges.csv"

NODE_THEMES = {
    "Patient": {
        "bg": "#0284c7",
        "border": "#0369a1",
        "font": "#ffffff",
        "level": 0
    },
    "Symptom": {
        "bg": "#fee2e2",
        "border": "#ef4444",
        "font": "#991b1b",
        "level": 1
    },
    "Diagnosis": {
        "bg": "#ffedd5",
        "border": "#f97316",
        "font": "#9a3412",
        "level": 1
    },
    "Exam": {
        "bg": "#fef9c3",
        "border": "#eab308",
        "font": "#854d0e",
        "level": 1
    },
    "Anatomy": {
        "bg": "#dcfce7",
        "border": "#22c55e",
        "font": "#166534",
        "level": 2
    },
    "ExamResult": {
        "bg": "#f3e8ff",
        "border": "#a855f7",
        "font": "#581c87",
        "level": 2
    },
    "Default": {
        "bg": "#f1f5f9",
        "border": "#94a3b8",
        "font": "#334155",
        "level": 1
    }
}

EDGE_THEMES = {
    "PRESENTS_WITH": {"color": "#dc2626", "dashes": False},
    "DENIES_SYMPTOM": {"color": "#7f1d1d", "dashes": True},
    "DIAGNOSED_WITH": {"color": "#ea580c", "dashes": False},
    "RULED_OUT": {"color": "#9a3412", "dashes": True},
    "UNDERWENT_EXAM": {"color": "#ca8a04", "dashes": False},
    "HAS_RESULT": {"color": "#7c3aed", "dashes": False},
    "HAS_LAB_VALUE": {"color": "#9333ea", "dashes": False},
    "HAS_SIZE": {"color": "#c026d3", "dashes": False},
    "LOCATED_IN": {"color": "#16a34a", "dashes": [4, 4]},
    "Default": {"color": "#64748b", "dashes": False}
}

PYVIS_HIERARCHICAL_OPTIONS = {
    "layout": {
        "hierarchical": {
            "enabled": True,
            "direction": "LR",
            "sortMethod": "directed",
            "levelSeparation": 280,
            "nodeSpacing": 100,
            "treeSpacing": 120,
            "blockShifting": True,
            "edgeMinimization": True,
            "parentCentralization": True
        }
    },
    "physics": {
        "hierarchicalRepulsion": {
            "nodeDistance": 140,
            "centralGravity": 0.0,
            "springLength": 100,
            "springStrength": 0.01,
            "damping": 0.1
        },
        "solver": "hierarchicalRepulsion"
    },
    "interaction": {
        "dragNodes": True,
        "zoomView": True,
        "hover": True
    }
}


def sanitize_subgraph(df_sub_edges, patient_id):
    grouped = (
        df_sub_edges.groupby(["source_id", "target_id", "relation"])
        .size()
        .reset_index(name="count")
    )

    resolved_rows = []
    pairs = grouped.groupby(["source_id", "target_id"])

    for (src, tgt), group in pairs:
        rels = set(group["relation"])
        if "DIAGNOSED_WITH" in rels and "RULED_OUT" in rels:
            group = group[group["relation"] != "RULED_OUT"]
        if "PRESENTS_WITH" in rels and "DENIES_SYMPTOM" in rels:
            group = group[group["relation"] != "DENIES_SYMPTOM"]
        resolved_rows.append(group)

    clean_edges = pd.concat(resolved_rows, ignore_index=True) if resolved_rows else pd.DataFrame()

    organs_with_disease = clean_edges.loc[clean_edges["relation"] == "LOCATED_IN", "target_id"].unique()
    mask_redundant = (
        (clean_edges["source_id"] == patient_id) &
        (clean_edges["target_id"].isin(organs_with_disease)) &
        (clean_edges["relation"] == "ASSOCIATED_WITH")
    )
    clean_edges = clean_edges[~mask_redundant]

    return clean_edges


def generate_interactive_patient_kg(
    patient_id=None,
    nodes_path=DEFAULT_NODES_PATH,
    edges_path=DEFAULT_EDGES_PATH,
    output_html=None
):
    if not os.path.exists(nodes_path) or not os.path.exists(edges_path):
        print(f"Error: Missing '{nodes_path}' or '{edges_path}'.")
        return None

    df_nodes = pd.read_csv(nodes_path)
    df_edges = pd.read_csv(edges_path)

    available_patients = df_nodes.loc[df_nodes["type"] == "Patient", "node_id"].dropna().unique().tolist()
    if not available_patients:
        print("No patient nodes found in nodes file.")
        return None

    if patient_id is None:
        patient_full_id = random.choice(available_patients)
        print(f"No patient specified. Selected random patient: {patient_full_id}")
    else:
        patient_full_id = patient_id if str(patient_id).startswith("Patient_") else f"Patient_{patient_id}"
        if patient_full_id not in available_patients:
            matches = [p for p in available_patients if str(patient_id).lower() in p.lower()]
            if matches:
                patient_full_id = matches[0]
                print(f"Matched partial patient ID: {patient_full_id}")
            else:
                print(f"Patient '{patient_id}' not found.")
                print(f"Sample available IDs: {available_patients[:5]}")
                return None

    direct_targets = df_edges.loc[df_edges["source_id"] == patient_full_id, "target_id"].unique()
    connected_ids = set(direct_targets).union({patient_full_id})

    sub_edges = df_edges[
        df_edges["source_id"].isin(connected_ids) & df_edges["target_id"].isin(connected_ids)
    ].copy()

    sub_edges = sanitize_subgraph(sub_edges, patient_full_id)

    active_nodes = set(sub_edges["source_id"]).union(set(sub_edges["target_id"]))
    sub_nodes = df_nodes[df_nodes["node_id"].isin(active_nodes)]

    if sub_nodes.empty:
        print(f"No active connected nodes for {patient_full_id}.")
        return None

    if output_html is None:
        clean_name = patient_full_id.replace("Patient_", "").lower()
        output_html = str(DATA_PROCESSED / f"03_interactive_graph_{clean_name}.html")

    net = Network(height="750px", width="100%", bgcolor="#ffffff", font_color="#0f172a", directed=True)

    for _, row in sub_nodes.iterrows():
        n_id = str(row["node_id"])
        n_type = row.get("type", "Default")
        theme = NODE_THEMES.get(n_type, NODE_THEMES["Default"])
        raw_label = str(row.get("label", n_id))
        attrs = str(row.get("attributes", ""))

        is_patient = (n_type == "Patient")

        if is_patient:
            meta_lines = attrs.replace("; ", "\n")
            display_label = f"PATIENT\n{raw_label}\n{meta_lines}"
        elif n_type == "ExamResult":
            display_label = f"Result\n{raw_label}"
        else:
            display_label = f"{raw_label}\n({n_type})"

        tooltip = f"""
        <div style="font-family: Arial, sans-serif; font-size: 12px; padding: 6px;">
            <b>ID:</b> {n_id}<br>
            <b>Type:</b> {n_type}<br>
            <b>Attributes:</b> {html.escape(attrs)}
        </div>
        """

        net.add_node(
            n_id=n_id,
            label=display_label,
            title=tooltip,
            shape="box",
            level=theme["level"],
            color=theme["border"],
            font={"color": theme["font"]},
            background=theme["bg"],
            borderWidth=2,
            margin=10,
            fontSize=16,
            mass=3,
            physics=False,
        )

    for _, row in sub_edges.iterrows():
        src = str(row["source_id"])
        dst = str(row["target_id"])
        rel = str(row["relation"])
        edge_theme = EDGE_THEMES.get(rel, EDGE_THEMES["Default"])
        label = rel

        net.add_edge(
            src,
            dst,
            label=label,
            color=edge_theme["color"],
            dashes=edge_theme["dashes"],
            font={"color": edge_theme["color"], "size": 12},
            arrows="to",
            smooth={"type": "dynamic"},
            width=2,
        )

    output_html = str(DATA_PROCESSED / output_html) if not os.path.isabs(output_html) else output_html
    net.write_html(output_html)
    print(f"Interactive graph saved to: {output_html}")
    return output_html


def main():
    discovered_terms = build_reference_vocabulary()
    print(f"Unique discovered terms: {len(discovered_terms)}")

    df_nodes, df_edges = process_cases_to_graph(discovered_terms)
    if df_nodes.empty:
        print("No graph data generated from case texts.")
        return

    df_nodes.to_csv(DATA_PROCESSED / "03_nodes.csv", index=False)
    df_edges.to_csv(DATA_PROCESSED / "03_edges.csv", index=False)
    print(f"Generated {len(df_nodes)} nodes and {len(df_edges)} edges.")

    generate_interactive_patient_kg(
        patient_id=None,
        nodes_path=DEFAULT_NODES_PATH,
        edges_path=DEFAULT_EDGES_PATH,
        output_html=str(DATA_PROCESSED / "03_interactive_graph.html"),
    )


if __name__ == "__main__":
    main()

