# executa o pipeline nos cinco casos de desenvolvimento

from pathlib import Path

from approach_04_controlled_gazetteer.pipeline import run_pipeline


SOURCE_DIR = Path(__file__).resolve().parent
REPOSITORY_DIR = SOURCE_DIR.parent

CASES_PATH = REPOSITORY_DIR / "data" / "raw" / "cases.csv"
METADATA_PATH = REPOSITORY_DIR / "data" / "raw" / "metadata.csv"
RESULTS_DIR = REPOSITORY_DIR / "data" / "processed"
OUTPUT_PREFIX = "04_"

CASE_IDS = [
    "PMC5137649_01",
    "PMC11722600_01",
    "PMC11783470_01",
    "PMC2817501_01",
    "PMC11368112_01",
]


if __name__ == "__main__":
    summary = run_pipeline(
        CASES_PATH,
        METADATA_PATH,
        RESULTS_DIR,
        CASE_IDS,
        output_prefix=OUTPUT_PREFIX,
    )
    print("abordagem 04 concluida")
    print(summary)
