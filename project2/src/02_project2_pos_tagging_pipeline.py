import json
from pathlib import Path
import re
from collections import defaultdict
import pandas as pd
import networkx as nx
import nltk
from nltk.corpus import stopwords
from nltk import pos_tag, RegexpParser, sent_tokenize

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Garante downloads necessários do NLTK
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)
nltk.download('averaged_perceptron_tagger_eng', quiet=True)
nltk.download('stopwords', quiet=True)

# Caminhos de arquivos
CASES_FILE = Path('sample/cases.csv') if Path('sample/cases.csv').exists() else Path('data/raw/cases.csv')
VOCAB_FILE = Path('src/project1/medical_vocab.json') if Path('src/project1/medical_vocab.json').exists() else Path('src/medical_vocab.json')
OUTPUT_FILE = Path('data/processed/02-project2-pos-tagging-graph.md')

stop_words = set(stopwords.words('english'))
stop_words.discard('no')

# Padrões Genéricos de Regex
REGEX_PATTERNS = {
    "patient_info": re.compile(r'\b(\d+)[ -]?(?:year[ -]old|yo)\s+(man|woman|female|male|patient)\b', re.IGNORECASE),
    "measurement": re.compile(r'\b\d+(?:\.\d+)?\s*(?:cm|mm|m)(?:\s*x\s*\d+(?:\.\d+)?\s*(?:cm|mm|m))*\b', re.IGNORECASE),
    "lab_value": re.compile(r'\b\d+(?:[\.,]\d+)?\s*(?:ng/ml|iu/ml|mg/L|U/L|%)\b', re.IGNORECASE),
    "tokens": re.compile(r'\b\d+(?:\.\d+)?\s*(?:cm|mm|m|ng/ml|iu/ml|mg/L|U/L|%)\b|\b[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*\b|[^\w\s]')
}

PREPOSITIONS_SPATIAL = ["between", "arising from", "adherent to", "adjacent to", "in", "located at", "abutting", "encasing"]
VERBS_REVEAL = ["demonstrating", "revealed", "showed", "noted", "show", "confirmed"]


# ==============================================================================
# 1. ESPAÇO VETORIAL DE N-GRAMS E CLASSIFICAÇÃO COM MACHINE LEARNING
# ==============================================================================
def build_ngram_vector_space():
    """
    Constrói o espaço vetorial contínuo baseado em N-grams (TF-IDF de unigramas e bigramas).
    Mapeia os termos conceituais de cada categoria médica para um espaço de características.
    Dessa forma, a classificação de novas entidades é feita por proximidade vetorial
    (distância de cosseno / vizinho mais próximo), sem busca exata de string em dicionário.
    """
    with open(VOCAB_FILE, 'r', encoding='utf-8') as f:
        vocab = json.load(f)

    train_terms = []
    train_categories = []

    for category, terms in vocab.items():
        for term in terms:
            train_terms.append(term.lower())
            train_categories.append(category)

    # Espaço vetorial TF-IDF com N-grams de palavras (unigramas e bigramas)
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), analyzer='word', lowercase=True)
    X_train_vectors = vectorizer.fit_transform(train_terms)

    return vectorizer, X_train_vectors, train_categories


# Inicializa o espaço vetorial de N-grams
VECTORIZER, X_VOCAB, TRAIN_CATEGORIES = build_ngram_vector_space()


def clean_phrase(phrase):
    """Remove preposições e ruídos residuais no final do sintagma nominal."""
    cleaned = phrase.strip()
    trailing_noise = re.compile(r'\s+(?:secondary|to|of|in|with|for|from|at|by|on|and|or)$', re.IGNORECASE)
    while trailing_noise.search(cleaned):
        cleaned = trailing_noise.sub('', cleaned).strip()
    return cleaned


def classify_entity_vector_space(entity_str, threshold=0.35):
    """
    Classifica entidades projetando o texto no Espaço Vetorial de N-grams.
    Utiliza Similaridade de Cosseno (Nearest Neighbor no espaço vetorial):
    - Se a similaridade com o protótipo médico mais próximo for >= threshold,
      atribui a categoria clínica predita.
    - Termos não médicos (ex: 'three months', 'Figure 1') têm similaridade < threshold
      e são automaticamente rotulados como 'Unknown'.
    """
    entity_lower = clean_phrase(entity_str).lower()

    # 1. Valores Laboratoriais via Regex
    if REGEX_PATTERNS["lab_value"].search(entity_lower):
        return "ExamResult"

    if len(entity_lower) <= 2 or entity_lower.isdigit():
        return "Unknown"

    # 2. Projeção no Espaço Vetorial de N-grams
    entity_vector = VECTORIZER.transform([entity_lower])
    cosine_sims = cosine_similarity(entity_vector, X_VOCAB)[0]

    best_idx = cosine_sims.argmax()
    best_similarity = cosine_sims[best_idx]

    # Atribuição probabilística no espaço vetorial
    if best_similarity >= threshold:
        return TRAIN_CATEGORIES[best_idx]

    return "Unknown"


# ==============================================================================
# 2. EXTRAÇÃO DE SINTAGMAS NOMINAIS (POS-TAGGING CHUNKING)
# ==============================================================================
def extract_noun_chunks(tokens):
    """Extrai sintagmas nominais (NPs) e os classifica via espaço vetorial de N-grams."""
    tagged_tokens = pos_tag(tokens)
    grammar = r"NP: {<DT>?<JJ.*|CD|NN.*>+(?:\s+<CC>\s+<JJ.*|CD|NN.*>+)*}"
    chunk_parser = RegexpParser(grammar)
    tree = chunk_parser.parse(tagged_tokens)

    extracted = []
    seen = set()

    for subtree in tree.subtrees():
        if subtree.label() == 'NP':
            words = [w for w, t in subtree.leaves() if w.lower() not in stop_words]
            phrase = clean_phrase(" ".join(words))

            if phrase and len(phrase) > 2 and phrase.lower() not in seen:
                category = classify_entity_vector_space(phrase)
                if category != "Unknown":
                    extracted.append((phrase, category))
                    seen.add(phrase.lower())

    return extracted


# ==============================================================================
# 3. CONSTRUÇÃO DO GRAFO DE CONHECIMENTO
# ==============================================================================
def build_generic_graph(text):
    """Constrói o grafo clínico conectando as entidades extraídas via N-grams e ML."""
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

            # Regras de Conexão baseadas na categoria e sintaxe da frase
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


# ==============================================================================
# 4. TABELAS E DIAGRAMA MERMAID
# ==============================================================================
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


# ==============================================================================
# 5. EXECUÇÃO PRINCIPAL
# ==============================================================================
def main():
    try:
        cases_df = pd.read_csv(CASES_FILE, header=0)
        text = cases_df.loc[1]['case_text']

        print("=== PROJETO 2: Grafo Clínico com Espaço Vetorial de N-Grams e ML ===")
        print(f"Lendo caso de: {CASES_FILE}")

        knowledge_graph = build_generic_graph(text)

        df_nodes, node_map = generate_node_table(knowledge_graph)
        df_edges = generate_edge_table(knowledge_graph, node_map)
        mermaid_code = generate_mermaid_graph(knowledge_graph, node_map)

        print("\n--- TABELA DE NÓS (ENTIDADES CLÍNICAS) ---")
        print(df_nodes.to_markdown(index=False))
        print("\n" + "="*60 + "\n")

        print("--- TABELA DE ARESTAS (RELAÇÕES CLÍNICAS) ---")
        print(df_edges.to_markdown(index=False))
        print("\n" + "="*60 + "\n")

        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(mermaid_code)

        cross_edges = sum(1 for u, v in knowledge_graph.edges() if u != "P1" and v != "P1")
        print(f"Diagrama Mermaid salvo em: {OUTPUT_FILE.resolve()}")
        print(f"Total de Nós: {knowledge_graph.number_of_nodes()}")
        print(f"Total de Arestas: {knowledge_graph.number_of_edges()}")
        print(f"Arestas entre Entidades (Cross-entity relations): {cross_edges}")

    except Exception as e:
        print(f"Erro ao executar o pipeline do Projeto 2: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
