# REPORTE DE ITERACIÓN 1

## A. Especificación recibida

Se solicitó construir la base reproducible del pipeline únicamente para
`PMC5137649_01`, `PMC11722600_01`, `PMC11783470_01`, `PMC2817501_01` y
`PMC11368112_01`: carga y validación, preservación del texto, limpieza mínima,
segmentación, tokenización, normalización básica, extracción regex de
mediciones, nodos preliminares y una visualización Mermaid por caso.

## B. Arquitectura implementada

- `config.py`: rutas y lista explícita `CASE_IDS`.
- `models.py`: estructuras trazables `Sentence`, `Token` y `Entity`.
- `text_processing.py`: limpieza conservadora, segmentación con offsets,
  tokenización clínica y normalización básica.
- `measurements.py`: reglas localizadas y priorizadas para presión arterial,
  dimensiones, rangos, porcentajes y mediciones simples.
- `pipeline.py`: carga/validación, ejecución, nodos, CSV, JSON y Mermaid.
- `run_iteration1.py`: punto de entrada reproducible; no utiliza `main.py`.
- `tests/`: pruebas de mediciones, negativos, offsets, segmentación y tokens.

Los offsets son intervalos semiabiertos `[start_char, end_char)` sobre
`original_text`, no sobre el texto limpiado. `case_text` nunca se sobrescribe.
Se cargó `metadata.csv` para validar la presencia de los cinco `article_id`, sin
usar sus campos como verdad clínica. `age` y `gender` se preservaron sin cambios.

## C. No implementado

No se implementaron extractores de síntomas, diagnósticos, findings, historia,
medicamentos, tratamientos, procedimientos, outcomes ni anatomía. Tampoco se
implementaron negación, temporalidad semántica, relaciones, coreferencia,
ontologías, POS tagging ni asociación entre una medición y un examen. `edges.csv`
está vacío de manera intencional.

## D. Segmentación

| Caso | Oraciones | Observaciones |
|---|---:|---|
| PMC5137649_01 | 18 | Sin cortes incorrectos observados; se normalizan CR/LF solo en la copia limpia. |
| PMC11722600_01 | 16 | Los segmentos extensos separados por punto y coma permanecen en una oración. |
| PMC11783470_01 | 15 | Decimales como `11.5` y `12.8` no generan cortes. |
| PMC2817501_01 | 12 | `St. Jude` queda protegido mediante lista explícita de abreviaturas. |
| PMC11368112_01 | 27 | Fechas y etiquetas de figura no producen cortes espurios. |

No se observaron errores de segmentación inequívocos en estos cinco casos. La
lista de abreviaturas es deliberadamente pequeña y deberá ampliarse solo con
patrones generales cuando aparezcan nuevos errores.

## E. Tokenización

Funcionó como se esperaba para `EUS-FNA`, `C-reactive`, `12,476.5ng/ml` y
`6cm x 9cm` (`6cm`, `x`, `9cm`). El patrón también conserva `CA 19-9` como un
token cuando aparece literalmente de esa forma. En el corpus aparece `(CA) 19-9`,
por lo que la puntuación impide tratar toda la expresión como un único token.

Resultados discutibles:

- `A-53-year` queda como un token por el formato anómalo de la fuente.
- `12.65 x 109/L` queda fragmentado (`12.65`, `x`, `109`, `/`, `L`), pues su
  interpretación como notación científica no se aprobó.
- `body/tail` queda en tres tokens; resolver expresiones anatómicas no pertenece
  a esta iteración.

## F. Mediciones

Leyenda de reglas: `V` = `measurement_value_unit_v1`, `D` =
`measurement_dimension_v1`, `R` = `measurement_range_v1`, `P` =
`measurement_percentage_v1`, `B` = `measurement_blood_pressure_v1`.

### PMC5137649_01 — 5

| Span | Valor | Unidad | Regla |
|---|---|---|---|
| `6cm` | 6 | cm | V |
| `6cm x 9cm` | [6, 9] | [cm, cm] | D |
| `12,476.5ng/ml` | 12476.5 | ng/mL | V |
| `6iu/ml` | 6 | IU/mL | V |
| `9.5cm x 4.5cm x 2.0cm` | [9.5, 4.5, 2] | [cm, cm, cm] | D |

### PMC11722600_01 — 11

| Span | Valor | Unidad | Regla |
|---|---|---|---|
| `12 h` | 12 | h | V |
| `8800/mm3` | 8800 | /mm3 | V |
| `3800-10,000/mm3` | [3800, 10000] | /mm3 | R |
| `55 mg/L` | 55 | mg/L | V |
| `<5 mg/L` | 5, comparador `<` | mg/L | V |
| `29 mm/h` | 29 | mm/h | V |
| `3-20 mm/h` | [3, 20] | mm/h | R |
| `8 mm` | 8 | mm | V |
| `4 cm` | 4 | cm | V |
| `24 h` | 24 | h | V |
| `6 month` | 6 | month | V |

### PMC11783470_01 — 7

| Span | Valor | Unidad | Regla |
|---|---|---|---|
| `11.5 g/dL` | 11.5 | g/dL | V |
| `12.8%` | 12.8 | % | P |
| `200 ng/mL` | 200 | ng/mL | V |
| `76 mcg/dL` | 76 | mcg/dL | V |
| `<20%` | 20, comparador `<` | % | P |
| `7-mm` | 7 | mm | V |
| `3 months` | 3 | months | V |

### PMC2817501_01 — 10

| Span | Valor | Unidad | Regla |
|---|---|---|---|
| `120/80 mmHg` | 120/80 | mmHg | B |
| `92 beats/min` | 92 | beats/min | V |
| `30 mmHg` | 30 | mmHg | V |
| `20 mmHg` | 20 | mmHg | V |
| `1.8 cm2` | 1.8 | cm2 | V |
| `30%` | 30 | % | P |
| `68 mmHg` | 68 | mmHg | V |
| `90%` | 90 | % | P |
| `29 mm` | 29 | mm | V |
| `21 mm` | 21 | mm | V |

### PMC11368112_01 — 15

| Span | Valor | Unidad | Regla |
|---|---|---|---|
| `38.7 C` | 38.7 | C | V |
| `85%` | 85 | % | P |
| `65 mg/L` | 65 | mg/L | V |
| `55 mm/h` | 55 | mm/h | V |
| `26.12 mg/L` | 26.12 | mg/L | V |
| `39.5 C` | 39.5 | C | V |
| `39.8 C` | 39.8 | C | V |
| `3 x 3 cm` | [3, 3] | [cm, cm] | D |
| `0.2-0.8 cm` | [0.2, 0.8] | cm | R |
| `80 mg per day` | 80 | mg/day | V |
| `60 mg per day` | 60 | mg/day | V |
| `5 mg` | 5 | mg | V |
| `5 mg` | 5 | mg | V |
| `200 mg per day` | 200 | mg/day | V |
| `14 days` | 14 | days | V |

Total: 48 mediciones. Se generaron 53 nodos: cinco `Patient` estructurales y
48 `Measurement`. No se generaron relaciones.

Ejemplos correctos destacados: `120/80 mmHg` se conserva como una sola presión;
`9.5cm x 4.5cm x 2.0cm` como una sola dimensión; `ng/ml` y `ng/mL` comparten la
forma normalizada `ng/mL`. No se vinculó ningún valor a CEA, CRP u otro examen.

## G. False positives observados manualmente

No se confirmó ningún falso positivo inequívoco entre las 48 salidas bajo la
definición sintáctica de “valor + unidad”. En una ejecución intermedia,
`Figure 2c` y `Figure 1c` fueron confundidos con grados C. Se corrigió mediante
la regla general que exige separación antes de `C`; no se añadieron excepciones
por caso.

Los spans temporales `12 h`, `24 h`, `6 month`, `3 months` y `14 days` son
sintácticamente valor + unidad, pero su futura categoría semántica es ambigua.

## H. False negatives y expresiones fuera de cobertura

- `WBC, 12.65 x 109/L`: no detectado. La fuente parece representar notación
  científica, pero normalizar `109` a `10^9` implica una interpretación todavía
  no aprobada.
- `4/6 systolic murmur`: no detectado; razón sin unidad explícita.
- `3-4 degree mitral insufficiency`: no detectado; `degree` no está en el
  vocabulario de unidades aprobado para esta base.
- `INR ... 2.0-3.0`: no detectado; rango sin unidad.
- `3-day history`, `2-day history` y `7th day`: excluidos deliberadamente de la
  regla de medición por su naturaleza temporal/contextual.
- Números escritos con palabras (`two weeks`, `nine months`) quedan fuera del
  extractor numérico actual.

## I. Casos ambiguos

- `30%` es una medición sintáctica válida, pero todavía no se asocia con
  ejection fraction.
- `day 4`, `Figure 1`, `patient 2` y `2014` no se extraen.
- `3-day history` no se extrae, mientras que `14 days` sí se conserva como
  candidato valor + unidad. Hace falta definir si duración será `Measurement`,
  atributo o futura expresión temporal.
- Los límites de referencia se detectan como mediciones independientes
  (`<5 mg/L`, `3-20 mm/h`) sin asociarlos todavía al resultado correspondiente.

## J. Mermaid y artefactos

Se generaron:

- `output/iteration_1/mermaid/PMC5137649_01.mmd`
- `output/iteration_1/mermaid/PMC11722600_01.mmd`
- `output/iteration_1/mermaid/PMC11783470_01.mmd`
- `output/iteration_1/mermaid/PMC2817501_01.mmd`
- `output/iteration_1/mermaid/PMC11368112_01.mmd`

Cada archivo contiene el nodo `Patient` y los nodos `Measurement` sin aristas,
con un comentario explícito que documenta por qué no existen relaciones.
También se generaron `selected_cases.csv`, `sentences.csv`, `tokens.csv`,
`measurements.csv`, `nodes.csv`, `edges.csv`, `validation.json` y `summary.json`.

## K. Tests, métricas y regresión

Resultado: 8 pruebas ejecutadas, 8 aprobadas. Cubren los diez positivos mínimos,
negativos contextuales, presión, rango, dimensión, unidad compartida, notación
`7-mm`, offsets originales, decimales, abreviaturas y tokens clínicos.

Además, se verificó por programa que cada span de las 88 oraciones, 2.097 tokens
y 48 mediciones reconstruye exactamente el fragmento de `original_text` indicado
por sus offsets.

No existe Gold Standard para esta iteración; Precision, Recall y F1 no son
calculables de forma válida. No se fabricaron métricas. No hay una iteración
anterior contra la cual medir regresión. Durante el desarrollo, la corrección de
temperatura eliminó dos falsos positivos de figura y la ampliación de dimensión
reemplazó el span parcial `3 cm` por `3 x 3 cm`; todas las pruebas previas siguieron
pasando.

## L. Nuevos patrones observados y limitaciones

- Notación científica degradada: `12.65 x 109/L`.
- Duraciones con número antes o después de la unidad: `3-day`, `14 days`, `day 4`.
- Referencias con comparador y rango: `<5 mg/L`, `3-20 mm/h`.
- Abreviatura separada por puntuación: `(CA) 19-9`.
- Errores de origen que deben preservarse: `A-53-year`, `revealedsigns`.

El vocabulario de unidades es controlado, no exhaustivo. La segmentación depende
de una lista breve de abreviaturas. No hay asociación semántica, contexto,
negación ni evaluación contra anotación humana.

## Resumen final

**ITERACIÓN:** 1

**Casos procesados:** los cinco casos aprobados; ningún caso de la segunda tanda.

**Implementado:** carga/validación, texto original y limpio, 88 oraciones, 2.097
tokens, normalización básica, 48 mediciones, 53 nodos, CSV/JSON y cinco Mermaid.

**Precision / Recall / F1:** no disponibles por ausencia de Gold Standard.

**Errores principales:** notación científica no reconocida y expresiones
numéricas sin unidad fuera de cobertura.

**Regresiones:** ninguna prueba rota; no existe baseline de una iteración previa.

**Decisiones que requieren aprobación:**

1. Definir si duraciones como `12 h`, `14 days` y `3 months` deben permanecer
   como `Measurement`, ser atributos o pasar a una futura categoría temporal.
2. Definir si deben incorporarse las formas `3-day`, `day 4` y números escritos
   con palabras, y bajo qué estructura.
3. Aprobar o rechazar la interpretación de `12.65 x 109/L` como notación
   científica equivalente a `12.65 × 10^9/L`.
4. Decidir si razones y escalas sin unidad (`4/6`, `3-4 degree`, INR `2.0-3.0`)
   pertenecen al extractor de mediciones.
5. Definir en una iteración posterior cómo distinguir resultado observado y
   rango de referencia sin basarse únicamente en proximidad.
