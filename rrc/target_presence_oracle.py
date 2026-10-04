"""Exhaustive target-retention checks, distinct from the complete-label oracle.

For each width, -1 means infeasible, 0 absent, and 1 present. Expected minimal
coordinate sets are obtained directly from all subsets, not from the witness
producer. The production routines are called only after the expected family is
fixed. This is a bounded executable check, not a proof-assistant development.
"""
from __future__ import annotations
from itertools import product
from typing import Any

TARGET = ["L", "A", "f", "()"]


def expected_minima(n: int, labels: tuple[int, ...], base: int) -> set[int]:
    sufficient: set[int] = set()
    for selected in range(1 << n):
        matching_bad = False
        for world, label in enumerate(labels):
            if label != 0:
                continue
            agrees = True
            for j in range(n):
                if selected & (1 << j) and ((world ^ base) & (1 << (n - j - 1))):
                    agrees = False
                    break
            if agrees:
                matching_bad = True
                break
        if not matching_bad:
            sufficient.add(selected)
    return {s for s in sufficient if not any(t != s and (t & s) == t for t in sufficient)}


def transversal_minima(n: int, labels: tuple[int, ...], base: int) -> set[int]:
    edges = set()
    for world, label in enumerate(labels):
        if label == 0:
            edges.add(sum(1 << j for j in range(n)
                          if (world ^ base) & (1 << (n - j - 1))))
    candidates = {0}
    for edge in sorted(edges):
        expanded = set()
        for s in candidates:
            if s & edge:
                expanded.add(s)
            else:
                expanded.update(s | (1 << j) for j in range(n) if edge & (1 << j))
        candidates = {s for s in expanded if not any(t != s and (t & s) == t for t in expanded)}
    return candidates


def check_target_presence(max_width: int = 3) -> dict[str, Any]:
    if type(max_width) is not int or not 0 <= max_width <= 3:
        raise ValueError("target-presence oracle width must be an integer in [0,3]")
    from .missing_witness import produce_missing_target_witness
    from .witness_checker import check_missing_target_witness
    counts = {"tables": 0, "target_present_bases": 0, "checked_order_records": 0,
              "multiple_minimal_families": 0, "unequal_cardinality_families": 0,
              "mismatches": 0}
    by_width = []
    for n in range(max_width + 1):
        start = counts.copy()
        for labels in product((-1, 0, 1), repeat=1 << n):
            counts["tables"] += 1
            worlds = [{"index": i,
                       "external": [bool(i & (1 << (n-j-1))) for j in range(n)],
                       "targets": [[TARGET] if label == 1 else []]}
                      for i, label in enumerate(labels) if label != -1]
            summary = {"worlds": worlds, "may": [[TARGET] if 1 in labels else []],
                       "robust": [([TARGET] if worlds and all(labels[w['index']] == 1
                                   for w in worlds) else []) if worlds else None]}
            for base, label in enumerate(labels):
                if label != 1:
                    continue
                counts["target_present_bases"] += 1
                expected = expected_minima(n, labels, base)
                dual = transversal_minima(n, labels, base)
                counts["mismatches"] += int(expected != dual)
                counts["multiple_minimal_families"] += int(len(expected) > 1)
                counts["unequal_cardinality_families"] += int(len({s.bit_count() for s in expected}) > 1)
                for reverse in (False, True):
                    witness = produce_missing_target_witness(summary, 0, TARGET, [], base, reverse)
                    check_missing_target_witness(summary, witness)
                    selected = sum(1 << j for j in witness["selected"])
                    counts["checked_order_records"] += 1
                    counts["mismatches"] += int(selected not in expected)
        by_width.append({"width": n, **{key: counts[key]-start[key] for key in counts}})
    if counts["mismatches"]:
        raise AssertionError(f"target-presence oracle disagreement: {counts}")
    return {"predicate": "single-target retention", "alphabet": ["infeasible", "absent", "present"],
            "widths": list(range(max_width + 1)), **counts, "by_width": by_width}
