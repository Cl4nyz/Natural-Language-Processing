from pathlib import Path
import re

import csv
import pandas as pd
import networkx as nx
import nltk
from nltk.corpus import stopwords
from nltk.collocations import BigramCollocationFinder
from nltk.metrics import BigramAssocMeasures

CASES = Path('sample/cases.csv')
METADATA = Path('sample/metadata.csv')

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
    for title, reg in patterns.items():
        pattern = re.compile(reg)
        # matches = pattern.finditer(text)
        # print_matches_and_groups(matches, title)
        matches[title] = list(set(pattern.findall(text)))
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

def build_pmi_graph(tokens, window_size, min_freq, min_pmi):
    finder = BigramCollocationFinder.from_words(tokens, window_size=window_size)
    
    finder.apply_freq_filter(min_freq)
    
    pmi_scores = finder.score_ngrams(BigramAssocMeasures.pmi)
    
    G = nx.Graph()
    
    for (node1, node2), pmi in pmi_scores:
        if pmi >= min_pmi:
            G.add_edge(node1, node2, weight=pmi)
            
    return G

def main():
    cases_df = pd.read_csv(CASES, header=0)
    metadata_df = pd.read_csv(METADATA, header=0)
    concat_text = " ".join(cases_df['case_text'].iloc[:60].dropna().astype(str))
    # print(concat_text)
    text = cases_df.loc[23, 'case_text']
    text = concat_text
    # print('-'*30)
    # print(text)
    # print('-'*30)
    # apply_regex(text)
    # byte_pair_encoding(concat_text, k=400)

    # Cria uma nova coluna no DataFrame com os tokens extraídos
    # cases_df['tokens'] = cases_df['case_text'].apply(regex_tokenize)
    remov_chars = [chr(i) for i in range(33, 48)] + [chr(i) for i in range(58, 65)] + [chr(i) for i in range(123, 127)]
    remov_chars.remove("'")
    remov_chars.remove(".")
    remov_chars.remove("-")
    print(remov_chars)
    for c in remov_chars:
        text = text.replace(c, ' ')
    tokens = regex_tokenize(text)

    nltk.download('stopwords')
    stop_words = set(stopwords.words('english'))
    stop_words.discard('no')

    tokens = [t for t in tokens if t.lower() not in stop_words]
    tokens = list(set(tokens))
    # print(tokens)
    # print(len(set(tokens)))

    knowledge_graph = build_pmi_graph(
        tokens=tokens, 
        window_size=5, 
        min_freq=1, 
        min_pmi=0.5
    )

    print(len(knowledge_graph.edges()))

    for edge in sorted(knowledge_graph.edges(data=True), key=lambda x: x[2]['weight'], reverse=True)[:20]:
        print(edge)

    # All tokens
    print(sorted(tokens))

    # Tokens separated by type (number, acronym, etc.)
    matches = apply_regex(text)
    for title, match_list in matches.items():
        print(f'{"="*30} {title.upper()} {"="*30}')
        print(sorted(match_list))

    # Keywords from metadata
    # unique_items = set(metadata_df['keywords'].str.strip('[]').str.split(', ').explode())
    # print(unique_items)
    


if __name__ == '__main__':
    main()