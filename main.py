from pathlib import Path
import re

import csv
import pandas as pd

CASES = Path('sample/cases.csv')

def print_matches_and_groups(matches, title=None):
    if title is not None:
        print(f'{'='*30} {title.upper()} {'='*30}')
    for match_num, match in enumerate(matches, start=1):
        print(f'Match {match_num} was found at {match.start()}-{match.end()}: {match.group()}')

        for group_num, group in enumerate(match.groups(), start=1):
            print(f'    Group {group_num} was found at {match.start(group_num)}-{match.end(group_num)}: {group}')

def apply_regex(text):
    patterns = {
        'numbers': r'(\d+)\.(\d+)',
        'exams': r'\w+copy',
        'body parts': r'bowel|stomach|pancreas',
        'problems': r'nausea|constipation|cyst\w*'
    }
    for title, reg in patterns.items():
        pattern = re.compile(reg)
        matches = pattern.finditer(text)
        print_matches_and_groups(matches, title)

def byte_pair_encoding(text, k=200):
    corpus = list(text)
    for epoch in range(k):
        print(len(corpus))
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
        print(f'Most frequent pair in epoch {epoch}: "{max_pair}"')
    for c in corpus:
        print(f"{c}", end='|')
    print('\n')
        # TODO avoid collisions (ex. a a a -> aa a or a aa?)
    return vocabulary, corpus

# Tokenização por palavra
def regex_tokenize(text):
    tokenizer = re.compile(
        r'''(?x)
        \d+(?:[\.,]\d+)?\s*(?:mg/L|U/L|ng/ml|iu/ml|cm|mm|m)
        | \d+-\d+\s*(?:U/L|mg/L)?
        | \d+(?:\.\d+)?
        | [A-Z][a-zA-Z0-9-]*-\d+
        | \b[a-zA-Z]+-[a-zA-Z]+\b
        | \w+
        | [^\w\s]
        '''
    )
    return tokenizer.findall(text)


def main():
    df = pd.read_csv(CASES, header=0)
    # text = df.loc[0, 'case_text']
    # print('-'*30)
    # print(text)
    # print('-'*30)
    # apply_regex(text)
    # byte_pair_encoding(text)

    # Cria uma nova coluna no DataFrame com os tokens extraídos
    df['tokens'] = df['case_text'].apply(regex_tokenize)
    print(df['tokens'].iloc[0][:15])


if __name__ == '__main__':
    main()