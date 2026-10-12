"""Same-information local comparison on fixed finite inputs, without Java or network.

Task: validate every expression, feasibility and probe outcome plus exact aggregation.
Creation is measured once per case; encoding and receiver stages are repeated. Total
time is a stage-accounted sum, not a network latency or independently timed deployment.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import statistics
import time
from typing import Any

from rrc.checker import check
from rrc.factor import produce_factorized
from rrc.factor_checker import check_factorized
from rrc.fixture_gold import all_fixture_expectations
from rrc.producer import produce
from rrc.schema import MAX_INPUT_BYTES, load_json, parse_json_bytes, require, strict_equal
from rrc.transport import accept, choose, compact, encode

ROOT = Path(__file__).resolve().parent
METHODS = ("flat_json", "flat_gzip", "factor_json", "factor_gzip",
           "factor_gzip_reuse", "adaptive_gzip_reuse")


def timed(fn):
    wall, cpu = time.perf_counter(), time.process_time()
    result = fn()
    return result, {"wall_seconds": time.perf_counter() - wall,
                    "cpu_seconds": time.process_time() - cpu}


def run(repeats: int) -> dict[str, Any]:
    paths = sorted((ROOT / "inputs").glob("*.json"))
    require(len(paths) == 664, "fixed corpus count")
    gold = all_fixture_expectations()
    records = []
    for position, path in enumerate(paths):
        record = load_json(path, MAX_INPUT_BYTES)
        p = record["program"]
        source = compact(p)  # separately supplied consumer source, without test gold
        source_encoding = timed(lambda: compact(p))[1]
        flat, flat_create = timed(lambda: produce(p))
        factor, factor_create = timed(lambda: produce_factorized(p))
        expected_rows = gold[path.stem] if path.stem.startswith("F") else record["expected_rows"]
        actual_rows = [{"feasible": r["feasible"], "outcomes": r["outcomes"]} for r in flat["rows"]]
        require(strict_equal(actual_rows, expected_rows), "independent finite row expectation")
        expected = check(p, flat)["summary"]
        old = check_factorized(p, factor)
        reused = check_factorized(p, factor, reuse_diagram=True)
        require(strict_equal(old["summary"], expected) and strict_equal(reused["summary"], expected),
                "factorized/reuse summary agreement")
        row = {"case": path.stem, "assignments": old["assignments"],
               "source_bytes": len(source), "old_diagram_steps": old["diagram_steps"],
               "reused_diagram_steps": reused["diagram_steps"], "methods": {}}
        observations = {method: [] for method in METHODS}
        for repeat in range(repeats):
            wires, encodings = {}, {}
            for representation, certificate in (("flat", flat), ("factor", factor)):
                for compressed in (False, True):
                    method = representation + ("_gzip" if compressed else "_json")
                    wires[method], encodings[method] = timed(
                        lambda c=certificate, r=representation, z=compressed: encode(c, r, compressed=z))
            wires["factor_gzip_reuse"] = wires["factor_gzip"]
            encodings["factor_gzip_reuse"] = encodings["factor_gzip"]
            wires["adaptive_gzip_reuse"], selection = timed(
                lambda: choose(wires["flat_gzip"], wires["factor_gzip"]))
            encodings["adaptive_gzip_reuse"] = {
                key: encodings["flat_gzip"][key] + encodings["factor_gzip"][key] + selection[key]
                for key in selection}
            # Rotate measurement order by case/repetition to limit fixed-order timing bias.
            shift = (position + repeat) % len(METHODS)
            for method in METHODS[shift:] + METHODS[:shift]:
                wire = wires[method]
                def receive():
                    consumer_source = parse_json_bytes(source, MAX_INPUT_BYTES)
                    return accept(consumer_source, wire, reuse_diagram=method.endswith("reuse"))
                accepted, receiving = timed(receive)
                require(strict_equal(accepted["checked"]["summary"], expected), "receiver summary")
                creation = (flat_create if method.startswith("flat") else factor_create)
                if method.startswith("adaptive"):
                    creation = {key: flat_create[key] + factor_create[key] for key in flat_create}
                observations[method].append({
                    "wire_bytes": len(wire), "total_bytes": len(source) + len(wire),
                    "representation": accepted["representation"],
                    **{"receive_" + key: value for key, value in receiving.items()},
                    **{"total_" + key: creation[key] + source_encoding[key] + encodings[method][key]
                       + receiving[key] for key in creation},
                })
        for method, runs in observations.items():
            row["methods"][method] = {key: (statistics.median([r[key] for r in runs])
                                             if key.endswith("seconds") else runs[0][key])
                                       for key in runs[0]}
        records.append(row)
        if (position + 1) % 100 == 0:
            print(f"checked {position + 1}/664 finite inputs", flush=True)
    totals = {}
    for method in METHODS:
        rows = [r["methods"][method] for r in records]
        totals[method] = {
            **{key: sum(r[key] for r in rows) for key in rows[0] if key != "representation"},
            "flat_selected": sum(r["representation"] == "flat" for r in rows),
            "factor_selected": sum(r["representation"] == "factor" for r in rows),
        }
    return {"scope": "finite same-information certificate acceptance; no Java/analyzer comparison",
            "cases": len(records), "assignments": sum(r["assignments"] for r in records),
            "repeats": repeats, "python": platform.python_version(), "platform": platform.platform(),
            "timing": "sum of per-case median encode/receive stages plus once-measured creation; disk and network excluded",
            "bytes": "plain compact program source once plus five-byte frame and complete certificate payload",
            "source_bytes": sum(r["source_bytes"] for r in records),
            "old_diagram_steps": sum(r["old_diagram_steps"] for r in records),
            "reused_diagram_steps": sum(r["reused_diagram_steps"] for r in records),
            "totals": totals, "records": records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    require(1 <= args.repeats <= 5, "bounded repetition count")
    output = args.output.resolve()
    require(output.is_relative_to((ROOT / "results").resolve()), "output must stay inside results")
    require(not output.exists(), "choose a fresh output file")
    result = run(args.repeats)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: value for key, value in result.items() if key != "records"}, indent=2))


if __name__ == "__main__":
    main()
