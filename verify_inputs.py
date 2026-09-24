#!/usr/bin/env python3
"""Compare each supplied input with its deterministic in-repository construction."""
from pathlib import Path
from rrc.fixtures import all_fixtures
from rrc.generated import all_generated
from rrc.public_cases import all_public, provenance_rows
from rrc.schema import load_json, strict_equal, MAX_INPUT_BYTES
from rrc.java_frontend import frontend_result_record, frontend_control_record
from verify_bibliography import verify as verify_bibliography
import json

ROOT = Path(__file__).resolve().parent

def main():
    expected = {name: {"label": label, "program": p} for name, label, p in all_fixtures()}
    expected.update({name: {"label": "deterministic structured generated case", "program": p,
                            "expected_rows": outcome} for name, p, outcome in all_generated()})
    expected.update({name: {"label": label, "program": p, "expected_rows": outcome}
                     for name, label, p, outcome, _ in all_public()})
    actual = {path.stem for path in (ROOT / "inputs").glob("*.json")}
    if actual != set(expected):
        raise RuntimeError("input inventory differs from the specified 24 + 600 + 40 cases")
    for name, value in expected.items():
        if not strict_equal(load_json(ROOT / "inputs" / (name + ".json"), MAX_INPUT_BYTES), value):
            raise RuntimeError("input construction mismatch: " + name)
    rows = provenance_rows()
    with (ROOT / "docs" / "public-provenance.csv").open(newline="", encoding="utf-8") as stream:
        actual_rows = list(__import__("csv").DictReader(stream))
    if actual_rows != rows:
        raise RuntimeError("public provenance table mismatch")
    frontend = frontend_result_record()
    controls = frontend_control_record()
    bibliography = verify_bibliography(
        ROOT / "docs" / "references.bib",
        ROOT / "docs" / "bibliography-audit.csv",
        ROOT / "docs" / "literature.csv",
    )
    print(json.dumps({"status": "matched", "authored_fixtures": 24, "generated_cases": 600,
                      "public_cases": 40, "manual_public_projections": 11,
                      "source_extracted_public_cases": 29, "public_source_apps": 13,
                      "frontend_source_files": frontend["source_files"],
                      "frontend_gold_matches": frontend["gold_matches"],
                      "frontend_rejection_controls": controls["rejection_controls"],
                      "frontend_runtime_identity_checks": controls["runtime_probe"]["identity_checks"],
                      "frontend_direct_call_checks": controls["direct_call_probe"]["invocation_checks"],
                      "bibliography_entries": bibliography["entries"],
                      "bibliography_unique_dois": bibliography["unique_dois"]}, sort_keys=True))

if __name__ == "__main__": main()
