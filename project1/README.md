# Project1 — Iteración 1

Base reproducible y basada en reglas para los cinco casos de desarrollo. Los
offsets de oraciones, tokens y mediciones son intervalos semiabiertos sobre
`original_text`: `original_text[start_char:end_char]`.

Ejecución desde la raíz del repositorio:

```powershell
.\.venv\Scripts\python.exe -m Project1.run_iteration1
.\.venv\Scripts\python.exe -m unittest discover -s Project1/tests -v
```

El punto de entrada es `run_iteration1.py`; `main.py` no se utiliza. Los
artefactos se escriben en `Project1/output/iteration_1/`.
