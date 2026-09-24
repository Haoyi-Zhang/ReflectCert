"""Transparent local baselines, NOT executions of DroidRA, SOLAR, or COAL."""
from __future__ import annotations
import itertools
from typing import Any
from .schema import validate


def string_sets(p: dict[str, Any], constant_only: bool = False) -> list[list[list[str]]]:
    """Nonrelational value sets; constant-only variant maps multi-valued nodes to top.

For constant-only, top is represented by None and soundly expanded at lookup to
matching finite-table entries. This is not a false-negative constant resolver.
Feasibility/guard constraints are ignored except when syntactically constant.
"""
    validate(p)
    vals: list[set[Any] | None] = []
    for node in p["nodes"]:
        op = node["op"]
        if op == "lit": v = {node["value"]}
        elif op == "input": v = {False, True}
        else:
            operands = [vals[j] for j in node["args"]]
            if op == "ite" and operands[0] is None:
                # A top condition still selects between the two branch values;
                # it does not erase a common constant branch result.
                v = None if any(x is None for x in operands[1:]) else operands[1] | operands[2]
            elif op == "and" and {False} in operands:
                v = {False}
            elif op == "or" and {True} in operands:
                v = {True}
            elif op == "eq" and node["args"][0] == node["args"][1]:
                v = {True}
            elif op == "ite" and operands[0] == {True}:
                v = operands[1]
            elif op == "ite" and operands[0] == {False}:
                v = operands[2]
            elif any(x is None for x in operands):
                v = None
            else:
                v = set()
                for a in itertools.product(*operands):
                    if op == "alias": z = a[0]
                    elif op == "not": z = not a[0]
                    elif op == "and": z = a[0] and a[1]
                    elif op == "or": z = a[0] or a[1]
                    elif op == "eq": z = a[0] == a[1]
                    elif op == "cat": z = a[0] + a[1]
                    elif op == "ite": z = a[1] if a[0] else a[2]
                    else: raise AssertionError("unvalidated operator")
                    v.add(z)
                    if len(v) > 1024:
                        # Honest coarse fallback, not a truncated value set.
                        v = None
                        break
        if constant_only and v is not None and len(v) > 1: v = None
        vals.append(v)
    targets = []
    for s in p["sites"]:
        if vals[p["feasible"]] == {False} or vals[s["guard"]] == {False}:
            targets.append([]); continue
        fields = [vals[s[k]] for k in ("loader", "class", "method", "signature")]
        targets.append(sorted([t for t in p["table"] if all(v is None or x in v for x,v in zip(t,fields))]))
    return targets


def invoke_all(targets: list[list[str]]) -> list[dict[str, Any]]:
    """Deliberately wrong executable rewrite used solely as a negative control."""
    return [{"kind": "target", "key": t} for t in targets]


def dispatch_table(checked_certificate: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    """A finite per-input outcome table, not Java instrumentation.

The caller must run the checker first. Equality is only lookup-probe outcome
trace equality; no method body, exception propagation, heap or JVM claim.
"""
    return {r["index"]: r["outcomes"] for r in checked_certificate["rows"]}
