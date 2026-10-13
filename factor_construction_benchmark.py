"""Same-information producer comparison on the frozen benign finite corpus.

Each timed or allocation-profiled corpus pass runs in a fresh child process with
one path live at a time. The legacy builder below is the pre-token algorithm;
both factor paths use the same eager evaluator and summary implementation.
No Java extraction, external analyzer, network, dispatch-only substitution, or
adaptive selection is measured. Outputs must be fresh.
"""
from __future__ import annotations

import argparse
import copy
import gc
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
import tracemalloc
from unittest.mock import patch

from rrc import factor
from rrc.checker import check
from rrc.dispatch import produce_direct_dispatch
from rrc.dispatch_checker import check_direct_dispatch
from rrc.factor_checker import check_factorized
from rrc.fixture_gold import all_fixture_expectations
from rrc.producer import produce
from rrc.schema import MAX_CERT_BYTES, MAX_INPUT_BYTES, load_json, require, strict_equal, validate
from rrc.transport import _encode_raw, accept, compact
from rrc.witness_checker import check_missing_target_witness

ROOT = Path(__file__).resolve().parent
METHODS = ("flat_gzip", "factor_legacy_gzip", "factor_tokens_gzip")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


class LegacySharedMTBDD:
    """Frozen pre-token algorithm, including recursive JSON-string memo keys."""

    def __init__(self, width):
        self.width = width
        self.nodes = []
        self._terminal_ids = {}
        self._branch_ids = {}
        self._memo = {}

    def terminal(self, value):
        key = canonical(value)
        found = self._terminal_ids.get(key)
        if found is not None:
            return found
        node_id = len(self.nodes)
        self.nodes.append({"kind": "terminal", "value": copy.deepcopy(value)})
        self._terminal_ids[key] = node_id
        return node_id

    def branch(self, var, low, high):
        if low == high:
            return low
        key = (var, low, high)
        found = self._branch_ids.get(key)
        if found is not None:
            return found
        node_id = len(self.nodes)
        self.nodes.append({"kind": "branch", "var": var, "low": low, "high": high})
        self._branch_ids[key] = node_id
        return node_id

    def build(self, values, var=0):
        if len(values) != 1 << (self.width - var):
            raise ValueError("diagram vector width")
        enc = tuple(canonical(value) for value in values)
        key = (var, enc)
        found = self._memo.get(key)
        if found is not None:
            return found
        if all(value == enc[0] for value in enc[1:]):
            root = self.terminal(values[0])
        else:
            if var >= self.width:
                raise AssertionError("different values without a decision variable")
            half = len(values) // 2
            root = self.branch(var, self.build(values[:half], var + 1),
                               self.build(values[half:], var + 1))
        self._memo[key] = root
        return root


def produce_legacy(program):
    validate(program)
    width = len(program["external"]) + len(program["choices"])
    values, feasible, outcomes = factor._evaluate_all(program)
    diagram = LegacySharedMTBDD(width)
    value_roots = [diagram.build(vector) for vector in values]
    feasible_root = diagram.build(feasible)
    outcome_roots = [diagram.build(vector) for vector in outcomes]
    return {"format": factor.FORMAT, "program": copy.deepcopy(program),
            "bit_order": list(program["external"] + program["choices"]),
            "diagram": {"nodes": diagram.nodes},
            "roots": {"values": value_roots, "feasible": feasible_root, "outcomes": outcome_roots},
            "summary": factor._summary(program, outcomes, feasible)}


def paths():
    found = sorted((ROOT / "inputs").glob("*.json"))
    require(len(found) == 664, "frozen 664-input corpus required")
    return found


def verify():
    """Complete acceptance and work counts, outside all measured samples."""
    gold = all_fixture_expectations()
    rows = []
    for path in paths():
        record = load_json(path, MAX_INPUT_BYTES)
        program = record["program"]
        flat = produce(program)
        expected_rows = gold[path.stem] if path.stem.startswith("F") else record["expected_rows"]
        require(strict_equal([{"feasible": row["feasible"], "outcomes": row["outcomes"]}
                              for row in flat["rows"]], expected_rows), "independent row expectation")
        old, new = produce_legacy(program), factor.produce_factorized(program)
        saved = load_json(ROOT / "results" / "measured" / "certificates" / path.name, MAX_CERT_BYTES)
        require(compact(old) == compact(new) == compact(saved["factorized_certificate"]),
                "legacy/current/retained complete certificate byte identity")
        old_checked, new_checked = check_factorized(program, old), check_factorized(program, new)
        require(strict_equal(old_checked, new_checked), "unchanged checker counters and values")
        require(strict_equal(new_checked["summary"], check(program, flat)["summary"]), "flat summary")
        direct = produce_direct_dispatch(program, new, certificate_checked=True)
        require(compact(direct) == compact(saved["direct_dispatch"]), "unchanged direct object")
        replay = check_direct_dispatch(program, direct)
        for witness in saved["missing_target_witnesses"]:
            check_missing_target_witness(new_checked["summary"], witness)
        work = {}
        for label, producer, target in (("legacy", produce_legacy, __name__ + ".canonical"),
                                        ("tokens", factor.produce_factorized, "rrc.factor._canonical")):
            count = {"canonical_calls": 0, "canonical_characters": 0}
            def counted(value):
                result = canonical_original(value)
                count["canonical_calls"] += 1
                count["canonical_characters"] += len(result)
                return result
            canonical_original = canonical
            with patch(target, counted):
                producer(program)
            work[label] = count
        rows.append({"case": path.stem, "assignments": new_checked["assignments"],
                     "trace_events": replay["trace_events"],
                     "witnesses": len(saved["missing_target_witnesses"]), **work})
    return {"cases": len(rows), "assignments": sum(row["assignments"] for row in rows),
            "trace_events": sum(row["trace_events"] for row in rows),
            "witnesses": sum(row["witnesses"] for row in rows),
            "byte_identical_certificates": len(rows), "byte_identical_direct_objects": len(rows),
            "work": {label: {key: sum(row[label][key] for row in rows) for key in rows[0][label]}
                     for label in ("legacy", "tokens")}, "records": rows}


def peak_rss_bytes():
    """OS process maximum, including interpreter, imports and native allocations."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in
                ("peak_ws", "ws", "peak_paged", "paged", "peak_nonpaged", "nonpaged", "pagefile", "peak_pagefile")]
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = (wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD)
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        require(bool(psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb)),
                "OS process memory observation failed")
        return counters.peak_ws
    import resource
    maximum = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return maximum if sys.platform == "darwin" else maximum * 1024


def timed(fn):
    wall, cpu = time.perf_counter(), time.process_time()
    result = fn()
    return result, {"wall_seconds": time.perf_counter() - wall,
                    "cpu_seconds": time.process_time() - cpu}


def one_case(path, method):
    record, reading = timed(lambda: load_json(path, MAX_INPUT_BYTES))
    program = record["program"]
    producer = {"flat_gzip": produce, "factor_legacy_gzip": produce_legacy,
                "factor_tokens_gzip": factor.produce_factorized}[method]
    certificate, construction = timed(lambda: producer(program))
    representation = "flat" if method == "flat_gzip" else "factor"
    def serialize():
        source = compact(program)
        raw = compact(certificate)
        wire = _encode_raw(raw, representation, compressed=True)
        return source, len(raw), wire
    (source, raw_bytes, wire), serialization = timed(serialize)
    # Receiver starts with separate source bytes and the same complete evidence.
    # Do not retain the Python source/certificate while measuring reception.
    del program, record, certificate
    def receive():
        from rrc.schema import parse_json_bytes
        return accept(parse_json_bytes(source, MAX_INPUT_BYTES), wire, reuse_diagram=True)
    checked, reception = timed(receive)
    stages = {"source_read_parse": reading, "construction": construction,
              "source_certificate_serialization_gzip": serialization, "decode_accept": reception}
    return {"case": path.stem, "assignments": checked["checked"]["assignments"],
            "source_bytes": len(source), "certificate_raw_bytes": raw_bytes,
            "wire_bytes": len(wire), "total_bytes": len(source) + len(wire),
            "stages": stages,
            **{"pipeline_" + key: sum(stage[key] for stage in stages.values()) for key in reading}}


def worker(method, allocations):
    require(method in METHODS, "measurement path")
    corpus = paths()
    gc.collect()
    if allocations:
        tracemalloc.start()
    wall, cpu = time.perf_counter(), time.process_time()
    for path in corpus:
        row = one_case(path, method)
        print(json.dumps({"case_record": row}, sort_keys=True), flush=True)
        del row
    traced = tracemalloc.get_traced_memory()[1] if allocations else None
    if allocations:
        tracemalloc.stop()
    print(json.dumps({"worker_summary": {"method": method, "allocation_profile": allocations,
          "peak_rss_bytes": peak_rss_bytes(), "peak_traced_bytes": traced,
          "corpus_wall_seconds": time.perf_counter() - wall,
          "corpus_cpu_seconds": time.process_time() - cpu}}, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--worker", choices=METHODS, help=argparse.SUPPRESS)
    parser.add_argument("--allocations", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        worker(args.worker, args.allocations)
        return
    require(args.output is not None and not args.output.exists(), "fresh output file required")
    require(1 <= args.repeats <= 5, "bounded repeats")
    verification = verify()
    measurements = {method: {"timing_passes": [], "allocation_pass": None} for method in METHODS}
    for repetition in range(args.repeats + 1):
        allocation_profile = repetition == args.repeats
        shift = repetition % len(METHODS)
        for method in METHODS[shift:] + METHODS[:shift]:
            command = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker", method]
            if allocation_profile:
                command.append("--allocations")
            completed = subprocess.run(command, capture_output=True, text=True, check=True, timeout=120)
            events = [json.loads(line) for line in completed.stdout.splitlines()]
            rows = [event["case_record"] for event in events if "case_record" in event]
            require(len(rows) == 664 and sum(row["assignments"] for row in rows) == 32139,
                    "complete measurement population")
            observation = {**events[-1]["worker_summary"], "records": rows}
            if allocation_profile:
                measurements[method]["allocation_pass"] = observation
            else:
                measurements[method]["timing_passes"].append(observation)
            print(f"{method}: {'allocation' if allocation_profile else 'timing'} pass {repetition + 1} complete",
                  flush=True)
    totals = {}
    for method, samples in measurements.items():
        passes = samples["timing_passes"]
        rows = passes[0]["records"]
        totals[method] = {**{key: sum(row[key] for row in rows) for key in
                             ("source_bytes", "certificate_raw_bytes", "wire_bytes", "total_bytes")},
                         **{key: statistics.median(sum(row[key] for row in sample["records"])
                                                  for sample in passes)
                            for key in ("pipeline_wall_seconds", "pipeline_cpu_seconds")},
                         "peak_rss_bytes_max": max(sample["peak_rss_bytes"] for sample in passes),
                         "peak_traced_bytes": samples["allocation_pass"]["peak_traced_bytes"],
                         "stage_median_totals": {stage: {key: statistics.median(
                             sum(row["stages"][stage][key] for row in sample["records"]) for sample in passes)
                             for key in ("wall_seconds", "cpu_seconds")}
                             for stage in rows[0]["stages"]}}
    result = {"scope": "complete finite evidence; no new Java or native-analyzer validation",
              "python": platform.python_version(), "platform": platform.platform(),
              "protocol": "3 rotated fresh-process timing passes by default; separate allocation pass; one path live",
              "accounting": "source read/parse, creation, source/certificate serialization, gzip/frame, decode/full acceptance; disk read included, network and process startup excluded from stage totals; OS peak includes interpreter/imports/native allocations; traced peak excludes pre-imports and does not equal RSS; profiled times are not used for speed comparisons",
              "repeats": args.repeats, "verification": verification, "totals": totals,
              "measurements": measurements}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"verification": {key: value for key, value in verification.items() if key != "records"},
                      "totals": totals}, indent=2))


if __name__ == "__main__":
    main()
