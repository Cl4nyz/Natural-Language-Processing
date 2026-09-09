# Primeira entrega

Esta pasta contém a base do pipeline de NLP desenvolvida para a primeira entrega.
A implementação atual processa cinco casos clínicos e extrai medições, candidatos
temporais e candidatos a intervalos de referência mediante expressões regulares.

## Estrutura

```text
project1/
├── run_project1.py       execução da entrega
├── pipeline.py           carga, validação e geração dos resultados
├── nlp_utils.py          limpeza, sentenças, tokens e medições
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

## Resultado atual

- 5 casos processados;
- 88 sentenças;
- 2.097 tokens;
- 44 medições;
- 19 candidatos temporais;
- 3 candidatos a intervalos de referência;
- 49 nós preliminares;
- nenhuma relação clínica, pois essa etapa ainda não foi aprovada.

Os offsets usam intervalos `[start_char, end_char)` sobre o texto original.
Os candidatos temporais e de referência não são transformados em nós do grafo.
O estado atual corresponde ao ajuste posterior à Iteração 1 e está salvo em
`results/post_iteration_1/`; `results/iteration_1/` conserva a saída anterior.
