# Projeto 2: Classificação Vetorial de Entidades com N-Grams e Machine Learning

Este projeto aprimora o pipeline do **Projeto 1** ([`src/project1/02_pos_tagging_pipeline.py`](../project1/02_pos_tagging_pipeline.py)) substituindo a busca exata de strings por um **Espaço Vetorial baseado em N-grams** e **Machine Learning (Nearest Neighbors com Similaridade de Cosseno)**, mantendo 100% de conformidade com as restrições do edital (sem Transformers e sem embeddings densos proibidos como LLMs).

---

## 1. Ideia Central da Abordagem

No Projeto 1, a função `classify_entity_generically()` fazia uma varredura estrita e rígida em um dicionário estático (`medical_vocab.json`). Termos clínicos que não estivessem exatamente no dicionário eram descartados como `Unknown`.

Neste projeto:
1. **Espaço Vetorial Contínuo com N-Grams**:
   * Utilizamos `TfidfVectorizer(ngram_range=(1, 2), analyzer='word')` para projetar os termos conceituais das categorias médicas (`Symptom`, `Exam`, `Finding`, `Anatomy`, `Treatment`, `Diagnosis`, `Outcome`) em um espaço vetorial de N-grams.
2. **Classificação por Proximidade Vetorial (Machine Learning)**:
   * Cada sintagma nominal extraído pelo POS-tagger é vetorizado no mesmo espaço.
   * O algoritmo calcula a **Similaridade de Cosseno** (Nearest Neighbor no espaço vetorial) entre o vetor da entidade e os protótipos de cada categoria.
   * Se a maior similaridade for $\ge 0.35$, a entidade é classificada na categoria médica mais próxima.
   * Termos não clínicos ou ruídos (como *three months*, *Figure 1*) têm similaridade nula ou muito baixa e são automaticamente rotulados como `Unknown`.

---

## 2. O Papel e a Importância do TF-IDF com N-Grams

O **TF-IDF** (*Term Frequency – Inverse Document Frequency*) é a peça central que viabiliza a transição de um sistema baseado em regras cegas para um modelo de aprendizado vetorial fundamentado estatisticamente.

$$\text{TF-IDF} = \text{TF}(t, d) \times \text{IDF}(t)$$

### A Lógica das Duas Forças
1. **TF (Frequência do Termo)**: Mede a relevância local. Se um termo ou bigrama clínico se repete na descrição de uma categoria, ele ganha peso.
2. **IDF (Inverso da Frequência nos Documentos)**: Avalia o grau de especificidade do termo no corpus global:
   $$\text{IDF}(t) = \log\left(\frac{N}{\text{DF}(t) + 1}\right)$$
   * Palavras genéricas e frequentes em todos os contextos recebem IDF próximo de zero, anulando seu impacto.
   * Termos raros e altamente especializados recebem IDF elevado, tornando-se âncoras discriminativas.

### Por Que o TF-IDF é Decisivo no Contexto Clínico?
* **Desempate em Expressões Clínicas Ambíguas**: Em sintagmas compostos como *"pancreatic ductal adenocarcinoma"*, o termo *"pancreatic"* aparece em dezenas de estruturas anatômicas (IDF moderado), enquanto *"adenocarcinoma"* é específico de patologias (IDF alto). O TF-IDF pondera adequadamente esses pesos, direcionando a classificação para **`Diagnosis`** em vez de confundi-la com **`Anatomy`**, resolvendo conflitos que no Projeto 1 dependiam arbitrariamente da ordem de um loop `if/else`.
* **Valorização de Bigramas Clínicos**: Ao configurar `ngram_range=(1, 2)`, pares de palavras como *"cystic lesion"* ou *"bowel obstruction"* passam a ter peso próprio no espaço vetorial, capturando o significado composto que transcende palavras isoladas.
* **Mapeamento Geométrico Contínuo**: O TF-IDF transforma texto em coordenadas numéricas normalizadas ($\vec{v}$). Isso permite calcular a **Similaridade de Cosseno** (o ângulo vetorial entre a frase candidata e os protótipos médicos), produzindo um score contínuo de confiança entre $0.0$ e $1.0$.
* **Filtragem Automática de Ruído**: Sintagmas não médicos extraídos pelo POS-tagger (como *"Figure 1"*, *"three months"*, *"outside surgeon"*) têm representação ortogonal (similaridade de cosseno próxima de $0.00$) em relação aos termos médicos, sendo descartados de forma natural sem necessidade de regras manuais ad-hoc.

---

## 3. Vantagens em Relação ao Projeto 1

* **Generalização sem Dicionário Rígido**: Entidades clínicas complexas e compostas (*postprandial abdominal fullness*, *central mesenteric mass*, *superior mesenteric vessels*, *gastroduodenal outlet obstruction*) são classificadas com sucesso pela proximidade semântica no espaço de N-grams.
* **100% Conforme ao Edital**: Utiliza N-grams e aprendizado clássico de máquina por proximidade de cosseno, respeitando estritamente a proibição de Transformers e embeddings pré-treinados.
* **Simplicidade e Integridade do Pipeline**: Mantém o mesmo fluxo limpo e robusto do Projeto 1 (POS-tagging, tabelas normalizadas de nós/arestas e diagrama Mermaid).

---

## 4. Como Executar

A partir da raiz do repositório:

```bash
./.venv/bin/python src/project2/02_pos_tagging_pipeline.py
```

O grafo resultante será salvo em [`data/processed/02_project2_pos_tagging_graph.md`](../../data/processed/02_project2_pos_tagging_graph.md).
