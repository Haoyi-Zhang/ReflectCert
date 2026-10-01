#!/usr/bin/env python3
"""Reproduce the source-frontend and 664-case certificate campaign."""
from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import os
from pathlib import Path
import resource
import shutil
import statistics
import time
from typing import Any

ROOT = Path(__file__).resolve().parent


def cumulative_cpu_seconds() -> float:
    """Return user+system CPU for this process and completed child processes."""
    own = resource.getrusage(resource.RUSAGE_SELF)
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    return own.ru_utime + own.ru_stime + children.ru_utime + children.ru_stime


def cumulative_peak_rss_kib() -> int:
    """Return the largest observed resident set among the driver and its children."""
    own = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    children = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    return max(own, children)


def write_json(path: Path, value: Any) -> None:
    """Atomically replace a JSON file, including after an interrupted prior write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, separators=(",", ":"), allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def compact_bytes(value: Any) -> int:
    return len(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8"))


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = (len(ordered) - 1) * fraction
    low = math.floor(index)
    high = math.ceil(index)
    if low == high:
        return ordered[low]
    return ordered[low] * (high - index) + ordered[high] * (index - low)


def case_record(case: str, output: Path) -> dict[str, Any]:
    from rrc.schema import MAX_INPUT_BYTES, load_json, strict_equal
    from rrc.producer import produce
    from rrc.checker import check
    from rrc.factor import produce_factorized
    from rrc.factor_checker import check_factorized
    from rrc.dispatch import produce_direct_dispatch
    from rrc.dispatch_checker import check_direct_dispatch
    from rrc.missing_witness import produce_missing_target_witness, check_missing_target_witness
    from rrc.baselines import string_sets

    record = load_json(ROOT / "inputs" / f"{case}.json", MAX_INPUT_BYTES)
    program = record["program"]

    start = time.process_time()
    flat = produce(program)
    flat_producer_cpu = time.process_time() - start
    start = time.process_time()
    flat_checked = check(program, flat)
    flat_checker_cpu = time.process_time() - start

    start = time.process_time()
    factor = produce_factorized(program)
    factor_producer_cpu = time.process_time() - start
    start = time.process_time()
    factor_checked = check_factorized(program, factor)
    factor_checker_cpu = time.process_time() - start

    start = time.process_time()
    dispatch = produce_direct_dispatch(program, factor, certificate_checked=True)
    dispatch_transformer_cpu = time.process_time() - start
    start = time.process_time()
    dispatch_checked = check_direct_dispatch(program, dispatch)
    dispatch_checker_cpu = time.process_time() - start

    if not strict_equal(flat_checked["summary"], factor_checked["summary"]):
        raise AssertionError(f"flat/factor summary mismatch: {case}")
    actual = [{"feasible": row["feasible"], "outcomes": row["outcomes"]}
              for row in flat["rows"]]
    if case.startswith("F"):
        # Closed-form fixture expectations live outside the tested inputs and
        # import neither the fixture builder nor producer/checker modules.
        from rrc.fixture_gold import all_fixture_expectations
        expected_rows = all_fixture_expectations()[case]
    else:
        expected_rows = record.get("expected_rows")
    if expected_rows is not None and not strict_equal(actual, expected_rows):
        raise AssertionError(f"independent row expectation mismatch: {case}")

    witnesses = []
    selected_sizes: list[int] = []
    alternative_pairs = 0
    for site, targets in enumerate(factor_checked["summary"]["may"]):
        if not targets:
            continue
        # Pick a deterministic target/base pair that stresses explanation
        # structure: prefer incomparable deletion-order results, then a larger
        # subset-minimal slice, and finally lexicographic target/base order.
        candidates = []
        target_candidates = targets if len(targets) <= 2 else [targets[0], targets[-1]]
        for target in target_candidates:
            claimed = [candidate for candidate in targets if candidate != target]
            containing = [world for world in factor_checked["summary"]["worlds"]
                          if target in world["targets"][site]]
            base_candidates = containing if len(containing) <= 2 else [containing[0], containing[-1]]
            for world in base_candidates:
                forward = produce_missing_target_witness(
                    factor_checked["summary"], site, target, claimed, world["index"], reverse=False)
                reverse = produce_missing_target_witness(
                    factor_checked["summary"], site, target, claimed, world["index"], reverse=True)
                distinct = forward["selected"] != reverse["selected"]
                candidates.append((distinct,
                                   max(len(forward["selected"]), len(reverse["selected"])),
                                   tuple(target), -world["index"], forward, reverse))
        _, _, _, _, forward, reverse = max(candidates, key=lambda row: row[:4])
        for witness in (forward, reverse):
            check_missing_target_witness(factor_checked["summary"], witness)
            witnesses.append(witness)
            selected_sizes.append(len(witness["selected"]))
        alternative_pairs += int(forward["selected"] != reverse["selected"])

    exact = factor_checked["summary"]["may"]
    string_set = string_sets(program)
    constant = string_sets(program, True)
    for baseline in (string_set, constant):
        if not all(set(map(tuple, expected)) <= set(map(tuple, reported))
                   for expected, reported in zip(exact, baseline)):
            raise AssertionError(f"unsound local baseline: {case}")

    flat_size = compact_bytes(flat)
    factor_size = compact_bytes(factor)
    dispatch_size = compact_bytes(dispatch)
    witness_keys = {
        json.dumps(witness, sort_keys=True, separators=(",", ":"), allow_nan=False)
        for witness in witnesses
    }
    bundle = {"format": "reflection-resolution-evidence",
              "factorized_certificate": factor, "direct_dispatch": dispatch,
              "missing_target_witnesses": witnesses}
    write_json(output / "certificates" / f"{case}.json", bundle)
    return {
        "case": case,
        "label": record["label"],
        "category": ("fixture" if case.startswith("F") else
                     ("generated" if case.startswith("G") else
                      ("public_manual" if int(case[1:]) <= 11 else "public_source_extracted"))),
        "generated": case.startswith("G"),
        "external_bits": len(program["external"]),
        "choice_bits": len(program["choices"]),
        "nodes": len(program["nodes"]),
        "sites": len(program["sites"]),
        "table_entries": len(program["table"]),
        "assignments": factor_checked["assignments"],
        "feasible_worlds": len(factor_checked["summary"]["worlds"]),
        "flat_bytes": flat_size,
        "factor_bytes": factor_size,
        "compression_ratio": flat_size / factor_size,
        "diagram_nodes": factor_checked["diagram_nodes"],
        "dispatch_bytes": dispatch_size,
        "dispatch_nodes": dispatch_checked["diagram_nodes"],
        "dispatch_trace_events": dispatch_checked["trace_events"],
        "dispatch_semantic_steps": dispatch_checked["semantic_steps"],
        "dispatch_diagram_steps": dispatch_checked["diagram_steps"],
        "dispatch_invocations": dispatch_checked["invocations"],
        "dispatch_lookup_errors": dispatch_checked["lookup_errors"],
        "dispatch_skipped": dispatch_checked["skipped"],
        "dispatch_infeasible": dispatch_checked["infeasible"],
        "flat_checker_steps": flat_checked["checker_steps"],
        "factor_semantic_steps": factor_checked["semantic_steps"],
        "factor_diagram_steps": factor_checked["diagram_steps"],
        "missing_target_witnesses": len(witnesses),
        "witness_target_base_pairs": len(witnesses) // 2,
        "witness_unique_within_case": len(witness_keys),
        "witness_duplicate_records": len(witnesses) - len(witness_keys),
        "witness_selected_total": sum(selected_sizes),
        "witness_selected_max": max(selected_sizes, default=0),
        "alternative_witness_pairs": alternative_pairs,
        "string_set_extra_targets": sum(len(set(map(tuple, reported)) - set(map(tuple, expected)))
                                        for expected, reported in zip(exact, string_set)),
        "constant_extra_targets": sum(len(set(map(tuple, reported)) - set(map(tuple, expected)))
                                      for expected, reported in zip(exact, constant)),
        "flat_producer_cpu_seconds": flat_producer_cpu,
        "flat_checker_cpu_seconds": flat_checker_cpu,
        "factor_producer_cpu_seconds": factor_producer_cpu,
        "factor_checker_cpu_seconds": factor_checker_cpu,
        "dispatch_transformer_cpu_seconds": dispatch_transformer_cpu,
        "dispatch_checker_cpu_seconds": dispatch_checker_cpu,
    }


def controls() -> dict[str, Any]:
    from rrc.schema import Invalid, MAX_CERT_BYTES, validate
    from rrc.fixtures import all_fixtures
    from rrc.factor import produce_factorized, serialized_bytes
    from rrc.factor_checker import check_factorized
    from rrc.dispatch import produce_direct_dispatch
    from rrc.dispatch_checker import check_direct_dispatch
    from rrc.baselines import invoke_all
    from rrc.producer import produce
    from rrc.missing_witness import produce_missing_target_witness, check_missing_target_witness
    from rrc.witness_counterexamples import minimum_cardinality_counterexample

    fixtures = {name: program for name, _, program in all_fixtures()}
    program = fixtures["F06"]
    factor = produce_factorized(program)
    rejected: dict[str, bool] = {}

    bad = copy.deepcopy(factor)
    bad["program"]["table"][0][0] = "OTHER"
    try:
        check_factorized(program, bad)
        rejected["source_binding"] = False
    except Invalid:
        rejected["source_binding"] = True

    bad = copy.deepcopy(factor)
    terminal = next(node for node in bad["diagram"]["nodes"]
                    if node["kind"] == "terminal" and node["value"] is False)
    terminal["value"] = True
    try:
        check_factorized(program, bad)
        rejected["terminal_value"] = False
    except Invalid:
        rejected["terminal_value"] = True

    direct = produce_direct_dispatch(program, factor, certificate_checked=True)
    bad_direct = copy.deepcopy(direct)
    bad_direct["program"]["table"][0][0] = "OTHER"
    try:
        check_direct_dispatch(program, bad_direct)
        rejected["dispatch_source_binding"] = False
    except Invalid:
        rejected["dispatch_source_binding"] = True

    bad_direct = copy.deepcopy(direct)
    invoke_terminal = next(node for node in bad_direct["diagram"]["nodes"]
                           if node["kind"] == "terminal" and node["action"]["kind"] == "invoke")
    invoke_terminal["action"] = {"kind": "lookup_error", "key": ["Z", "Z", "Z", "Z"]}
    try:
        check_direct_dispatch(program, bad_direct)
        rejected["dispatch_terminal_action"] = False
    except Invalid:
        rejected["dispatch_terminal_action"] = True

    summary = check_factorized(program, factor)["summary"]
    target = summary["may"][0][0]
    base = next(world["index"] for world in summary["worlds"] if target in world["targets"][0])
    witness = produce_missing_target_witness(summary, 0, target, summary["may"][0][1:], base)
    bad_witness = copy.deepcopy(witness)
    bad_witness["necessity"] = []
    try:
        check_missing_target_witness(summary, bad_witness)
        rejected["necessity_omission"] = False
    except Invalid:
        rejected["necessity_omission"] = True

    word = "A" * 48
    large = {"external": [f"h{i}" for i in range(8)], "choices": [f"r{i}" for i in range(4)],
             "nodes": [{"op": "lit", "value": True}] + [{"op": "lit", "value": word} for _ in range(63)],
             "feasible": 0, "table": [[word] * 4],
             "sites": [{"guard": 0, "loader": 1, "class": 1, "method": 1, "signature": 1}
                       for _ in range(8)]}
    validate(large)
    large_factor = produce_factorized(large)
    check_factorized(large, large_factor)
    large_dispatch = produce_direct_dispatch(large, large_factor, certificate_checked=True)
    large_dispatch_checked = check_direct_dispatch(large, large_dispatch)
    flat_quoted_string_lower_bound = (1 << 12) * (63 + 8 * 4) * (48 + 2)
    invoke_all_program = fixtures["F03"]
    invoke_all_flat = produce(invoke_all_program)
    invoke_all_counterexample = invoke_all(invoke_all_flat["summary"]["may"][0]) != invoke_all_flat["rows"][0]["outcomes"]
    if not invoke_all_counterexample:
        raise AssertionError("invoke-all negative control collapsed")
    if not all(rejected.values()):
        raise AssertionError("a seeded fault was accepted")
    if not (flat_quoted_string_lower_bound > MAX_CERT_BYTES > serialized_bytes(large_factor)):
        raise AssertionError("factorized admission control failed")
    return {
        "seeded_faults_rejected": rejected,
        "minimum_cardinality_counterexample": minimum_cardinality_counterexample(),
        "flat_quoted_string_lower_bound": flat_quoted_string_lower_bound,
        "factorized_bytes": serialized_bytes(large_factor),
        "certificate_byte_cap": MAX_CERT_BYTES,
        "factorized_checker_assignments": 1 << 12,
        "direct_dispatch_bytes": compact_bytes(large_dispatch),
        "direct_dispatch_checker_assignments": large_dispatch_checked["assignments"],
        "invoke_all_counterexample": invoke_all_counterexample,
    }


def run_oracle(output: Path) -> dict[str, int]:
    """Run two exhaustive set-theoretic spaces independently of the DSL."""
    from rrc.oracle import check_chunk

    specifications = [(2, 4), (3, 2)]
    chunks: list[dict[str, Any]] = []
    totals: dict[str, int] = {}
    for bits, labels in specifications:
        total = (labels + 1) ** (1 << bits)
        counts = check_chunk(bits, labels, 0, total)
        chunks.append({"bits": bits, "target_labels": labels, "start": 0, "stop": total,
                       "counts": counts})
        for key, value in counts.items():
            totals[key] = totals.get(key, 0) + value
    write_json(output / "oracle-chunks.json", chunks)
    if totals.get("mismatches") != 0:
        raise AssertionError("exhaustive oracle mismatch")
    return totals


def run(output: Path, *, resume: bool = False) -> dict[str, Any]:
    if output.exists() and any(output.iterdir()) and not resume:
        raise RuntimeError("output directory must be absent or empty (or pass --resume)")
    output.mkdir(parents=True, exist_ok=True)
    partial_records = output / "partial-records"
    partial_records.mkdir(parents=True, exist_ok=True)
    progress_path = output / "progress.json"
    prior_wall = 0.0
    prior_cpu = 0.0
    prior_peak = 0
    if resume and progress_path.exists():
        with progress_path.open(encoding="utf-8") as stream:
            previous_progress = json.load(stream)
        prior_wall = float(previous_progress.get("wall_seconds", 0.0))
        prior_cpu = float(previous_progress.get("cpu_seconds", 0.0))
        prior_peak = int(previous_progress.get("peak_rss_kib", 0))
    started_wall = time.monotonic()
    started_cpu = cumulative_cpu_seconds()

    def progress(status: str, completed: int, total: int) -> dict[str, Any]:
        return {
            "status": status,
            "completed": completed,
            "total": total,
            "wall_seconds": prior_wall + (time.monotonic() - started_wall),
            "cpu_seconds": prior_cpu + (cumulative_cpu_seconds() - started_cpu),
            "peak_rss_kib": max(prior_peak, cumulative_peak_rss_kib()),
        }

    from rrc.java_frontend import frontend_result_record, frontend_control_record
    from verify_bibliography import verify as verify_bibliography

    bibliography_path = output / "bibliography-results.json"
    if resume and bibliography_path.exists():
        with bibliography_path.open(encoding="utf-8") as stream:
            bibliography_results = json.load(stream)
    else:
        bibliography_results = verify_bibliography(
            ROOT / "docs" / "references.bib",
            ROOT / "docs" / "bibliography-audit.csv",
            ROOT / "docs" / "literature.csv",
            minimum=55,
        )
        write_json(bibliography_path, bibliography_results)

    frontend_path = output / "frontend-results.json"
    if resume and frontend_path.exists():
        with frontend_path.open(encoding="utf-8") as stream:
            frontend_results = json.load(stream)
    else:
        frontend_results = {
            "public_sources": frontend_result_record(),
            "controls": frontend_control_record(),
        }
        write_json(frontend_path, frontend_results)
    cases = ([f"F{index:02d}" for index in range(1, 25)]
             + [f"G{index:03d}" for index in range(1, 601)]
             + [f"P{index:03d}" for index in range(1, 41)])
    records = []
    for position, case in enumerate(cases, start=1):
        partial_path = partial_records / f"{case}.json"
        if resume and partial_path.exists() and (output / "certificates" / f"{case}.json").exists():
            with partial_path.open(encoding="utf-8") as stream:
                record = json.load(stream)
        else:
            record = case_record(case, output)
            write_json(partial_path, record)
        records.append(record)
        # Every completed case becomes a durable resume point.
        write_json(progress_path, progress("partial", position, len(cases)))
    control_results = controls()
    oracle_results = run_oracle(output)

    deterministic_fields = [key for key in records[0] if not key.endswith("_seconds")]
    with (output / "case-results.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    write_json(output / "case-results.json", records)
    write_json(output / "deterministic-case-results.json",
               [{key: row[key] for key in deterministic_fields} for row in records])
    write_json(output / "negative-controls.json", control_results)

    ratios = [row["compression_ratio"] for row in records]
    flat_sizes = [row["flat_bytes"] for row in records]
    factor_sizes = [row["factor_bytes"] for row in records]
    summary = {
        "status": "complete",
        "case_count": len(records),
        "authored_fixtures": 24,
        "generated_cases": 600,
        "public_cases": 40,
        "manual_public_projections": 11,
        "source_extracted_public_cases": 29,
        "public_source_apps": 13,
        "bibliography_entries": bibliography_results["entries"],
        "bibliography_unique_dois": bibliography_results["unique_dois"],
        "bibliography_no_doi_records": bibliography_results["no_doi_records"],
        "bibliography_audit_rows": bibliography_results["audit_rows"],
        "redistributed_source_files": frontend_results["public_sources"]["source_files"],
        "frontend_gold_matches": frontend_results["public_sources"]["gold_matches"],
        "frontend_rejection_controls": frontend_results["controls"]["rejection_controls"],
        "frontend_supported_assignment_checks": frontend_results["controls"]["supported_assignment_checks"],
        "frontend_runtime_assignments": frontend_results["controls"]["runtime_probe"]["assignments"],
        "frontend_runtime_identity_checks": frontend_results["controls"]["runtime_probe"]["identity_checks"],
        "frontend_direct_call_assignments": frontend_results["controls"]["direct_call_probe"]["assignments"],
        "frontend_direct_call_invocation_checks": frontend_results["controls"]["direct_call_probe"]["invocation_checks"],
        "frontend_bridge_risk_sources": frontend_results["controls"]["bridge_risks"]["source_files"],
        "frontend_bridge_risk_runtime_executions": frontend_results["controls"]["bridge_risks"]["runtime_executions"],
        "frontend_bridge_risk_rejected_events": frontend_results["controls"]["bridge_risks"]["rejected_events"],
        "assignments": sum(row["assignments"] for row in records),
        "flat_checker_steps": sum(row["flat_checker_steps"] for row in records),
        "factor_semantic_steps": sum(row["factor_semantic_steps"] for row in records),
        "factor_diagram_steps": sum(row["factor_diagram_steps"] for row in records),
        "dispatch_trace_events": sum(row["dispatch_trace_events"] for row in records),
        "dispatch_semantic_steps": sum(row["dispatch_semantic_steps"] for row in records),
        "dispatch_diagram_steps": sum(row["dispatch_diagram_steps"] for row in records),
        "dispatch_invocations": sum(row["dispatch_invocations"] for row in records),
        "dispatch_lookup_errors": sum(row["dispatch_lookup_errors"] for row in records),
        "dispatch_skipped": sum(row["dispatch_skipped"] for row in records),
        "dispatch_infeasible": sum(row["dispatch_infeasible"] for row in records),
        "dispatch_bytes_total": sum(row["dispatch_bytes"] for row in records),
        "dispatch_nodes_total": sum(row["dispatch_nodes"] for row in records),
        "dispatch_nodes_max": max(row["dispatch_nodes"] for row in records),
        "missing_target_witnesses": sum(row["missing_target_witnesses"] for row in records),
        "witness_target_base_pairs": sum(row["witness_target_base_pairs"] for row in records),
        "witness_unique_within_case": sum(row["witness_unique_within_case"] for row in records),
        "witness_duplicate_records": sum(row["witness_duplicate_records"] for row in records),
        "public_witness_records": sum(row["missing_target_witnesses"] for row in records
                                      if row["category"].startswith("public_")),
        "public_witness_unique_within_case": sum(row["witness_unique_within_case"] for row in records
                                                  if row["category"].startswith("public_")),
        "witness_selected_total": sum(row["witness_selected_total"] for row in records),
        "witness_selected_max": max(row["witness_selected_max"] for row in records),
        "alternative_witness_pairs": sum(row["alternative_witness_pairs"] for row in records),
        "flat_bytes_total": sum(flat_sizes),
        "factor_bytes_total": sum(factor_sizes),
        "factor_smaller_cases": sum(factor < flat for factor, flat in zip(factor_sizes, flat_sizes)),
        "factor_larger_cases": sum(factor > flat for factor, flat in zip(factor_sizes, flat_sizes)),
        "compression_ratio_median": statistics.median(ratios),
        "compression_ratio_p10": percentile(ratios, 0.10),
        "compression_ratio_p90": percentile(ratios, 0.90),
        "compression_ratio_max": max(ratios),
        "compression_ratio_geometric_mean": math.exp(sum(math.log(value) for value in ratios) / len(ratios)),
        "largest_factor_bytes": max(factor_sizes),
        "largest_flat_bytes": max(flat_sizes),
        "string_set_extra_targets": sum(row["string_set_extra_targets"] for row in records),
        "constant_extra_targets": sum(row["constant_extra_targets"] for row in records),
        "wall_seconds": prior_wall + (time.monotonic() - started_wall),
        "cpu_seconds": prior_cpu + (cumulative_cpu_seconds() - started_cpu),
        "peak_rss_kib": max(prior_peak, cumulative_peak_rss_kib()),
        "negative_controls": control_results,
        "bibliography": bibliography_results,
        "frontend": {
            "accepted_public_events": frontend_results["public_sources"]["accepted_events"],
            "rejected_public_events": frontend_results["public_sources"]["rejected_events"],
            "gold_matches": frontend_results["public_sources"]["gold_matches"],
            "rejection_controls": frontend_results["controls"]["rejection_controls"],
            "runtime_assignments": frontend_results["controls"]["runtime_probe"]["assignments"],
            "runtime_identity_checks": frontend_results["controls"]["runtime_probe"]["identity_checks"],
            "direct_call_assignments": frontend_results["controls"]["direct_call_probe"]["assignments"],
            "direct_call_invocation_checks": frontend_results["controls"]["direct_call_probe"]["invocation_checks"],
            "bridge_risk_sources": frontend_results["controls"]["bridge_risks"]["source_files"],
            "bridge_risk_runtime_executions": frontend_results["controls"]["bridge_risks"]["runtime_executions"],
            "bridge_risk_rejected_events": frontend_results["controls"]["bridge_risks"]["rejected_events"],
        },
        "oracle": oracle_results,
    }
    write_json(output / "summary.json", summary)
    deterministic_summary = {
        key: value for key, value in summary.items()
        if key not in {"wall_seconds", "cpu_seconds", "peak_rss_kib"}
    }
    write_json(output / "deterministic-summary.json", deterministic_summary)
    write_json(progress_path, {
        "status": "complete",
        "completed": len(records),
        "total": len(records),
        "wall_seconds": summary["wall_seconds"],
        "cpu_seconds": summary["cpu_seconds"],
        "peak_rss_kib": summary["peak_rss_kib"],
    })
    shutil.rmtree(partial_records)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/reproduced"))
    parser.add_argument("--resume", action="store_true", help="resume an interrupted run")
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else (ROOT / args.output)
    output = output.resolve()
    try:
        output.relative_to((ROOT / "results").resolve())
    except ValueError as exc:
        raise SystemExit("output must be inside results/") from exc
    print(json.dumps(run(output, resume=args.resume), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
