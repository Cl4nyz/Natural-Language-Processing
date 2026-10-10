from pathlib import Path
import re

import csv
import pandas as pd
import networkx as nx
import nltk
from nltk.corpus import stopwords
from nltk.collocations import BigramCollocationFinder
from nltk.metrics import BigramAssocMeasures
from pyvis.network import Network

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_RAW = BASE_DIR / 'data' / 'raw'
DATA_PROCESSED = BASE_DIR / 'data' / 'processed'

CASES = DATA_RAW / 'cases.csv'
METADATA = DATA_RAW / 'metadata.csv'
OUTPUT_GRAPH = DATA_PROCESSED / '01_medical_knowledge_graph.html'

NUM_CASES = 56

def print_matches_and_groups(matches, title=None):
    if title is not None:
        print(f'{'='*30} {title.upper()} {'='*30}')
    for match_num, match in enumerate(sorted(matches), start=1):
        print(f'Match {match_num} was found at {match.start()}-{match.end()}: {match.group()}')

        for group_num, group in enumerate(match.groups(), start=1):
            print(f'    Group {group_num} was found at {match.start(group_num)}-{match.end(group_num)}: {group}')

def apply_regex(text):
    matches = {}
    patterns = {
        'numbers': r'[\d+]\.[\d+]',
        'exams': r'\w+copy',
        'body parts': r'bowel|stomach|pancreas',
        'problems': r'nausea|constipation|cyst\w*',
        'acronyms': r'\b[A-Z]{2,}\b',
        'numeric_values_with_units': r'\d+(?:[\.,]\d+)?\s*(?:mg/L|U/L|ng/ml|iu/ml|cm|mm|m|%)\b',
        'measurement_ranges': r'\d+-\d+\s*(?:U/L|mg/L)?',
        'isolated_numbers': r'\d+(?:\.\d+)?',
        'alphanumeric_codes': r'[A-Z][a-zA-Z0-9-]*-\d+',
        'hyphenated_words': r'\b[a-zA-Z]+-[a-zA-Z]+\b',
        'words_with_apostrophes': r"\w+'\w*",
        'words_and_acronyms': r'\w+',
        'punctuation_and_symbols': r'[^\w\s]',
    }
    titles = [title for title in patterns.keys()]
    for i, (title, reg) in enumerate(patterns.items()):
        pattern = re.compile(reg)
        # matches = pattern.finditer(text)
        # print_matches_and_groups(matches, title)
        m = set(pattern.findall(text))
        for j in range(i):
            m -= set(matches[titles[j]])
        matches[title] = list(m)
    return matches

def byte_pair_encoding(text, k=200):
    corpus = list(text)
    for epoch in range(k):
        vocabulary = {}
        max_pair = None
        for i in range(len(corpus)-1):
            pair = corpus[i]+corpus[i+1]
            if pair in vocabulary:
                vocabulary[pair].append(i)
            else:
                vocabulary[pair] = [i]
            if max_pair is None or len(vocabulary[pair]) > len(vocabulary[max_pair]):
                max_pair = pair
        for i in vocabulary[max_pair][::-1]:
            corpus[i:i+2] = [corpus[i] + corpus[i+1]]
        # print(f'Most frequent pair in epoch {epoch}: "{max_pair}"')
    for c in corpus:
        print(f"{c}", end='|')
    print('\n')
        # TODO avoid collisions (ex. a a a -> aa a or a aa?)
    return set(vocabulary).union(set(chr(i) for i in range(32,127))), corpus

# Tokenização por palavra
def regex_tokenize(text):
    tokenizer = re.compile(
        r'''(?x)                                              # Flag para permitir comentários no Regex
        \d+(?:[\.,]\d+)?\s*(?:mg/L|U/L|ng/ml|iu/ml|cm|mm|m|%)\b # Valores numéricos + Unidades
        | \d+-\d+\s*(?:U/L|mg/L)?                             # Intervalos de medidas
        | \d+(?:\.\d+)?                                       # Números decimais ou inteiros isolados
        | [A-Z][a-zA-Z0-9-]*-\d+                              # Códigos com hífen e número (ex: CA 19-9, POD-7)
        | \b[a-zA-Z]+-[a-zA-Z]+\b                             # Palavras com hífen
        | \w+'\w*                                             # Palavras com apóstrofo (ex: don't, it's)
        | \w+                                                 # Palavras normais e siglas
        | [^\w\s]                                             # Caracter de pontuação/símbolo individual
        '''
    )
    return tokenizer.findall(text)

def build_pmi_graph(tokens, window_size, min_freq, min_pmi, entity_map=None, default_relation="co_occurs"):
    if entity_map is None:
        entity_map = {}

    finder = BigramCollocationFinder.from_words(tokens, window_size=window_size)
    finder.apply_freq_filter(min_freq)
    pmi_scores = finder.score_ngrams(BigramAssocMeasures.pmi)

    G = nx.Graph()

    for (node1, node2), pmi in pmi_scores:
        if pmi >= min_pmi:
            for node in (node1, node2):
                if node not in G:
                    meta = entity_map.get(node, {})
                    G.add_node(
                        node,
                        entity_type=meta.get("entity_type", "Unknown")
                    )

            G.add_edge(node1, node2, weight=pmi, relation=default_relation)

    return G

def create_html_graph(knowledge_graph, output_file="knowledge_graph.html", top_nodes=-1):
    type_color_map = {
        "problems": "#FF6B6B",                  # Soft red
        "body parts": "#6BCB77",                # Sage green
        "exams": "#4D96FF",                     # Slate blue
        "numbers": "#FFD93D",                   # Amber yellow
        "isolated_numbers": "#F4D160",          # Light gold
        "numeric_values_with_units": "#9B59B6", # Amethyst purple
        "measurement_ranges": "#8E44AD",        # Deep purple
        "alphanumeric_codes": "#1ABC9C",        # Teal
        "acronyms": "#E67E22",                  # Burnt orange
        "words_and_acronyms": "#3498DB",        # Sky blue
        "hyphenated_words": "#16A085",          # Deep teal
        "words_with_apostrophes": "#E74C3C",    # Coral red
        "punctuation_and_symbols": "#95A5A6",   # Cool slate grey
    }
    default_color = "#95A5A6"

    net = Network(
        notebook=False,
        height="80vh",
        width="100%",
        bgcolor="#222222",
        font_color="white",
        select_menu=True,
        filter_menu=True,
    )

    edges = sorted(
        knowledge_graph.edges(data=True),
        key=lambda x: x[2].get("weight", 0),
        reverse=True,
    )
    if top_nodes > 0:
        edges = edges[:top_nodes]

    subgraph = nx.Graph()

    for u, v, data in edges:
        weight = data.get("weight", 0)
        relation = data.get("relation", "relates_to")

        subgraph.add_edge(
            u,
            v,
            weight=weight,
            label=relation,
            title=f"Relation: {relation} PMI: {weight:.2f}",
        )

    for node in subgraph.nodes():
        node_attrs = knowledge_graph.nodes.get(node, {})
        entity_type = node_attrs.get("entity_type", "Unknown")
        color = type_color_map.get(entity_type, default_color)

        tooltip_lines = [
            f"Node: {node}",
            f"Type: {entity_type}",
        ]
        
        for key, val in node_attrs.items():
            if key not in ("entity_type", "label", "title"):
                tooltip_lines.append(f"{key}: {val}")

        subgraph.nodes[node].update(
            {
                "label": str(node),
                "color": color,
                "title": " ".join(tooltip_lines),
            }
        )

    net.from_nx(subgraph)
    # net.show_buttons(filter_=["physics"])
    net.write_html(output_file)
    print(f"Knowledge graph saved to {output_file}")

def main():
    cases_df = pd.read_csv(CASES, header=0)
    concat_text = " ".join(cases_df['case_text'].iloc[:60].dropna().astype(str))
    text = cases_df.loc[0, 'case_text']
    # byte_pair_encoding(concat_text, k=400)

    # Cria uma nova coluna no DataFrame com os tokens extraídos
    # cases_df['tokens'] = cases_df['case_text'].apply(regex_tokenize)
    remov_chars = [chr(i) for i in range(33, 48)] + [chr(i) for i in range(58, 65)] + [chr(i) for i in range(123, 127)]
    remov_chars.remove("'")
    remov_chars.remove(".")
    remov_chars.remove("-")
    for c in remov_chars:
        text = text.replace(c, ' ')
    tokens = regex_tokenize(text)

    nltk.download('stopwords')
    stop_words = set(stopwords.words('english'))
    stop_words.discard('no')

    tokens = [t for t in tokens if t.lower() not in stop_words]
    tokens = list(set(tokens))

    class_tokens = apply_regex(text)
    entity_metadata = {
        val: {'entity_type': class_name}
        for class_name, vals in class_tokens.items()
        for val in vals
    }
    knowledge_graph = build_pmi_graph(
        tokens=tokens,
        window_size=5,
        min_freq=1,
        min_pmi=0.5,
        entity_map=entity_metadata,
        default_relation=":)"
    )
    OUTPUT_GRAPH.parent.mkdir(parents=True, exist_ok=True)
    create_html_graph(knowledge_graph, str(OUTPUT_GRAPH), top_nodes=100)

    # print(len(knowledge_graph.edges()))

    # for edge in sorted(knowledge_graph.edges(data=True), key=lambda x: x[2]['weight'], reverse=True)[:20]:
    #     print(edge)


    # # Tokens separated by type (number, acronym, etc.)
    # matches = apply_regex(text)
    # for title, match_list in matches.items():
    #     print(f'{"="*30} {title.upper()} {"="*30}')
    #     print(sorted(match_list))

    # Keywords from metadata
    metadata_df = pd.read_csv(METADATA, header=0)
    unique_items = set(metadata_df['keywords'].str.strip('[]').str.split(', ').explode())
    # print(unique_items)
    

if __name__ == '__main__':
    main()