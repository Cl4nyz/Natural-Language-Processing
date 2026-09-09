# Primeira entrega

Esta pasta contém a base do pipeline de NLP desenvolvida para a primeira entrega.
A implementação atual processa cinco casos clínicos e extrai medições, candidatos
temporais, candidatos a intervalos de referência e uma primeira camada de
entidades clínicas mediante gazetteers, expressões regulares e regras explícitas.

## Estrutura

```text
project1/
├── run_project1.py       execução da entrega
├── pipeline.py           carga, validação e geração dos resultados
├── nlp_utils.py          limpeza, sentenças, tokens e medições
├── clinical_rules.py     extração clínica e relações
├── gazetteers.json       termos clínicos e formas normalizadas
├── tests/                testes automatizados
├── results/              resultados preservados por iteração
└── docs/                 relatório técnico
```

## Execução

Os comandos devem ser executados a partir da raiz do repositório:

```powershell
.\.venv\Scripts\python.exe -m project1.run_project1
.\.venv\Scripts\python.exe -m unittest discover -s project1/tests -v
```

O arquivo `main.py` da raiz não é utilizado.

Os termos dos gazetteers podem ser consultados em `gazetteers.json`. O arquivo
agrupa por tipo cada expressão procurada no texto e sua forma normalizada.

## Resultado atual

- 5 casos processados;
- 88 sentenças;
- 2.097 tokens;
- 44 medições;
- 19 candidatos temporais;
- 3 candidatos a intervalos de referência;
- 207 entidades clínicas;
- 256 nós;
- 58 relações clínicas baseadas em padrões explícitos.

Os offsets usam intervalos `[start_char, end_char)` sobre o texto original.
Os candidatos temporais e de referência não são transformados em nós do grafo.
O estado atual corresponde à Iteração 2 e está salvo em `results/iteration_2/`.
As pastas `iteration_1/` e `post_iteration_1/` conservam as saídas anteriores.
