"""Small explicit counterexamples for target-retention witness claims."""
from __future__ import annotations

from itertools import combinations
from typing import Any

from .missing_witness import (
    check_missing_target_witness,
    produce_missing_target_witness,
    retains_target,
)

TARGET = ["L", "A", "f", "()"]


def unequal_cardinality_summary() -> dict[str, Any]:
    """Return a 3-bit summary whose minimal retaining sets are {0} and {1,2}.

    The base is 000.  The target is absent only at 101 and 110, so a retaining
    set must hit both changed-coordinate sets {0,2} and {0,1}.
    """
    worlds = []
    for index in range(8):
        bits = [bool(index & 4), bool(index & 2), bool(index & 1)]
        targets = [] if index in (5, 6) else [TARGET]
        worlds.append({"index": index, "external": bits, "targets": [targets]})
    return {"worlds": worlds, "may": [[TARGET]], "robust": [[]]}


def minimum_cardinality_counterexample() -> dict[str, Any]:
    summary = unequal_cardinality_summary()
    base = summary["worlds"][0]
    minimal: list[list[int]] = []
    for size in range(4):
        for subset in combinations(range(3), size):
            selected = set(subset)
            if not retains_target(summary["worlds"], 0, TARGET, base, selected):
                continue
            if any(retains_target(summary["worlds"], 0, TARGET, base, selected - {index})
                   for index in selected):
                continue
            minimal.append(list(subset))
    forward = produce_missing_target_witness(summary, 0, TARGET, [], 0, reverse=False)
    reverse = produce_missing_target_witness(summary, 0, TARGET, [], 0, reverse=True)
    check_missing_target_witness(summary, forward)
    check_missing_target_witness(summary, reverse)
    if minimal != [[0], [1, 2]]:
        raise AssertionError("unexpected unequal-cardinality minimal family")
    if forward["selected"] != [1, 2] or reverse["selected"] != [0]:
        raise AssertionError("greedy order no longer exposes cardinality gap")
    return {
        "format": "rrc-witness-cardinality-counterexample-v1",
        "base": 0,
        "target": TARGET,
        "target_absent_worlds": [5, 6],
        "retention_minimal_sets": minimal,
        "minimum_cardinality": 1,
        "forward_order": [0, 1, 2],
        "forward_selected": forward["selected"],
        "reverse_order": [2, 1, 0],
        "reverse_selected": reverse["selected"],
        "forward_witness": forward,
        "reverse_witness": reverse,
    }
