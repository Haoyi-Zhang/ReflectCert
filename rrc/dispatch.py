"""Untrusted certificate-guided lowering to a finite direct-dispatch program.

The transformed program contains no reflective string construction or table lookup.
Each site is an ordered Boolean decision DAG whose leaves are one of:
``infeasible``, ``skipped``, ``lookup_error(key)``, or ``invoke(target_index)``.
The transformer consumes an accepted factorized certificate, but its output is checked
again by :mod:`rrc.dispatch_checker` against the source semantics.
"""
from __future__ import annotations

import copy
import itertools
import json
from typing import Any, Callable, Iterable

from .factor_checker import check_factorized
from .schema import Invalid, strict_equal, validate

FORMAT = "certificate-guided-direct-dispatch"


def bit_rows(width: int) -> Iterable[tuple[bool, ...]]:
    return itertools.product((False, True), repeat=width)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


class _SharedDispatchDAG:
    """Independent hash-consed ordered DAG builder for dispatch actions."""

    def __init__(self, width: int):
        self.width = width
        self.nodes: list[dict[str, Any]] = []
        self._terminal_ids: dict[str, int] = {}
        self._branch_ids: dict[tuple[int, int, int], int] = {}
        self._memo: dict[tuple[int, tuple[str, ...]], int] = {}

    def terminal(self, action: dict[str, Any]) -> int:
        key = _canonical(action)
        existing = self._terminal_ids.get(key)
        if existing is not None:
            return existing
        node_id = len(self.nodes)
        self.nodes.append({"kind": "terminal", "action": copy.deepcopy(action)})
        self._terminal_ids[key] = node_id
        return node_id

    def branch(self, var: int, low: int, high: int) -> int:
        if low == high:
            return low
        key = (var, low, high)
        existing = self._branch_ids.get(key)
        if existing is not None:
            return existing
        node_id = len(self.nodes)
        self.nodes.append({"kind": "branch", "var": var, "low": low, "high": high})
        self._branch_ids[key] = node_id
        return node_id

    def build(self, actions: list[dict[str, Any]], var: int = 0) -> int:
        expected = 1 << (self.width - var)
        if len(actions) != expected:
            raise ValueError("dispatch vector width")
        encoded = tuple(_canonical(action) for action in actions)
        memo_key = (var, encoded)
        existing = self._memo.get(memo_key)
        if existing is not None:
            return existing
        if all(item == encoded[0] for item in encoded[1:]):
            root = self.terminal(actions[0])
        else:
            if var >= self.width:
                raise AssertionError("different actions without a decision variable")
            half = len(actions) // 2
            low = self.build(actions[:half], var + 1)
            high = self.build(actions[half:], var + 1)
            root = self.branch(var, low, high)
        self._memo[memo_key] = root
        return root


def _certificate_value(nodes: list[dict[str, Any]], root: int, bits: tuple[bool, ...]) -> Any:
    node_id = root
    while True:
        node = nodes[node_id]
        if node["kind"] == "terminal":
            return node["value"]
        node_id = node["high"] if bits[node["var"]] else node["low"]


def _action_for(outcome: Any, table: list[list[str]]) -> dict[str, Any]:
    if type(outcome) is not dict or type(outcome.get("kind")) is not str:
        raise Invalid("certificate outcome")
    kind = outcome["kind"]
    if kind in ("infeasible", "skipped"):
        if set(outcome) != {"kind"}:
            raise Invalid("certificate outcome fields")
        return {"kind": kind}
    if kind == "lookup_error":
        if set(outcome) != {"kind", "key"}:
            raise Invalid("certificate lookup-error fields")
        return {"kind": "lookup_error", "key": copy.deepcopy(outcome["key"])}
    if kind == "target":
        if set(outcome) != {"kind", "key"}:
            raise Invalid("certificate target fields")
        for index, target in enumerate(table):
            if strict_equal(target, outcome["key"]):
                return {"kind": "invoke", "target": index}
        raise Invalid("certificate target outside source table")
    raise Invalid("certificate outcome kind")


def produce_direct_dispatch(
    program: dict[str, Any],
    certificate: dict[str, Any],
    *,
    certificate_checked: bool = False,
) -> dict[str, Any]:
    """Lower an accepted certificate into an independently checkable direct dispatcher.

    By default acceptance is deliberately re-established here before any outcome is
    trusted.  Batch callers that have just obtained a successful checker result may pass
    ``certificate_checked=True`` to avoid repeating the same exhaustive check; the
    returned object is still treated as untrusted by the independent replay checker.
    """
    validate(program)
    if not certificate_checked:
        check_factorized(program, certificate)
    width = len(program["external"]) + len(program["choices"])
    cert_nodes = certificate["diagram"]["nodes"]
    cert_roots = certificate["roots"]["outcomes"]
    vectors: list[list[dict[str, Any]]] = [[] for _ in program["sites"]]
    for bits in bit_rows(width):
        for site, root in enumerate(cert_roots):
            outcome = _certificate_value(cert_nodes, root, bits)
            vectors[site].append(_action_for(outcome, program["table"]))
    dag = _SharedDispatchDAG(width)
    roots = [dag.build(vector) for vector in vectors]
    return {
        "format": FORMAT,
        "program": copy.deepcopy(program),
        "bit_order": list(program["external"] + program["choices"]),
        "diagram": {"nodes": dag.nodes},
        "roots": roots,
    }


def _action_at(dispatch: dict[str, Any], bits: list[bool] | tuple[bool, ...], site: int) -> dict[str, Any]:
    node_id = dispatch["roots"][site]
    nodes = dispatch["diagram"]["nodes"]
    while True:
        node = nodes[node_id]
        if node["kind"] == "terminal":
            return node["action"]
        node_id = node["high"] if bits[node["var"]] else node["low"]


def execute_direct_dispatch(
    dispatch: dict[str, Any],
    bits: list[bool] | tuple[bool, ...],
    callees: list[Callable[[], Any]] | None = None,
) -> list[dict[str, Any]]:
    """Execute the direct-dispatch IR and optionally invoke concrete target thunks.

    This helper is an execution engine, not the validator.  Callers should first use
    ``check_direct_dispatch``.  A target thunk is invoked at most once for each site whose
    leaf is ``invoke``; all non-invocation outcomes are returned as trace events.
    """
    if len(bits) != len(dispatch["bit_order"]) or not all(type(bit) is bool for bit in bits):
        raise Invalid("dispatch execution bits")
    if callees is not None and len(callees) != len(dispatch["program"]["table"]):
        raise Invalid("dispatch callee table")
    trace: list[dict[str, Any]] = []
    for site in range(len(dispatch["roots"])):
        action = _action_at(dispatch, bits, site)
        if action["kind"] == "invoke":
            target = action["target"]
            event: dict[str, Any] = {
                "kind": "invoke",
                "target": target,
                "key": copy.deepcopy(dispatch["program"]["table"][target]),
            }
            if callees is not None:
                event["result"] = callees[target]()
            trace.append(event)
        else:
            trace.append(copy.deepcopy(action))
    return trace
