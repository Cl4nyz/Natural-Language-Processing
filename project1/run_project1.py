"""Punto de entrada de la primera entrega."""

from pathlib import Path

from project1.pipeline import run_pipeline


PROJECT_DIR = Path(__file__).resolve().parent
REPOSITORY_DIR = PROJECT_DIR.parent

CASES_PATH = REPOSITORY_DIR / "sample" / "cases.csv"
METADATA_PATH = REPOSITORY_DIR / "sample" / "metadata.csv"
RESULTS_DIR = PROJECT_DIR / "results" / "post_iteration_1"

CASE_IDS = [
    "PMC5137649_01",
    "PMC11722600_01",
    "PMC11783470_01",
    "PMC2817501_01",
    "PMC11368112_01",
]


if __name__ == "__main__":
    summary = run_pipeline(CASES_PATH, METADATA_PATH, RESULTS_DIR, CASE_IDS)
    print("Ajuste post-Iteración 1 completado")
    print(summary)
