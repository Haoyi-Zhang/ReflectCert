#!/usr/bin/env python3
"""Compare deterministic journal analyses while treating retained CPU summaries as host observations."""
from pathlib import Path
import argparse
import csv
import json

TIMING_FILE = "stage-costs.csv"
TIMING_SUMMARY_FIELD = "stage_costs"
EXPECTED_STAGES = {
    "flat producer", "flat checker", "factorized producer",
    "factorized checker", "direct lowerer", "direct checker",
}


def load_stage_shape(path: Path) -> tuple[set[str], set[int]]:
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    return {row["stage"] for row in rows}, {int(row["cases"]) for row in rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expected")
    parser.add_argument("actual")
    args = parser.parse_args()
    left = Path(args.expected)
    right = Path(args.actual)
    names = {path.name for path in left.iterdir() if path.is_file()}
    if names != {path.name for path in right.iterdir() if path.is_file()}:
        raise SystemExit("journal result inventories differ")

    for name in sorted(names):
        if name == TIMING_FILE:
            left_shape = load_stage_shape(left / name)
            right_shape = load_stage_shape(right / name)
            expected_shape = (EXPECTED_STAGES, {664})
            if left_shape != expected_shape or right_shape != expected_shape:
                raise SystemExit("journal stage-cost inventory differs")
            continue

        left_text = (left / name).read_text(encoding="utf-8")
        right_text = (right / name).read_text(encoding="utf-8")
        if name.endswith(".json"):
            left_value = json.loads(left_text)
            right_value = json.loads(right_text)
            if name == "summary.json":
                left_value.pop(TIMING_SUMMARY_FIELD, None)
                right_value.pop(TIMING_SUMMARY_FIELD, None)
            same = left_value == right_value
        else:
            same = left_text == right_text
        if not same:
            raise SystemExit("journal result differs: " + name)

    print(json.dumps({
        "status": "matched",
        "journal_files": len(names),
        "environment_sensitive": [TIMING_FILE, "summary.json:stage_costs"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
