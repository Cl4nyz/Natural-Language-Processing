import argparse
from pathlib import Path

from Project1.config import (
    CASE_IDS,
    DEFAULT_CASES_PATH,
    DEFAULT_METADATA_PATH,
    DEFAULT_OUTPUT_DIR,
)
from Project1.pipeline import run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the reproducible Iteration 1 pipeline.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = run_pipeline(args.cases, args.metadata, args.output, CASE_IDS)
    print(f"Iteration 1 complete: {result}")
