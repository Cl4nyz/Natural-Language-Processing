from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PROJECT_ROOT.parent
DEFAULT_CASES_PATH = REPOSITORY_ROOT / "sample" / "cases.csv"
DEFAULT_METADATA_PATH = REPOSITORY_ROOT / "sample" / "metadata.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / "iteration_1"

CASE_IDS = [
    "PMC5137649_01",
    "PMC11722600_01",
    "PMC11783470_01",
    "PMC2817501_01",
    "PMC11368112_01",
]
