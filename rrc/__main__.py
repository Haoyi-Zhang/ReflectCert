"""Produce or check bounded factorized reflection-resolution evidence.

This command operates on the repository's finite source language; Java extraction is a
separate producer-side bridge in ``rrc.java_frontend``.  The checker receives the finite
source separately from the certificate bundle.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

from .factor_checker import check_factorized
from .dispatch_checker import check_direct_dispatch
from .missing_witness import check_missing_target_witness, produce_missing_target_witness
from .schema import Invalid, MAX_CERT_BYTES, MAX_INPUT_BYTES, exact_keys, load_json, require

ROOT = Path(__file__).resolve().parent.parent
BUNDLE_FORMAT = "reflection-resolution-evidence"


def read_program(path: Path) -> dict[str, Any]:
    record = load_json(path, MAX_INPUT_BYTES)
    require(type(record) is dict, "input record must be an object")
    require(set(record) in ({"label", "program"}, {"label", "program", "expected_rows"}),
            "input record fields")
    require(type(record["label"]) is str, "input label")
    return record["program"]


def verify_bundle(program: dict[str, Any], bundle: Any) -> dict[str, Any]:
    exact_keys(bundle, {"format", "factorized_certificate", "direct_dispatch",
                        "missing_target_witnesses"}, "evidence bundle")
    require(bundle["format"] == BUNDLE_FORMAT, "evidence bundle format")
    checked = check_factorized(program, bundle["factorized_certificate"])
    dispatch_checked = check_direct_dispatch(program, bundle["direct_dispatch"])
    witnesses = bundle["missing_target_witnesses"]
    require(type(witnesses) is list and len(witnesses) <= 4096, "missing-target witness count")
    for evidence in witnesses:
        check_missing_target_witness(checked["summary"], evidence)
    checked["direct_dispatch"] = dispatch_checked
    return checked


def _fresh_result_path(path: Path) -> Path:
    output = path.resolve()
    try:
        output.relative_to((ROOT / "results").resolve())
    except ValueError as exc:
        raise Invalid("output must be inside the repository results directory") from exc
    require(not output.exists(), "output already exists; choose a fresh path")
    return output


def _witnesses_for(program: dict[str, Any], certificate: dict[str, Any], site: int,
                   base_index: int, target_number: int) -> list[dict[str, Any]]:
    checked = check_factorized(program, certificate)
    summary = checked["summary"]
    require(0 <= site < len(summary["may"]), "site identity")
    by_id = {world["index"]: world for world in summary["worlds"]}
    require(base_index in by_id, "base must identify a feasible external world")
    base_targets = by_id[base_index]["targets"][site]
    require(base_targets, "selected base/site has no possible target")
    require(0 <= target_number < len(base_targets), "target number")
    target = base_targets[target_number]
    claimed = [candidate for candidate in summary["may"][site] if candidate != target]
    forward = produce_missing_target_witness(summary, site, target, claimed, base_index, reverse=False)
    reverse = produce_missing_target_witness(summary, site, target, claimed, base_index, reverse=True)
    return [forward] if forward == reverse else [forward, reverse]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser("check", help="check a factorized certificate and all omission witnesses")
    verify.add_argument("--source", required=True, type=Path)
    verify.add_argument("--evidence", required=True, type=Path)

    create = sub.add_parser("produce", help="produce a factorized certificate and optional witnesses")
    create.add_argument("--source", required=True, type=Path)
    create.add_argument("--output", required=True, type=Path)
    create.add_argument("--base", type=int, help="feasible external-world index for an omission witness")
    create.add_argument("--site", type=int, default=0)
    create.add_argument("--target-number", type=int, default=0,
                        help="index in the selected base world's sorted target list")
    args = parser.parse_args()

    try:
        program = read_program(args.source)
        if args.command == "check":
            bundle = load_json(args.evidence, MAX_CERT_BYTES)
            checked = verify_bundle(program, bundle)
        else:
            from .factor import produce_factorized
            from .dispatch import produce_direct_dispatch

            output = _fresh_result_path(args.output)
            certificate = produce_factorized(program)
            direct_dispatch = produce_direct_dispatch(program, certificate)
            witnesses = [] if args.base is None else _witnesses_for(
                program, certificate, args.site, args.base, args.target_number)
            bundle = {
                "format": BUNDLE_FORMAT,
                "factorized_certificate": certificate,
                "direct_dispatch": direct_dispatch,
                "missing_target_witnesses": witnesses,
            }
            checked = verify_bundle(program, bundle)
            raw = (json.dumps(bundle, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
            require(len(raw) <= MAX_CERT_BYTES, "evidence bundle byte bound")
            output.parent.mkdir(parents=True, exist_ok=True)
            temporary = output.with_name(output.name + ".tmp")
            with temporary.open("wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, output)

        print(json.dumps({
            "status": "accepted",
            "assignments": checked["assignments"],
            "semantic_steps": checked["semantic_steps"],
            "diagram_steps": checked["diagram_steps"],
            "diagram_nodes": checked["diagram_nodes"],
            "feasible_worlds": len(checked["summary"]["worlds"]),
            "missing_target_witnesses_checked": len(bundle["missing_target_witnesses"]),
            "direct_dispatch_nodes": checked["direct_dispatch"]["diagram_nodes"],
            "direct_trace_events": checked["direct_dispatch"]["trace_events"],
        }, sort_keys=True))
        return 0
    except (Invalid, OSError, ValueError) as exc:
        print(json.dumps({"status": "rejected", "reason": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
