import json
from pathlib import Path
import re
import pandas as pd
import networkx as nx
import nltk
from nltk.corpus import stopwords
from nltk import pos_tag, RegexpParser, sent_tokenize
from collections import defaultdict

nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)
nltk.download('averaged_perceptron_tagger_eng', quiet=True)
nltk.download('stopwords', quiet=True)

CASES = Path('sample/cases.csv')
OUTPUT_FILE = Path('pos-tagging-approach/graph.md')
VOCAB_FILE = Path('pos-tagging-approach/medical_vocab.json')

stop_words = set(stopwords.words('english'))
stop_words.discard('no')

# Padrões Genéricos de Regex
REGEX_PATTERNS = {
    "patient_info": re.compile(r'\b(\d+)[ -]?(?:year[ -]old|yo)\s+(man|woman|female|male|patient)\b', re.IGNORECASE),
    "measurement": re.compile(r'\b\d+(?:\.\d+)?\s*(?:cm|mm|m)(?:\s*x\s*\d+(?:\.\d+)?\s*(?:cm|mm|m))*\b', re.IGNORECASE),
    "lab_value": re.compile(r'\b\d+(?:[\.,]\d+)?\s*(?:ng/ml|iu/ml|mg/L|U/L|%)\b', re.IGNORECASE),
    "tokens": re.compile(r'\b\d+(?:\.\d+)?\s*(?:cm|mm|m|ng/ml|iu/ml|mg/L|U/L|%)\b|\b[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*\b|[^\w\s]')
}

PREPOSITIONS_SPATIAL = ["between", "arising from", "adherent to", "adjacent to", "in", "located at"]
VERBS_REVEAL = ["demonstrating", "revealed", "showed", "noted", "show", "confirmed"]

def load_medical_vocab():
    """Carrega o vocabulário médico de um arquivo JSON externo se disponível."""
    with open(VOCAB_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)
    
MEDICAL_VOCAB = load_medical_vocab()

def classify_entity_generically(entity_str):
    """Classifica entidades de forma genérica usando o vocabulário e padrões de regex."""
    entity_lower = entity_str.lower()
    
    # 1. Valores Laboratoriais
    if REGEX_PATTERNS["lab_value"].search(entity_lower):
        return "ExamResult"
    
    # 2. Busca no Vocabulário (ordena por tamanho decrescente para pegar termos compostos primeiro)
    for category, terms in MEDICAL_VOCAB.items():
        sorted_terms = sorted(terms, key=len, reverse=True)
        for term in sorted_terms:
            if re.search(r'\b' + re.escape(term) + r'\b', entity_lower):
                return category
                
    return "Unknown"

def extract_noun_chunks(tokens):
    """Extrai sintagmas nominais (NPs) incluindo conjunções (CC) e numerais."""
    tagged_tokens = pos_tag(tokens)
    grammar = r"NP: {<DT>?<JJ.*|CD|NN.*>+(?:\s+<CC>\s+<JJ.*|CD|NN.*>+)*}"
    chunk_parser = RegexpParser(grammar)
    tree = chunk_parser.parse(tagged_tokens)
    
    extracted = []
    for subtree in tree.subtrees():
        if subtree.label() == 'NP':
            words = [w for w, t in subtree.leaves() if w.lower() not in stop_words]
            phrase = " ".join(words).strip()
            if phrase:
                category = classify_entity_generically(phrase)
                extracted.append((phrase, category))
                
    return extracted

def build_generic_graph(text):
    G = nx.DiGraph()
    patient_id = "P1"
    G.add_node(patient_id, entity_type="Patient", label="Patient")
    
    sentences = sent_tokenize(text)
    last_exam = None
    last_finding = None
    
    for sentence in sentences:
        sentence_lower = sentence.lower()
        
        # 1. Captura dinâmica de informações do Paciente
        patient_match = REGEX_PATTERNS["patient_info"].search(sentence)
        if patient_match:
            age, gender = patient_match.groups()
            G.nodes[patient_id]['label'] = f"{age}yo {gender.capitalize()} Patient"

        # 2. Captura dinâmica de medições/tamanhos na frase
        size_match = REGEX_PATTERNS["measurement"].search(sentence_lower)
        current_size = size_match.group(0) if size_match else None

        tokens = REGEX_PATTERNS["tokens"].findall(sentence)
        entities = extract_noun_chunks(tokens)
        
        for entity_text, entity_type in entities:
            if entity_type in ["Unknown", "Patient"]:
                continue

            G.add_node(entity_text, entity_type=entity_type, label=entity_text)
            
            # Regras Genéricas de Conexão baseadas na categoria e sintaxe da frase
            if entity_type == "Symptom":
                G.add_edge(patient_id, entity_text, label="PRESENTS_WITH")
                
            elif entity_type == "Exam":
                G.add_edge(patient_id, entity_text, label="UNDERWENT_EXAM")
                last_exam = entity_text
                
            elif entity_type == "Finding":
                last_finding = entity_text
                if current_size:
                    G.nodes[entity_text]['size'] = current_size
                    
                if last_exam and any(verb in sentence_lower for verb in VERBS_REVEAL):
                    G.add_edge(last_exam, entity_text, label="REVEALS")
                else:
                    G.add_edge(patient_id, entity_text, label="HAS_FINDING")
                    
            elif entity_type == "Anatomy":
                # Se houver preposição espacial e um achado prévio na mesma frase
                if last_finding and any(prep in sentence_lower for prep in PREPOSITIONS_SPATIAL):
                    G.add_edge(last_finding, entity_text, label="LOCATED_AT")
                else:
                    G.add_edge(patient_id, entity_text, label="RELATED_ANATOMY")
                    
            elif entity_type == "ExamResult":
                if last_exam:
                    G.add_edge(last_exam, entity_text, label="HAS_RESULT")
                    
            elif entity_type == "Diagnosis":
                G.add_edge(patient_id, entity_text, label="DIAGNOSED_WITH")
                if last_finding:
                    G.add_edge(last_finding, entity_text, label="SUGGESTS")
                    
            elif entity_type == "Treatment":
                G.add_edge(patient_id, entity_text, label="TREATED_WITH")
                if last_finding:
                    G.add_edge(entity_text, last_finding, label="TARGETS")
                    
            elif entity_type == "Outcome":
                G.add_edge(patient_id, entity_text, label="HAS_OUTCOME")

    return G

def generate_node_table(knowledge_graph):
    rows = []
    type_counters = defaultdict(int)
    node_id_mapping = {}

    for node, data in knowledge_graph.nodes(data=True):
        entity_type = data.get("entity_type", "Unknown")
        label = data.get("label", str(node))
        
        if node == "P1":
            node_id = "P1"
        else:
            prefix = entity_type[0].upper() if entity_type != "Unknown" else "U"
            type_counters[prefix] += 1
            node_id = f"{prefix}{type_counters[prefix]}"
        
        node_id_mapping[node] = node_id
        
        ignored_keys = {"entity_type", "label"}
        attributes = [f"{k}={v}" for k, v in data.items() if k not in ignored_keys]
        
        rows.append({
            "node_id": node_id,
            "type": entity_type,
            "label": label.capitalize(),
            "attributes": "; ".join(attributes)
        })

    return pd.DataFrame(rows), node_id_mapping

def generate_edge_table(knowledge_graph, node_id_mapping):
    rows = []
    for i, (u, v, data) in enumerate(knowledge_graph.edges(data=True), start=1):
        source_id = node_id_mapping.get(u, "U0")
        target_id = node_id_mapping.get(v, "U0")
        relation = data.get("label", "RELATED_TO").upper()
        
        rows.append({
            "edge_id": f"e{i}",
            "source_id": source_id,
            "target_id": target_id,
            "relation": relation,
            "attributes": ""
        })
        
    return pd.DataFrame(rows)

def generate_mermaid_graph(knowledge_graph, node_id_mapping):
    mermaid_lines = ["```mermaid", "flowchart LR"]
    mermaid_lines.extend([
        "  classDef patient fill:#fef3c7,stroke:#d97706,color:#000",
        "  classDef symptom fill:#fee2e2,stroke:#b91c1c,color:#000",
        "  classDef finding fill:#fce7f3,stroke:#be185d,color:#000",
        "  classDef exam fill:#dbeafe,stroke:#1d4ed8,color:#000",
        "  classDef examresult fill:#cffafe,stroke:#0e7490,color:#000",
        "  classDef anatomy fill:#e0e7ff,stroke:#4338ca,color:#000",
        "  classDef diagnosis fill:#dcfce7,stroke:#15803d,color:#000",
        "  classDef treatment fill:#fef9c3,stroke:#a16207,color:#000",
        "  classDef outcome fill:#f3e8ff,stroke:#7e22ce,color:#000"
    ])
    
    nodes_str = []
    for node, data in knowledge_graph.nodes(data=True):
        node_id = node_id_mapping.get(node, "U0")
        entity_type = data.get("entity_type", "unknown").lower()
        if entity_type == "unknown":
            continue
            
        raw_label = data.get("label", str(node)).capitalize()
        if 'size' in data:
            raw_label += f"<br/>({data['size']})"
            
        nodes_str.append(f'  {node_id}["{raw_label}"]:::{entity_type}')
        
    mermaid_lines.extend([""] + nodes_str + [""])
    
    for u, v, data in knowledge_graph.edges(data=True):
        source_id = node_id_mapping.get(u)
        target_id = node_id_mapping.get(v)
        relation = data.get("label", "RELATED_TO").upper()
        
        if source_id and target_id:
            mermaid_lines.append(f"  {source_id} -->|{relation}| {target_id}")
            
    mermaid_lines.append("```")
    return "\n".join(mermaid_lines)

def main():
    try:
        cases_df = pd.read_csv(CASES, header=0)
        text = cases_df.loc[1]['case_text'] # Caso analisado do csv
        
        knowledge_graph = build_generic_graph(text)
        
        df_nodes, node_map = generate_node_table(knowledge_graph)
        df_edges = generate_edge_table(knowledge_graph, node_map)
        mermaid_code = generate_mermaid_graph(knowledge_graph, node_map)
        
        print(df_nodes.to_markdown(index=False))
        print("\n" + "="*50 + "\n")
        print(df_edges.to_markdown(index=False))
        print("\n" + "="*50 + "\n")
        
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(mermaid_code)
            
        print(f"Diagrama Mermaid salvo em: {OUTPUT_FILE.resolve()}")
        
    except Exception as e:
        print(f"Erro ao executar o pipeline: {e}")

if __name__ == '__main__':
    main()