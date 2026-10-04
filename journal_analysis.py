#!/usr/bin/env python3
"""Recompute journal analyses from the fixed 664-case evidence.

The analyses are descriptive and post hoc.  They do not turn the selected
finite corpus into a statistical sample of Java applications.  Transport
compression uses deterministic gzip level 9 over the exact compact UTF-8 JSON
objects.  Trust-surface counts are descriptive source measures, not assurance
metrics.  Stage timings reuse the retained single-host measurements and are not
speed comparisons with other tools.
"""
from __future__ import annotations

import argparse
import ast
import csv
import gzip
import io
import json
import math
from pathlib import Path
import statistics
import tokenize
from typing import Any, Iterable

from rrc.journal_bridge import journal_bridge_record
from rrc.target_presence_oracle import check_target_presence

ROOT = Path(__file__).resolve().parent
POPULATIONS = ["boundary", "generated", "manual-public", "source-public"]


def emit_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def emit_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to emit empty CSV: {path}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def compact_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def deterministic_gzip(data: bytes) -> bytes:
    """Return deterministic RFC 1952 bytes (level 9, zero modification time)."""
    return gzip.compress(data, compresslevel=9, mtime=0)


def population(case: str) -> str:
    if case.startswith("F"):
        return "boundary"
    if case.startswith("G"):
        return "generated"
    return "manual-public" if int(case[1:]) <= 11 else "source-public"


def family(case: str) -> str:
    if not case.startswith("G"):
        return population(case)
    kind = (int(case[1:]) - 1) % 10
    if kind == 0:
        return "four-coordinate"
    if kind == 1:
        return "alternative-minima"
    return "mixed"


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        raise ValueError("percentile of empty sequence")
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    low = math.floor(index)
    high = math.ceil(index)
    if low == high:
        return ordered[low]
    return ordered[low] * (high - index) + ordered[high] * (index - low)


def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ratios = [row["flat_bytes"] / row["factor_bytes"] for row in rows]
    flat = sum(row["flat_bytes"] for row in rows)
    factor = sum(row["factor_bytes"] for row in rows)
    return {
        "cases": len(rows),
        "assignments": sum(row["assignments"] for row in rows),
        "flat_bytes": flat,
        "factor_bytes": factor,
        "dispatch_bytes": sum(row["dispatch_bytes"] for row in rows),
        "smaller": sum(ratio > 1 for ratio in ratios),
        "larger": sum(ratio < 1 for ratio in ratios),
        "equal": sum(ratio == 1 for ratio in ratios),
        "ratio_total": flat / factor,
        "ratio_median": statistics.median(ratios),
        "ratio_geomean": math.exp(statistics.mean(math.log(ratio) for ratio in ratios)),
        "ratio_min": min(ratios),
        "ratio_max": max(ratios),
    }


def transport_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    raw_ratios = [row["flat_bytes"] / row["factor_bytes"] for row in rows]
    gzip_ratios = [row["flat_gzip_bytes"] / row["factor_gzip_bytes"] for row in rows]
    flat_raw = sum(row["flat_bytes"] for row in rows)
    factor_raw = sum(row["factor_bytes"] for row in rows)
    flat_gzip = sum(row["flat_gzip_bytes"] for row in rows)
    factor_gzip = sum(row["factor_gzip_bytes"] for row in rows)
    return {
        "cases": len(rows),
        "flat_bytes": flat_raw,
        "factor_bytes": factor_raw,
        "dispatch_bytes": sum(row["dispatch_bytes"] for row in rows),
        "flat_gzip_bytes": flat_gzip,
        "factor_gzip_bytes": factor_gzip,
        "dispatch_gzip_bytes": sum(row["dispatch_gzip_bytes"] for row in rows),
        "raw_smaller": sum(ratio > 1 for ratio in raw_ratios),
        "raw_larger": sum(ratio < 1 for ratio in raw_ratios),
        "raw_equal": sum(ratio == 1 for ratio in raw_ratios),
        "gzip_smaller": sum(ratio > 1 for ratio in gzip_ratios),
        "gzip_larger": sum(ratio < 1 for ratio in gzip_ratios),
        "gzip_equal": sum(ratio == 1 for ratio in gzip_ratios),
        "raw_ratio_total": flat_raw / factor_raw,
        "gzip_ratio_total": flat_gzip / factor_gzip,
        "gzip_ratio_median": statistics.median(gzip_ratios),
        "gzip_ratio_geomean": math.exp(
            statistics.mean(math.log(ratio) for ratio in gzip_ratios)
        ),
        "gzip_ratio_min": min(gzip_ratios),
        "gzip_ratio_max": max(gzip_ratios),
    }


def reachable(nodes: list[dict[str, Any]], root: int) -> set[int]:
    seen: set[int] = set()
    todo = [root]
    while todo:
        index = todo.pop()
        if index in seen:
            continue
        seen.add(index)
        node = nodes[index]
        if node["kind"] == "branch":
            todo.extend([node["low"], node["high"]])
    return seen


def python_significant_lines(path: Path) -> int:
    """Count physical lines occupied by non-layout, non-comment Python tokens."""
    source = path.read_text(encoding="utf-8")
    occupied: set[int] = set()
    ignored = {
        tokenize.ENCODING,
        tokenize.ENDMARKER,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.NEWLINE,
        tokenize.NL,
        tokenize.COMMENT,
    }
    for token in tokenize.tokenize(io.BytesIO(source.encode("utf-8")).readline):
        if token.type in ignored:
            continue
        occupied.update(range(token.start[0], token.end[0] + 1))
    return len(occupied)


def java_significant_lines(path: Path) -> int:
    """Count nonblank Java lines after removing lexical line/block comments."""
    lines = path.read_text(encoding="utf-8").splitlines()
    in_block = False
    count = 0
    for line in lines:
        out: list[str] = []
        index = 0
        in_string = False
        in_char = False
        escaped = False
        while index < len(line):
            char = line[index]
            nxt = line[index + 1] if index + 1 < len(line) else ""
            if in_block:
                if char == "*" and nxt == "/":
                    in_block = False
                    index += 2
                else:
                    index += 1
                continue
            if escaped:
                out.append(char)
                escaped = False
                index += 1
                continue
            if char == "\\" and (in_string or in_char):
                out.append(char)
                escaped = True
                index += 1
                continue
            if not in_char and char == '"':
                in_string = not in_string
                out.append(char)
                index += 1
                continue
            if not in_string and char == "'":
                in_char = not in_char
                out.append(char)
                index += 1
                continue
            if not in_string and not in_char and char == "/" and nxt == "*":
                in_block = True
                index += 2
                continue
            if not in_string and not in_char and char == "/" and nxt == "/":
                break
            out.append(char)
            index += 1
        if "".join(out).strip():
            count += 1
    return count


def trust_surface() -> list[dict[str, Any]]:
    groups: list[tuple[str, list[str], str]] = [
        ("shared schema and JSON admission", ["rrc/schema.py"], "trusted shared syntax/limits"),
        ("flat reference checker", ["rrc/checker.py"], "trusted finite reference acceptance"),
        ("factorized certificate checker", ["rrc/factor_checker.py"], "trusted finite certificate acceptance"),
        ("direct-dispatch checker", ["rrc/dispatch_checker.py"], "trusted finite action replay"),
        ("missing-target witness checker", ["rrc/witness_checker.py"], "trusted retention/minimality acceptance"),
        (
            "untrusted producers and lowerers",
            ["rrc/producer.py", "rrc/factor.py", "rrc/dispatch.py", "rrc/missing_witness.py"],
            "outside the trusted base",
        ),
        (
            "Python source-bridge adapter and controls",
            ["rrc/java_frontend.py", "rrc/journal_bridge.py"],
            "optional frontend trust boundary",
        ),
        (
            "javac AST extractor",
            ["frontend/JavaReflectionExtractor.java"],
            "optional frontend trust boundary",
        ),
    ]
    output: list[dict[str, Any]] = []
    for component, relative_paths, role in groups:
        source_lines = 0
        ast_nodes = 0
        for relative in relative_paths:
            path = ROOT / relative
            if path.suffix == ".py":
                source_lines += python_significant_lines(path)
                ast_nodes += sum(1 for _ in ast.walk(ast.parse(path.read_text(encoding="utf-8"))))
            else:
                source_lines += java_significant_lines(path)
        output.append(
            {
                "component": component,
                "files": len(relative_paths),
                "significant_source_lines": source_lines,
                "python_ast_nodes": ast_nodes if ast_nodes else "",
                "role": role,
            }
        )
    return output


def stage_costs(measured: Path) -> list[dict[str, Any]]:
    columns = [
        ("flat producer", "flat_producer_cpu_seconds"),
        ("flat checker", "flat_checker_cpu_seconds"),
        ("factorized producer", "factor_producer_cpu_seconds"),
        ("factorized checker", "factor_checker_cpu_seconds"),
        ("direct lowerer", "dispatch_transformer_cpu_seconds"),
        ("direct checker", "dispatch_checker_cpu_seconds"),
    ]
    with (measured / "case-results.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 664:
        raise ValueError("expected 664 timing rows")
    output = []
    for stage, column in columns:
        values = [float(row[column]) for row in rows]
        output.append(
            {
                "stage": stage,
                "cases": len(values),
                "total_cpu_seconds": sum(values),
                "median_cpu_ms": statistics.median(values) * 1000,
                "p90_cpu_ms": percentile(values, 0.90) * 1000,
                "maximum_cpu_ms": max(values) * 1000,
            }
        )
    return output


def transport_analysis(measured: Path, rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    from rrc.producer import produce
    from rrc.schema import MAX_INPUT_BYTES, load_json

    by_case: list[dict[str, Any]] = []
    for row in rows:
        case = row["case"]
        record = load_json(ROOT / "inputs" / f"{case}.json", MAX_INPUT_BYTES)
        flat = produce(record["program"])
        bundle = json.loads((measured / "certificates" / f"{case}.json").read_text(encoding="utf-8"))
        factor = bundle["factorized_certificate"]
        dispatch = bundle["direct_dispatch"]
        raw_flat = compact_json(flat)
        raw_factor = compact_json(factor)
        raw_dispatch = compact_json(dispatch)
        if len(raw_flat) != row["flat_bytes"]:
            raise AssertionError(f"flat size mismatch for {case}")
        if len(raw_factor) != row["factor_bytes"]:
            raise AssertionError(f"factorized size mismatch for {case}")
        if len(raw_dispatch) != row["dispatch_bytes"]:
            raise AssertionError(f"dispatch size mismatch for {case}")
        flat_gzip = len(deterministic_gzip(raw_flat))
        factor_gzip = len(deterministic_gzip(raw_factor))
        dispatch_gzip = len(deterministic_gzip(raw_dispatch))
        by_case.append(
            {
                "case": case,
                "population": population(case),
                "flat_bytes": len(raw_flat),
                "factor_bytes": len(raw_factor),
                "dispatch_bytes": len(raw_dispatch),
                "flat_gzip_bytes": flat_gzip,
                "factor_gzip_bytes": factor_gzip,
                "dispatch_gzip_bytes": dispatch_gzip,
                "raw_flat_factor_ratio": len(raw_flat) / len(raw_factor),
                "gzip_flat_factor_ratio": flat_gzip / factor_gzip,
            }
        )
    strata = [
        {"population": stratum, **transport_metrics([row for row in by_case if row["population"] == stratum])}
        for stratum in POPULATIONS
    ]
    summary = transport_metrics(by_case)
    summary.update(
        {
            "codec": "gzip level 9",
            "gzip_mtime": 0,
            "input_encoding": "sorted-key compact UTF-8 JSON",
            "scope": "transport-size baseline; decompression precedes the unchanged JSON checker",
        }
    )
    return by_case, strata, summary


def analyze(measured: Path, output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    rows = json.loads((measured / "deterministic-case-results.json").read_text(encoding="utf-8"))
    if len(rows) != 664 or len({row["case"] for row in rows}) != 664:
        raise ValueError("expected the fixed 664 cases")

    strata = [
        {"population": stratum, **metrics([row for row in rows if population(row["case"]) == stratum])}
        for stratum in POPULATIONS
    ]
    emit_csv(output / "strata.csv", strata)

    sensitivity = [{"selection": "all", **metrics(rows)}]
    largest_bytes = max(rows, key=lambda row: row["flat_bytes"])["case"]
    largest_ratio = max(rows, key=lambda row: row["compression_ratio"])["case"]
    sensitivity.append(
        {
            "selection": "without-largest-flat-" + largest_bytes,
            **metrics([row for row in rows if row["case"] != largest_bytes]),
        }
    )
    sensitivity.append(
        {
            "selection": "without-largest-ratio-" + largest_ratio,
            **metrics([row for row in rows if row["case"] != largest_ratio]),
        }
    )
    ordered = sorted(rows, key=lambda row: row["compression_ratio"])
    trim = len(rows) // 100
    sensitivity.append(
        {
            "selection": f"symmetric-ratio-trim-{trim}-each-tail",
            **metrics(ordered[trim:-trim]),
        }
    )
    for generated_family in ["four-coordinate", "alternative-minima", "mixed"]:
        sensitivity.append(
            {
                "selection": "without-generated-family-" + generated_family,
                **metrics([row for row in rows if family(row["case"]) != generated_family]),
            }
        )
    emit_csv(output / "sensitivity.csv", sensitivity)

    sharing: list[dict[str, Any]] = []
    witness_rows: list[dict[str, Any]] = []
    for row in rows:
        bundle = json.loads((measured / "certificates" / f"{row['case']}.json").read_text(encoding="utf-8"))
        certificate = bundle["factorized_certificate"]
        nodes = certificate["diagram"]["nodes"]
        roots = certificate["roots"]["values"] + [certificate["roots"]["feasible"]] + certificate["roots"]["outcomes"]
        width = len(certificate["bit_order"])
        root_sets = [reachable(nodes, root) for root in roots]
        if set().union(*root_sets) != set(range(len(nodes))):
            raise AssertionError("unreachable certificate node")
        sharing.append(
            {
                "case": row["case"],
                "population": population(row["case"]),
                "roots": len(roots),
                "full_tree_slots": len(roots) * ((1 << (width + 1)) - 1),
                "per_root_reduced_nodes": sum(len(node_set) for node_set in root_sets),
                "shared_nodes": len(nodes),
            }
        )
        witnesses = bundle["missing_target_witnesses"]
        distinct = {json.dumps(witness, sort_keys=True, separators=(",", ":")) for witness in witnesses}
        pairs = {(witness["site"], tuple(witness["target"]), witness["base"]) for witness in witnesses}
        if len(witnesses) != 2 * len(pairs):
            raise AssertionError("two orders per selected pair")
        witness_rows.append(
            {
                "case": row["case"],
                "population": population(row["case"]),
                "records": len(witnesses),
                "selected_pairs": len(pairs),
                "unique_records": len(distinct),
                "duplicates": len(witnesses) - len(distinct),
                "selected_coordinates": sum(len(witness["selected"]) for witness in witnesses),
            }
        )
    emit_csv(output / "sharing-by-case.csv", sharing)
    emit_csv(output / "witness-by-case.csv", witness_rows)
    sharing_sum = {
        key: sum(row[key] for row in sharing)
        for key in ["full_tree_slots", "per_root_reduced_nodes", "shared_nodes"]
    }
    sharing_sum["cross_root_node_reduction"] = 1 - sharing_sum["shared_nodes"] / sharing_sum["per_root_reduced_nodes"]
    sharing_strata = [
        {
            "population": stratum,
            **{
                key: sum(row[key] for row in sharing if row["population"] == stratum)
                for key in ["full_tree_slots", "per_root_reduced_nodes", "shared_nodes"]
            },
        }
        for stratum in POPULATIONS
    ]
    emit_csv(output / "sharing-strata.csv", sharing_strata)
    emit_csv(
        output / "sharing-stages.csv",
        [
            {"stage": index + 1, "nodes": sharing_sum[key]}
            for index, key in enumerate(["full_tree_slots", "per_root_reduced_nodes", "shared_nodes"])
        ],
    )
    emit_csv(
        output / "stratum-ratios.csv",
        [
            {"group": index + 1, "geomean": row["ratio_geomean"], "median": row["ratio_median"]}
            for index, row in enumerate(strata)
        ],
    )

    transport_by_case, transport_strata, transport_summary = transport_analysis(measured, rows)
    emit_csv(output / "transport-by-case.csv", transport_by_case)
    emit_csv(output / "transport-strata.csv", transport_strata)
    emit_json(output / "transport-summary.json", transport_summary)

    surface = trust_surface()
    emit_csv(output / "trust-surface.csv", surface)
    costs = stage_costs(measured)
    emit_csv(output / "stage-costs.csv", costs)

    membership = check_target_presence(3)
    bridge = journal_bridge_record()
    emit_json(output / "target-presence-oracle.json", membership)
    emit_json(output / "bridge-controls.json", bridge)

    result = {
        "basis": "existing 664 cases; no cases added or replaced",
        "strata": strata,
        "sensitivity": sensitivity,
        "sensitivity_scope": "post-hoc deterministic corpus sensitivity, not population inference",
        "sharing": sharing_sum,
        "sharing_scope": "tree slots derived; reduced/shared nodes counted from checked DAGs",
        "transport": transport_summary,
        "transport_scope": "deterministic generic-compression baseline over exact compact JSON bytes",
        "stage_costs": costs,
        "stage_cost_scope": "retained single-host CPU observations; not cross-tool performance claims",
        "trust_surface": surface,
        "trust_surface_scope": "descriptive significant-line and Python-AST counts; not correctness evidence",
        "witness": {
            key: sum(row[key] for row in witness_rows)
            for key in ["records", "selected_pairs", "unique_records", "duplicates", "selected_coordinates"]
        },
        "target_presence_oracle": membership,
        "additional_bridge_controls": bridge,
        "status": "matched",
    }
    emit_json(output / "summary.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--measured", default="results/measured")
    parser.add_argument("--output", default="results/journal")
    arguments = parser.parse_args()
    output_path = (ROOT / arguments.output).resolve()
    measured_path = (ROOT / arguments.measured).resolve()
    if not output_path.is_relative_to(ROOT / "results") or not measured_path.is_relative_to(ROOT / "results"):
        parser.error("inputs and outputs must be within artifact/results")
    analysis = analyze(measured_path, output_path)
    print(
        json.dumps(
            {
                "status": analysis["status"],
                "cases": sum(row["cases"] for row in analysis["strata"]),
                "sharing": analysis["sharing"],
                "gzip_ratio": analysis["transport"]["gzip_ratio_total"],
                "target_presence": analysis["target_presence_oracle"]["tables"],
            }
        )
    )
