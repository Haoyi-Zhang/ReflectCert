"""Shared trusted syntax/size checks, not a shared semantic evaluator.

The input describes a finite collection of lookup probes. It is deliberately
not a parser for Java or an implementation of JVM reflection.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

MAX_INPUT_BYTES = 128 * 1024
MAX_CERT_BYTES = 16 * 1024 * 1024
MAX_BITS = 12
MAX_EXTERNAL = 8
MAX_CHOICES = 4
MAX_NODES = 64
MAX_SITES = 8
MAX_TABLE = 256
MAX_STRING = 48

class Invalid(ValueError):
    """Invalid or outside the explicitly bounded input language."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Invalid(message)


def exact_keys(value: Any, keys: set[str], where: str) -> None:
    require(type(value) is dict and set(value) == keys, f"{where}: fields")


def text(value: Any, where: str) -> None:
    require(type(value) is str, f"{where}: string required")
    try:
        b = value.encode("ascii")
    except UnicodeError as exc:
        raise Invalid(f"{where}: ASCII required") from exc
    require(len(b) <= MAX_STRING, f"{where}: string bound")


def strict_equal(a: Any, b: Any) -> bool:
    """Unlike Python equality, do not equate a JSON boolean with a number."""
    return json.dumps(a, sort_keys=True, separators=(",", ":"), allow_nan=False) == json.dumps(
        b, sort_keys=True, separators=(",", ":"), allow_nan=False)


def validate(p: Any) -> dict[str, Any]:
    exact_keys(p, {"external", "choices", "nodes", "feasible", "table", "sites"}, "program")
    for k, limit in (("external", MAX_EXTERNAL), ("choices", MAX_CHOICES)):
        require(type(p[k]) is list and len(p[k]) <= limit, f"{k}: bound")
        for s in p[k]:
            text(s, k)
            require(bool(s), f"{k}: empty name")
    names = p["external"] + p["choices"]
    require(len(names) == len(set(names)) and len(names) <= MAX_BITS, "duplicate/input bound")
    nodes = p["nodes"]
    require(type(nodes) is list and 1 <= len(nodes) <= MAX_NODES, "node bound")
    sorts: list[str] = []
    widths: list[int] = []
    dependencies: list[set[int]] = []
    for i, node in enumerate(nodes):
        require(type(node) is dict and type(node.get("op")) is str, "node: operation")
        op = node["op"]
        if op == "lit":
            exact_keys(node, {"op", "value"}, "literal")
            v = node["value"]
            require(type(v) in (str, bool), "literal: sort")
            if type(v) is str:
                text(v, "literal")
            sorts.append("bool" if type(v) is bool else "str")
            widths.append(len(v) if type(v) is str else 0)
            dependencies.append(set())
            continue
        if op == "input":
            exact_keys(node, {"op", "index"}, "input")
            j = node["index"]
            require(type(j) is int and 0 <= j < len(names), "input: index")
            sorts.append("bool"); widths.append(0); dependencies.append({j})
            continue
        arities = {"alias": 1, "not": 1, "and": 2, "or": 2, "eq": 2, "cat": 2, "ite": 3}
        require(op in arities, "unsupported operation")
        exact_keys(node, {"op", "args"}, op)
        args = node["args"]
        require(type(args) is list and len(args) == arities[op], f"{op}: arity")
        require(all(type(j) is int and 0 <= j < i for j in args), "non-topological reference")
        ss = [sorts[j] for j in args]
        if op in ("not", "and", "or"):
            require(all(s == "bool" for s in ss), "boolean operands")
            out, width = "bool", 0
        elif op == "eq":
            require(ss[0] == ss[1], "equality sorts")
            out, width = "bool", 0
        elif op == "cat":
            require(ss == ["str", "str"], "concatenation sorts")
            out, width = "str", sum(widths[j] for j in args)
        elif op == "ite":
            require(ss[0] == "bool" and ss[1] == ss[2], "conditional sorts")
            out, width = ss[1], max(widths[j] for j in args[1:])
        else:
            out, width = ss[0], widths[args[0]]
        require(width <= MAX_STRING, "static string-width bound")
        sorts.append(out); widths.append(width)
        dependencies.append(set().union(*(dependencies[j] for j in args)))
    def ref(j: Any, sort: str) -> None:
        require(type(j) is int and 0 <= j < len(nodes) and sorts[j] == sort, "reference/sort")
    ref(p["feasible"], "bool")
    require(all(j < len(p["external"]) for j in dependencies[p["feasible"]]),
            "feasibility cannot depend on internal choices")
    table = p["table"]
    require(type(table) is list and len(table) <= MAX_TABLE, "class-table bound")
    for entry in table:
        require(type(entry) is list and len(entry) == 4, "table entry")
        for field in entry:
            text(field, "table field")
    require(len(set(map(tuple, table))) == len(table), "duplicate target identity")
    sites = p["sites"]
    require(type(sites) is list and 1 <= len(sites) <= MAX_SITES, "site bound")
    for site in sites:
        exact_keys(site, {"guard", "loader", "class", "method", "signature"}, "site")
        ref(site["guard"], "bool")
        for field in ("loader", "class", "method", "signature"):
            ref(site[field], "str")
    return p


def load_json(path: str | Path, max_bytes: int) -> Any:
    """Bound input bytes before JSON parsing, and reject duplicate object keys."""
    with Path(path).open("rb") as stream:
        raw = stream.read(max_bytes + 1)
    require(len(raw) <= max_bytes, "input byte bound")
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, v in items:
            require(k not in out, "duplicate JSON key")
            out[k] = v
        return out
    try:
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(Invalid("non-finite JSON")))
    except (ValueError, RecursionError, UnicodeError) as exc:
        raise Invalid("invalid or excessively nested JSON") from exc
