"""Separately implemented recursive checker. No producer import/evaluator.

The trusted boundary includes this module, schema validation, Python, the input
contract and the supplied source; it does NOT include the producer. This is an
independent implementation, not an independently authored or verified checker.
"""
from __future__ import annotations
from typing import Any
from .schema import Invalid, exact_keys, require, strict_equal, validate


def decode(index: int, width: int) -> list[bool]:
    return [bool(index & (1 << (width - j - 1))) for j in range(width)]


def check(p: dict[str, Any], cert: Any) -> dict[str, Any]:
    validate(p)
    exact_keys(cert, {"program", "rows", "summary"}, "certificate")
    require(strict_equal(cert["program"], p), "source binding")
    rows = cert["rows"]
    n, ne, nc = len(p["external"]) + len(p["choices"]), len(p["external"]), len(p["choices"])
    require(type(rows) is list and len(rows) == 1 << n, "assignment coverage")
    sets: dict[int, list[set[tuple[str, ...]]]] = {}
    steps = 0
    for number in range(1 << n):
        row = rows[number]
        exact_keys(row, {"index", "input", "values", "feasible", "outcomes"}, "row")
        require(type(row["index"]) is int and row["index"] == number, "ordered assignment identity")
        bits = decode(number, n)
        require(strict_equal(row["input"], bits), "assignment input")
        cache: dict[int, Any] = {}
        def visit(j: int) -> Any:
            nonlocal steps
            if j in cache:
                return cache[j]
            steps += 1
            node = p["nodes"][j]
            op = node["op"]
            if op == "lit": out = node["value"]
            elif op == "input": out = bits[node["index"]]
            elif op == "alias": out = visit(node["args"][0])
            elif op == "ite":
                condition, yes, no = node["args"]
                out = visit(yes) if visit(condition) is True else visit(no)
            elif op == "not": out = visit(node["args"][0]) is False
            elif op == "and": out = all(visit(k) is True for k in node["args"])
            elif op == "or": out = any(visit(k) is True for k in node["args"])
            elif op == "eq": out = strict_equal(visit(node["args"][0]), visit(node["args"][1]))
            elif op == "cat": out = "".join(visit(k) for k in node["args"])
            else: raise Invalid("unknown operation")
            cache[j] = out
            return out
        # Checking all node values also checks deliberately unreachable nodes.
        expect_values = [visit(j) for j in range(len(p["nodes"]))]
        require(strict_equal(row["values"], expect_values), "node derivation")
        feasible = visit(p["feasible"])
        require(type(row["feasible"]) is bool and row["feasible"] is feasible, "feasibility")
        outputs = []
        wi = number >> nc
        if feasible:
            if wi not in sets:
                sets[wi] = [set() for _ in p["sites"]]
            for s, probe in enumerate(p["sites"]):
                steps += 1
                if visit(probe["guard"]) is False:
                    outputs.append({"kind": "skipped"})
                    continue
                target = [visit(probe[k]) for k in ("loader", "class", "method", "signature")]
                # Deliberately use linear exact identity search, not producer's set lookup.
                found = any(strict_equal(candidate, target) for candidate in p["table"])
                outputs.append({"kind": "target" if found else "lookup_error", "key": target})
                if found:
                    sets[wi][s].add(tuple(target))
        require(strict_equal(row["outcomes"], outputs), "probe outcome")
    worlds = [{"index": wi, "external": decode(wi, ne),
               "targets": [[list(k) for k in sorted(ts)] for ts in sets[wi]]} for wi in sorted(sets)]
    may, robust = [], []
    for s in range(len(p["sites"])):
        union = {k for wi in sets for k in sets[wi][s]}
        may.append([list(k) for k in sorted(union)])
        robust.append([list(k) for k in sorted(union) if all(k in sets[wi][s] for wi in sets)] if sets else None)
    summary = {"worlds": worlds, "may": may, "robust": robust}
    require(strict_equal(cert["summary"], summary), "target-set aggregation")
    return {"summary": summary, "checker_steps": steps, "assignments": 1 << n}


def check_observation(checked: dict[str, Any], evidence: Any) -> bool:
    exact_keys(evidence, {"site", "base", "selected", "necessity"}, "observation certificate")
    worlds = checked["summary"]["worlds"]
    site, base, selected = evidence["site"], evidence["base"], evidence["selected"]
    require(type(site) is int and 0 <= site < len(checked["summary"]["may"]), "site identity")
    require(type(base) is int, "base identity")
    byid = {w["index"]: w for w in worlds}
    require(base in byid, "feasible base")
    b = byid[base]
    require(type(selected) is list and all(type(j) is int and 0 <= j < len(b["external"]) for j in selected), "selected indices")
    require(selected == sorted(set(selected)), "selected uniqueness/order")
    def matches(w: dict[str, Any], keep: list[int]) -> bool:
        return all(w["external"][j] is b["external"][j] for j in keep)
    require(all(w["targets"][site] == b["targets"][site] for w in worlds if matches(w, selected)),
            "observation is insufficient")
    necessity = evidence["necessity"]
    require(type(necessity) is list and len(necessity) == len(selected), "necessity coverage")
    for j, witness in zip(selected, necessity):
        exact_keys(witness, {"removed", "world"}, "necessity witness")
        require(type(witness["removed"]) is int and witness["removed"] == j, "necessity identity")
        wi = witness["world"]
        require(type(wi) is int and wi in byid, "necessity feasibility")
        w = byid[wi]
        require(matches(w, [k for k in selected if k != j]) and w["targets"][site] != b["targets"][site],
                "false necessity witness")
    return True
