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


def compare(left: Path, right: Path, *, current_source_surface: bool = False) -> dict:
    names = {path.name for path in left.iterdir() if path.is_file()}
    if names != {path.name for path in right.iterdir() if path.is_file()}:
        raise SystemExit("journal result inventories differ")

    surface = None
    baseline_surface_changed = False
    if current_source_surface:
        # Source size is a description of this checkout, not a frozen campaign outcome.
        # Require freshly measured current counts in BOTH representations, not a bypass.
        from journal_analysis import trust_surface
        from rrc.schema import strict_equal
        surface = trust_surface()
        actual_summary = json.loads((right / "summary.json").read_text(encoding="utf-8"))
        if not strict_equal(actual_summary["trust_surface"], surface):
            raise SystemExit("journal current-source trust surface differs: summary.json")
        with (right / "trust-surface.csv").open(encoding="utf-8", newline="") as stream:
            actual_surface = list(csv.DictReader(stream))
        expected_surface = [{key: str(value) for key, value in row.items()} for row in surface]
        if actual_surface != expected_surface:
            raise SystemExit("journal current-source trust surface differs: trust-surface.csv")
        baseline_summary = json.loads((left / "summary.json").read_text(encoding="utf-8"))
        baseline_surface_changed = not strict_equal(baseline_summary["trust_surface"], surface)

    for name in sorted(names):
        if current_source_surface and name == "trust-surface.csv":
            continue  # Already validated against the current source, above.
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
                if current_source_surface:
                    left_value.pop("trust_surface")
                    right_value.pop("trust_surface")
            same = left_value == right_value
        else:
            same = left_text == right_text
        if not same:
            raise SystemExit("journal result differs: " + name)

    result = {
        "status": "matched",
        "journal_files": len(names),
        "environment_sensitive": [TIMING_FILE, "summary.json:stage_costs"],
    }
    if current_source_surface:
        result["current_source_surface"] = surface
        result["source_surface_baseline_changed"] = baseline_surface_changed
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expected")
    parser.add_argument("actual")
    parser.add_argument("--current-source-surface", action="store_true",
                        help="validate actual trust-surface counts against this checkout; "
                             "keep all other deterministic comparisons unchanged")
    args = parser.parse_args()
    print(json.dumps(compare(Path(args.expected), Path(args.actual),
                             current_source_surface=args.current_source_surface), sort_keys=True))


if __name__ == "__main__":
    main()
