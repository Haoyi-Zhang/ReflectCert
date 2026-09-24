"""Untrusted certificate producer: eager, topological evaluation of all rows."""
from __future__ import annotations
import copy
import itertools
from typing import Any
from .schema import validate


def bit_rows(n: int):
    return itertools.product((False, True), repeat=n)


def evaluate(p: dict[str, Any], bits: tuple[bool, ...]) -> list[Any]:
    values: list[Any] = []
    for node in p["nodes"]:
        op = node["op"]
        a = [values[j] for j in node.get("args", [])]
        if op == "lit": value = node["value"]
        elif op == "input": value = bits[node["index"]]
        elif op == "alias": value = a[0]
        elif op == "not": value = not a[0]
        elif op == "and": value = a[0] and a[1]
        elif op == "or": value = a[0] or a[1]
        elif op == "eq": value = a[0] == a[1]
        elif op == "cat": value = a[0] + a[1]
        elif op == "ite": value = a[1] if a[0] else a[2]
        else: raise AssertionError("schema did not reject operation")
        values.append(value)
    return values


def lookup(p: dict[str, Any], v: list[Any]) -> list[dict[str, Any]]:
    outcomes = []
    table = set(map(tuple, p["table"]))
    for s in p["sites"]:
        if not v[s["guard"]]:
            outcomes.append({"kind": "skipped"})
        else:
            key = [v[s[k]] for k in ("loader", "class", "method", "signature")]
            outcomes.append({"kind": "target" if tuple(key) in table else "lookup_error", "key": key})
    return outcomes


def aggregate(p: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    ne, nc, ns = len(p["external"]), len(p["choices"]), len(p["sites"])
    worlds = []
    for wi, h in enumerate(bit_rows(ne)):
        group = rows[wi * (1 << nc):(wi + 1) * (1 << nc)]
        if not group[0]["feasible"]:
            continue
        targets = [sorted({tuple(r["outcomes"][s]["key"]) for r in group
                           if r["outcomes"][s]["kind"] == "target"}) for s in range(ns)]
        worlds.append({"index": wi, "external": list(h), "targets": [[list(t) for t in ts] for ts in targets]})
    may, robust = [], []
    for s in range(ns):
        sets = [set(map(tuple, w["targets"][s])) for w in worlds]
        may.append([list(t) for t in sorted(set().union(*sets))])
        robust.append([list(t) for t in sorted(set.intersection(*sets))] if sets else None)
    return {"worlds": worlds, "may": may, "robust": robust}


def produce(p: dict[str, Any]) -> dict[str, Any]:
    validate(p)
    rows = []
    for index, bits in enumerate(bit_rows(len(p["external"]) + len(p["choices"]))):
        v = evaluate(p, bits)
        ok = v[p["feasible"]]
        rows.append({"index": index, "input": list(bits), "values": v, "feasible": ok,
                     "outcomes": lookup(p, v) if ok else []})
    return {"program": copy.deepcopy(p), "rows": rows, "summary": aggregate(p, rows)}


def sufficient(worlds: list[dict[str, Any]], site: int, base: int, selected: set[int]) -> bool:
    b = next(w for w in worlds if w["index"] == base)
    return all(w["targets"][site] == b["targets"][site]
               for w in worlds if all(w["external"][j] == b["external"][j] for j in selected))


def observation_certificate(cert: dict[str, Any], site: int, base: int,
                            reverse: bool = False) -> dict[str, Any]:
    worlds = cert["summary"]["worlds"]
    b = next(w for w in worlds if w["index"] == base)
    selected = set(range(len(b["external"])))
    for j in sorted(selected, reverse=reverse):
        if sufficient(worlds, site, base, selected - {j}):
            selected.remove(j)
    necessity = []
    for j in sorted(selected):
        w = next(w for w in worlds if w["targets"][site] != b["targets"][site]
                 and all(w["external"][k] == b["external"][k] for k in selected - {j}))
        necessity.append({"removed": j, "world": w["index"]})
    return {"site": site, "base": base, "selected": sorted(selected), "necessity": necessity}
