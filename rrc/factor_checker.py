"""Recursive checker for factorized reflection-target certificates.

This module does not import the producer or its diagram builder.  It validates the
submitted ordered DAG, independently evaluates the source, and compares every root
on every modeled assignment.  Factorization reduces transfer size; acceptance still
means exact finite coverage rather than a sampling claim.
"""
from __future__ import annotations

from typing import Any

from .schema import Invalid, exact_keys, require, strict_equal, validate

FORMAT = "factorized-target-certificate"
MAX_DIAGRAM_NODES = 131072


def decode(index: int, width: int) -> list[bool]:
    return [bool(index & (1 << (width - position - 1))) for position in range(width)]


def _canonical(value: Any) -> str:
    import json
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _validate_diagram(nodes: Any, width: int) -> None:
    require(type(nodes) is list and 1 <= len(nodes) <= MAX_DIAGRAM_NODES, "diagram node bound")
    branch_vars: list[int | None] = []
    terminals: set[str] = set()
    branches: set[tuple[int, int, int]] = set()
    for node_id, node in enumerate(nodes):
        require(type(node) is dict and type(node.get("kind")) is str, "diagram node")
        if node["kind"] == "terminal":
            exact_keys(node, {"kind", "value"}, "terminal")
            key = _canonical(node["value"])
            require(key not in terminals, "duplicate terminal")
            terminals.add(key)
            branch_vars.append(None)
            continue
        require(node["kind"] == "branch", "diagram node kind")
        exact_keys(node, {"kind", "var", "low", "high"}, "branch")
        var, low, high = node["var"], node["low"], node["high"]
        require(type(var) is int and 0 <= var < width, "branch variable")
        require(type(low) is int and type(high) is int and 0 <= low < node_id and 0 <= high < node_id,
                "branch child order")
        require(low != high, "unreduced branch")
        branch_key = (var, low, high)
        require(branch_key not in branches, "duplicate branch")
        branches.add(branch_key)
        for child in (low, high):
            child_var = branch_vars[child]
            require(child_var is None or child_var > var, "ordered decision path")
        branch_vars.append(var)


def _validate_reachability(nodes: list[dict[str, Any]], roots: list[int]) -> None:
    reachable: set[int] = set()
    pending = list(roots)
    while pending:
        node_id = pending.pop()
        require(type(node_id) is int and 0 <= node_id < len(nodes), "diagram root")
        if node_id in reachable:
            continue
        reachable.add(node_id)
        node = nodes[node_id]
        if node["kind"] == "branch":
            pending.extend((node["low"], node["high"]))
    require(len(reachable) == len(nodes), "unreachable diagram node")


def _diagram_value(nodes: list[dict[str, Any]], root: int, bits: list[bool]) -> tuple[Any, int]:
    require(type(root) is int and 0 <= root < len(nodes), "diagram root")
    node_id = root
    visits = 0
    while True:
        visits += 1
        node = nodes[node_id]
        if node["kind"] == "terminal":
            return node["value"], visits
        node_id = node["high"] if bits[node["var"]] else node["low"]


def check_factorized(program: dict[str, Any], certificate: Any) -> dict[str, Any]:
    validate(program)
    exact_keys(certificate, {"format", "program", "bit_order", "diagram", "roots", "summary"},
               "factorized certificate")
    require(certificate["format"] == FORMAT, "certificate format")
    require(strict_equal(certificate["program"], program), "source binding")
    bit_order = certificate["bit_order"]
    require(strict_equal(bit_order, program["external"] + program["choices"]), "bit order")
    width = len(bit_order)
    exact_keys(certificate["diagram"], {"nodes"}, "diagram")
    nodes = certificate["diagram"]["nodes"]
    _validate_diagram(nodes, width)
    roots = certificate["roots"]
    exact_keys(roots, {"values", "feasible", "outcomes"}, "diagram roots")
    require(type(roots["values"]) is list and len(roots["values"]) == len(program["nodes"]), "value roots")
    require(type(roots["outcomes"]) is list and len(roots["outcomes"]) == len(program["sites"]), "outcome roots")
    require(type(roots["feasible"]) is int, "feasibility root")
    all_roots = roots["values"] + [roots["feasible"]] + roots["outcomes"]
    require(all(type(root) is int for root in all_roots), "diagram roots")
    _validate_reachability(nodes, all_roots)

    ne, nc = len(program["external"]), len(program["choices"])
    sets: dict[int, list[set[tuple[str, ...]]]] = {}
    semantic_steps = 0
    diagram_steps = 0
    for number in range(1 << width):
        bits = decode(number, width)
        cache: dict[int, Any] = {}

        def visit(node_id: int) -> Any:
            nonlocal semantic_steps
            if node_id in cache:
                return cache[node_id]
            semantic_steps += 1
            node = program["nodes"][node_id]
            op = node["op"]
            if op == "lit":
                value = node["value"]
            elif op == "input":
                value = bits[node["index"]]
            elif op == "alias":
                value = visit(node["args"][0])
            elif op == "not":
                value = visit(node["args"][0]) is False
            elif op == "and":
                value = all(visit(arg) is True for arg in node["args"])
            elif op == "or":
                value = any(visit(arg) is True for arg in node["args"])
            elif op == "eq":
                value = strict_equal(visit(node["args"][0]), visit(node["args"][1]))
            elif op == "cat":
                value = "".join(visit(arg) for arg in node["args"])
            elif op == "ite":
                cond, yes, no = node["args"]
                value = visit(yes) if visit(cond) is True else visit(no)
            else:
                raise Invalid("unknown operation")
            cache[node_id] = value
            return value

        expected_values = [visit(node_id) for node_id in range(len(program["nodes"]))]
        for root, expected in zip(roots["values"], expected_values):
            actual, visits = _diagram_value(nodes, root, bits)
            diagram_steps += visits
            require(strict_equal(actual, expected), "factorized node derivation")
        feasible = visit(program["feasible"])
        actual_feasible, visits = _diagram_value(nodes, roots["feasible"], bits)
        diagram_steps += visits
        require(type(actual_feasible) is bool and actual_feasible is feasible, "factorized feasibility")

        world_index = number >> nc
        if feasible and world_index not in sets:
            sets[world_index] = [set() for _ in program["sites"]]
        for site_no, site in enumerate(program["sites"]):
            actual, visits = _diagram_value(nodes, roots["outcomes"][site_no], bits)
            diagram_steps += visits
            semantic_steps += 1
            if not feasible:
                expected = {"kind": "infeasible"}
            elif visit(site["guard"]) is False:
                expected = {"kind": "skipped"}
            else:
                key = [visit(site[field]) for field in ("loader", "class", "method", "signature")]
                found = any(strict_equal(key, table_entry) for table_entry in program["table"])
                expected = {"kind": "target" if found else "lookup_error", "key": key}
                if found:
                    sets[world_index][site_no].add(tuple(key))
            require(strict_equal(actual, expected), "factorized probe outcome")

    worlds = [
        {"index": world_index, "external": decode(world_index, ne),
         "targets": [[list(target) for target in sorted(site_targets)] for site_targets in sets[world_index]]}
        for world_index in sorted(sets)
    ]
    may: list[list[list[str]]] = []
    robust: list[list[list[str]] | None] = []
    for site_no in range(len(program["sites"])):
        union = {target for world_index in sets for target in sets[world_index][site_no]}
        may.append([list(target) for target in sorted(union)])
        robust.append([list(target) for target in sorted(union)
                       if all(target in sets[world_index][site_no] for world_index in sets)] if sets else None)
    summary = {"worlds": worlds, "may": may, "robust": robust}
    require(strict_equal(certificate["summary"], summary), "factorized target aggregation")
    return {
        "summary": summary,
        "assignments": 1 << width,
        "semantic_steps": semantic_steps,
        "diagram_steps": diagram_steps,
        "diagram_nodes": len(nodes),
    }
