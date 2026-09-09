# Primeira entrega

Esta pasta contém a base do pipeline de NLP desenvolvida para a primeira entrega.
A implementação atual processa cinco casos clínicos e extrai medições mediante
expressões regulares.

## Estrutura

```text
project1/
├── run_project1.py       execução da entrega
├── pipeline.py           carga, validação e geração dos resultados
├── nlp_utils.py          limpeza, sentenças, tokens e medições
├── tests/                testes automatizados
├── results/iteration_1/  arquivos CSV, JSON e Mermaid
└── docs/                 relatório técnico
```

## Execução

Os comandos devem ser executados a partir da raiz do repositório:

```powershell
.\.venv\Scripts\python.exe -m project1.run_project1
.\.venv\Scripts\python.exe -m unittest discover -s project1/tests -v
```

O arquivo `main.py` da raiz não é utilizado.

## Resultado atual

- 5 casos processados;
- 88 sentenças;
- 2.097 tokens;
- 48 medições;
- 53 nós preliminares;
- nenhuma relação clínica, pois essa etapa ainda não foi aprovada.

Os offsets usam intervalos `[start_char, end_char)` sobre o texto original.
