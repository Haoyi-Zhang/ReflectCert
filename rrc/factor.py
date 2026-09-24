"""Untrusted factorized certificate producer.

The format replaces one value/outcome record per assignment with a shared reduced
ordered multi-terminal decision diagram (MTBDD).  It changes transfer size, not the
finite semantic contract: the checker still validates every assignment independently.
"""
from __future__ import annotations

import copy
import itertools
import json
from typing import Any, Iterable

from .schema import strict_equal, validate

FORMAT = "factorized-target-certificate"


def bit_rows(n: int) -> Iterable[tuple[bool, ...]]:
    return itertools.product((False, True), repeat=n)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


class SharedMTBDD:
    """Hash-consed ordered decision DAG shared across all certified functions."""

    def __init__(self, width: int):
        self.width = width
        self.nodes: list[dict[str, Any]] = []
        self._terminal_ids: dict[str, int] = {}
        self._branch_ids: dict[tuple[int, int, int], int] = {}
        self._memo: dict[tuple[int, tuple[str, ...]], int] = {}

    def terminal(self, value: Any) -> int:
        key = _canonical(value)
        found = self._terminal_ids.get(key)
        if found is not None:
            return found
        node_id = len(self.nodes)
        self.nodes.append({"kind": "terminal", "value": copy.deepcopy(value)})
        self._terminal_ids[key] = node_id
        return node_id

    def branch(self, var: int, low: int, high: int) -> int:
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

    def build(self, values: list[Any], var: int = 0) -> int:
        expected = 1 << (self.width - var)
        if len(values) != expected:
            raise ValueError("diagram vector width")
        enc = tuple(_canonical(v) for v in values)
        memo_key = (var, enc)
        found = self._memo.get(memo_key)
        if found is not None:
            return found
        if all(x == enc[0] for x in enc[1:]):
            root = self.terminal(values[0])
        else:
            if var >= self.width:
                raise AssertionError("different values without a decision variable")
            half = len(values) // 2
            root = self.branch(var, self.build(values[:half], var + 1), self.build(values[half:], var + 1))
        self._memo[memo_key] = root
        return root


def _evaluate_all(program: dict[str, Any]) -> tuple[list[list[Any]], list[bool], list[list[dict[str, Any]]]]:
    """Eager topological evaluation, deliberately separate from the recursive checker."""
    width = len(program["external"]) + len(program["choices"])
    value_vectors = [[] for _ in program["nodes"]]
    feasible_vector: list[bool] = []
    outcome_vectors = [[] for _ in program["sites"]]
    table = set(map(tuple, program["table"]))
    for bits in bit_rows(width):
        values: list[Any] = []
        for node in program["nodes"]:
            op = node["op"]
            args = [values[j] for j in node.get("args", [])]
            if op == "lit":
                value = node["value"]
            elif op == "input":
                value = bits[node["index"]]
            elif op == "alias":
                value = args[0]
            elif op == "not":
                value = not args[0]
            elif op == "and":
                value = args[0] and args[1]
            elif op == "or":
                value = args[0] or args[1]
            elif op == "eq":
                value = strict_equal(args[0], args[1])
            elif op == "cat":
                value = args[0] + args[1]
            elif op == "ite":
                value = args[1] if args[0] is True else args[2]
            else:
                raise AssertionError("validated operation")
            values.append(value)
        for j, value in enumerate(values):
            value_vectors[j].append(value)
        feasible = values[program["feasible"]]
        feasible_vector.append(feasible)
        for site_no, site in enumerate(program["sites"]):
            if not feasible:
                outcome = {"kind": "infeasible"}
            elif values[site["guard"]] is False:
                outcome = {"kind": "skipped"}
            else:
                key = [values[site[field]] for field in ("loader", "class", "method", "signature")]
                outcome = {"kind": "target" if tuple(key) in table else "lookup_error", "key": key}
            outcome_vectors[site_no].append(outcome)
    return value_vectors, feasible_vector, outcome_vectors


def _summary(program: dict[str, Any], outcomes: list[list[dict[str, Any]]], feasible: list[bool]) -> dict[str, Any]:
    ne = len(program["external"])
    nc = len(program["choices"])
    worlds: list[dict[str, Any]] = []
    for world_index, external in enumerate(bit_rows(ne)):
        row0 = world_index << nc
        if not feasible[row0]:
            continue
        targets: list[list[list[str]]] = []
        for site_no in range(len(program["sites"])):
            values = {
                tuple(outcomes[site_no][row]["key"])
                for row in range(row0, row0 + (1 << nc))
                if outcomes[site_no][row]["kind"] == "target"
            }
            targets.append([list(target) for target in sorted(values)])
        worlds.append({"index": world_index, "external": list(external), "targets": targets})
    may: list[list[list[str]]] = []
    robust: list[list[list[str]] | None] = []
    for site_no in range(len(program["sites"])):
        sets = [set(map(tuple, world["targets"][site_no])) for world in worlds]
        union = set().union(*sets) if sets else set()
        may.append([list(target) for target in sorted(union)])
        robust.append([list(target) for target in sorted(set.intersection(*sets))] if sets else None)
    return {"worlds": worlds, "may": may, "robust": robust}


def produce_factorized(program: dict[str, Any]) -> dict[str, Any]:
    validate(program)
    width = len(program["external"]) + len(program["choices"])
    values, feasible, outcomes = _evaluate_all(program)
    diagram = SharedMTBDD(width)
    value_roots = [diagram.build(vector) for vector in values]
    feasible_root = diagram.build(feasible)
    outcome_roots = [diagram.build(vector) for vector in outcomes]
    return {
        "format": FORMAT,
        "program": copy.deepcopy(program),
        "bit_order": list(program["external"] + program["choices"]),
        "diagram": {"nodes": diagram.nodes},
        "roots": {"values": value_roots, "feasible": feasible_root, "outcomes": outcome_roots},
        "summary": _summary(program, outcomes, feasible),
    }


def serialized_bytes(certificate: dict[str, Any]) -> int:
    return len(json.dumps(certificate, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8"))
