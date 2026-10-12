"""Bounded same-information transport for flat or factorized finite certificates.

No new proof system: decoded evidence goes to the existing independent checker.
The five-byte frame identifies format/codec; gzip must be one complete member.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import sys
from typing import Any
import zlib

from .checker import check
from .factor_checker import check_factorized
from .schema import Invalid, MAX_CERT_BYTES, parse_json_bytes, require

MAGIC = b"RRC1"
TAGS = {("flat", False): b"f", ("factor", False): b"d",
        ("flat", True): b"F", ("factor", True): b"D"}
# gzip can slightly expand an incompressible admitted object; bound both stages.
MAX_WIRE_BYTES = MAX_CERT_BYTES + 65536 + 5


def compact(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def encode(certificate: Any, representation: str, *, compressed: bool) -> bytes:
    return _encode_raw(compact(certificate), representation, compressed=compressed)


def _encode_raw(raw: bytes, representation: str, *, compressed: bool) -> bytes:
    require((representation, compressed) in TAGS, "transport format/codec")
    require(len(raw) <= MAX_CERT_BYTES, "certificate byte bound")
    payload = gzip.compress(raw, compresslevel=9, mtime=0) if compressed else raw
    wire = MAGIC + TAGS[representation, compressed] + payload
    require(len(wire) <= MAX_WIRE_BYTES, "transport byte bound")
    return wire


def choose(flat_wire: bytes | None, factor_wire: bytes | None) -> bytes:
    """Choose by actual full-frame length; tie goes to the simpler flat format.

    Producer-side choice is untrusted. No semantic property follows from this function.
    An over-cap representation is omitted by the producer, not admitted after gzip.
    """
    candidates = [wire for wire in (flat_wire, factor_wire) if wire is not None]
    require(bool(candidates), "no admitted representation")
    return min(candidates, key=len)


def decode(wire: bytes) -> tuple[str, Any]:
    require(type(wire) is bytes and 5 < len(wire) <= MAX_WIRE_BYTES,
            "transport byte bound")
    require(wire[:4] == MAGIC, "transport version")
    inverse = {tag: pair for pair, tag in TAGS.items()}
    require(wire[4:5] in inverse, "transport format/codec")
    representation, compressed = inverse[wire[4:5]]
    payload = wire[5:]
    if compressed:
        try:
            decoder = zlib.decompressobj(wbits=31)
            raw = decoder.decompress(payload, MAX_CERT_BYTES + 1)
            require(len(raw) <= MAX_CERT_BYTES, "decompressed byte bound")
            require(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,
                    "incomplete or trailing gzip data")
        except zlib.error as exc:
            raise Invalid("invalid gzip payload") from exc
    else:
        raw = payload
    return representation, parse_json_bytes(raw, MAX_CERT_BYTES)


def accept(program: dict[str, Any], wire: bytes, *, reuse_diagram: bool = True) -> dict[str, Any]:
    representation, certificate = decode(wire)
    checked = (check(program, certificate) if representation == "flat" else
               check_factorized(program, certificate, reuse_diagram=reuse_diagram))
    return {"representation": representation, "checked": checked}


def produce_transport(program: dict[str, Any]) -> bytes:
    from .producer import produce
    from .factor import produce_factorized

    candidates = {"flat": None, "factor": None}
    for representation, producer in (("flat", produce), ("factor", produce_factorized)):
        certificate = producer(program)
        raw = compact(certificate)
        if len(raw) <= MAX_CERT_BYTES:
            candidates[representation] = _encode_raw(raw, representation, compressed=True)
    return choose(candidates["flat"], candidates["factor"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("produce", "check"):
        child = sub.add_parser(command)
        child.add_argument("--source", required=True, type=Path)
        child.add_argument("--wire", required=True, type=Path)
    args = parser.parse_args()
    try:
        from .__main__ import read_program, _fresh_result_path
        program = read_program(args.source)
        if args.command == "produce":
            output = _fresh_result_path(args.wire)
            wire = produce_transport(program)
            result = accept(program, wire)
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("xb") as stream:
                stream.write(wire)
        else:
            with args.wire.open("rb") as stream:
                wire = stream.read(MAX_WIRE_BYTES + 1)
            result = accept(program, wire)
        print(json.dumps({"status": "accepted", "wire_bytes": len(wire),
                          "representation": result["representation"],
                          "assignments": result["checked"]["assignments"]}, sort_keys=True))
        return 0
    except (Invalid, OSError, ValueError) as exc:
        print(json.dumps({"status": "rejected", "reason": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
