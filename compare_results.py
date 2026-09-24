#!/usr/bin/env python3
"""Compare deterministic campaign outputs and every retained certificate bundle."""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expected", type=Path)
    parser.add_argument("actual", type=Path)
    args = parser.parse_args()
    for name in (
        "deterministic-case-results.json",
        "deterministic-summary.json",
        "negative-controls.json",
        "frontend-results.json",
        "bibliography-results.json",
        "oracle-chunks.json",
    ):
        if load(args.expected / name) != load(args.actual / name):
            raise SystemExit(f"mismatch: {name}")
    expected = {path.name: load(path) for path in (args.expected / "certificates").glob("*.json")}
    actual = {path.name: load(path) for path in (args.actual / "certificates").glob("*.json")}
    if expected != actual:
        raise SystemExit("mismatch: certificate bundles")
    print(json.dumps({"status": "matched", "certificate_bundles": len(expected)}, sort_keys=True))


if __name__ == "__main__":
    main()
