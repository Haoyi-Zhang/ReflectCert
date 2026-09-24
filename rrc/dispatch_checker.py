"""Independent checker and exhaustive trace replay for direct-dispatch programs.

This module does not import the dispatch transformer or factorized-certificate code.  It
validates the submitted dispatch DAG and independently evaluates the bounded source on
every assignment.  Acceptance proves equality of the complete finite outcome trace.
"""
from __future__ import annotations

import json
from typing import Any

from .schema import Invalid, exact_keys, require, strict_equal, validate

FORMAT = "certificate-guided-direct-dispatch"
MAX_DISPATCH_NODES = 131072


def decode(index: int, width: int) -> list[bool]:
    return [bool(index & (1 << (width - position - 1))) for position in range(width)]


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _validate_action(action: Any, program: dict[str, Any]) -> None:
    require(type(action) is dict and type(action.get("kind")) is str, "dispatch action")
    kind = action["kind"]
    if kind in ("infeasible", "skipped"):
        exact_keys(action, {"kind"}, "dispatch terminal action")
        return
    if kind == "lookup_error":
        exact_keys(action, {"kind", "key"}, "dispatch lookup-error action")
        key = action["key"]
        require(type(key) is list and len(key) == 4 and all(type(field) is str for field in key),
                "dispatch lookup-error key")
        return
    require(kind == "invoke", "dispatch action kind")
    exact_keys(action, {"kind", "target"}, "dispatch invoke action")
    target = action["target"]
    require(type(target) is int and 0 <= target < len(program["table"]), "dispatch target index")


def _validate_diagram(nodes: Any, width: int, program: dict[str, Any]) -> None:
    require(type(nodes) is list and 1 <= len(nodes) <= MAX_DISPATCH_NODES, "dispatch node bound")
    branch_vars: list[int | None] = []
    terminals: set[str] = set()
    branches: set[tuple[int, int, int]] = set()
    for node_id, node in enumerate(nodes):
        require(type(node) is dict and type(node.get("kind")) is str, "dispatch node")
        if node["kind"] == "terminal":
            exact_keys(node, {"kind", "action"}, "dispatch terminal")
            _validate_action(node["action"], program)
            encoded = _canonical(node["action"])
            require(encoded not in terminals, "duplicate dispatch terminal")
            terminals.add(encoded)
            branch_vars.append(None)
            continue
        require(node["kind"] == "branch", "dispatch node kind")
        exact_keys(node, {"kind", "var", "low", "high"}, "dispatch branch")
        var, low, high = node["var"], node["low"], node["high"]
        require(type(var) is int and 0 <= var < width, "dispatch branch variable")
        require(type(low) is int and type(high) is int and 0 <= low < node_id and 0 <= high < node_id,
                "dispatch branch child order")
        require(low != high, "unreduced dispatch branch")
        branch = (var, low, high)
        require(branch not in branches, "duplicate dispatch branch")
        branches.add(branch)
        for child in (low, high):
            child_var = branch_vars[child]
            require(child_var is None or child_var > var, "ordered dispatch path")
        branch_vars.append(var)


def _validate_reachability(nodes: list[dict[str, Any]], roots: list[int]) -> None:
    reachable: set[int] = set()
    pending = list(roots)
    while pending:
        node_id = pending.pop()
        require(type(node_id) is int and 0 <= node_id < len(nodes), "dispatch root")
        if node_id in reachable:
            continue
        reachable.add(node_id)
        node = nodes[node_id]
        if node["kind"] == "branch":
            pending.extend((node["low"], node["high"]))
    require(len(reachable) == len(nodes), "unreachable dispatch node")


def _diagram_action(nodes: list[dict[str, Any]], root: int, bits: list[bool]) -> tuple[dict[str, Any], int]:
    require(type(root) is int and 0 <= root < len(nodes), "dispatch root")
    node_id = root
    visits = 0
    while True:
        visits += 1
        node = nodes[node_id]
        if node["kind"] == "terminal":
            return node["action"], visits
        node_id = node["high"] if bits[node["var"]] else node["low"]


def _expected_action(program: dict[str, Any], values: list[Any], feasible: bool,
                     site: dict[str, Any]) -> dict[str, Any]:
    if not feasible:
        return {"kind": "infeasible"}
    if values[site["guard"]] is False:
        return {"kind": "skipped"}
    key = [values[site[field]] for field in ("loader", "class", "method", "signature")]
    for target, candidate in enumerate(program["table"]):
        if strict_equal(key, candidate):
            return {"kind": "invoke", "target": target}
    return {"kind": "lookup_error", "key": key}


def check_direct_dispatch(program: dict[str, Any], dispatch: Any) -> dict[str, Any]:
    validate(program)
    exact_keys(dispatch, {"format", "program", "bit_order", "diagram", "roots"},
               "direct dispatch")
    require(dispatch["format"] == FORMAT, "direct-dispatch format")
    require(strict_equal(dispatch["program"], program), "direct-dispatch source binding")
    bit_order = dispatch["bit_order"]
    require(strict_equal(bit_order, program["external"] + program["choices"]),
            "direct-dispatch bit order")
    width = len(bit_order)
    exact_keys(dispatch["diagram"], {"nodes"}, "direct-dispatch diagram")
    nodes = dispatch["diagram"]["nodes"]
    _validate_diagram(nodes, width, program)
    roots = dispatch["roots"]
    require(type(roots) is list and len(roots) == len(program["sites"]) and
            all(type(root) is int for root in roots), "direct-dispatch roots")
    _validate_reachability(nodes, roots)

    semantic_steps = 0
    diagram_steps = 0
    invocations = 0
    lookup_errors = 0
    skipped = 0
    infeasible = 0
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
                value = all(visit(argument) is True for argument in node["args"])
            elif op == "or":
                value = any(visit(argument) is True for argument in node["args"])
            elif op == "eq":
                value = strict_equal(visit(node["args"][0]), visit(node["args"][1]))
            elif op == "cat":
                value = "".join(visit(argument) for argument in node["args"])
            elif op == "ite":
                condition, yes, no = node["args"]
                value = visit(yes) if visit(condition) is True else visit(no)
            else:
                raise Invalid("unknown operation")
            cache[node_id] = value
            return value

        values = [visit(node_id) for node_id in range(len(program["nodes"]))]
        feasible_value = visit(program["feasible"])
        for site_no, site in enumerate(program["sites"]):
            expected = _expected_action(program, values, feasible_value, site)
            actual, visits = _diagram_action(nodes, roots[site_no], bits)
            diagram_steps += visits
            require(strict_equal(actual, expected), "direct-dispatch trace mismatch")
            if actual["kind"] == "invoke":
                invocations += 1
            elif actual["kind"] == "lookup_error":
                lookup_errors += 1
            elif actual["kind"] == "skipped":
                skipped += 1
            else:
                infeasible += 1

    return {
        "assignments": 1 << width,
        "trace_events": (1 << width) * len(program["sites"]),
        "semantic_steps": semantic_steps,
        "diagram_steps": diagram_steps,
        "diagram_nodes": len(nodes),
        "invocations": invocations,
        "lookup_errors": lookup_errors,
        "skipped": skipped,
        "infeasible": infeasible,
    }
