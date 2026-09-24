"""Exhaustive table-level oracle, with no producer/checker imports.

Targets are labels on worlds. This tests the set-theoretic claims independently
of the reflection DSL. Cases enumerate all constrained maps at two small sizes;
these are not public applications and not a machine-checked general proof.
"""
from __future__ import annotations
from itertools import permutations, product
from typing import Iterable


def direct_observations(n: int, labels: tuple[int, ...], base: int) -> set[int]:
    sufficient = []
    for selected in range(1 << n):
        # Bit positions are irrelevant to the theorem; mask order is fixed here.
        if all(value == -1 or value == labels[base] or ((world ^ base) & selected) != 0
               for world, value in enumerate(labels)):
            sufficient.append(selected)
    return {s for s in sufficient if not any(t != s and (s & t) == t for t in sufficient)}


def difference_edges(labels: tuple[int, ...], base: int) -> set[int]:
    return {h ^ base for h, target in enumerate(labels) if target != -1 and target != labels[base]}


def minimal_hitting_sets(n: int, edges: set[int]) -> set[int]:
    # Incremental transversal construction, unlike exhaustive direct observations.
    candidates = {0}
    for edge in sorted(edges):
        expanded = {s | (1 << j) for s in candidates for j in range(n) if edge & (1 << j)}
        candidates = {s for s in expanded if not any(t != s and (s & t) == t for t in expanded)}
    return candidates


def greedy(n: int, labels: tuple[int, ...], base: int, order: tuple[int, ...]) -> int:
    keep = (1 << n) - 1
    for j in order:
        trial = keep & ~(1 << j)
        bad = False
        for w, target in enumerate(labels):
            if target >= 0 and target != labels[base] and (w & trial) == (base & trial):
                bad = True
                break
        if not bad: keep = trial
    return keep


def models(n: int, target_labels: int) -> Iterable[tuple[int, ...]]:
    yield from product(range(-1, target_labels), repeat=1 << n)


def check_chunk(n: int, target_labels: int, start: int, stop: int) -> dict[str, int]:
    # Mixed-radix indexing makes independently resumable chunks; no random seed.
    alphabet = target_labels + 1
    total = alphabet ** (1 << n)
    stop = min(stop, total)
    counts = {"models": 0, "nonempty_models": 0, "anchors": 0,
              "greedy_orders": 0, "multiple_minima": 0, "no_least_observation": 0,
              "one_minimal_not_subset_minimal": 0, "mismatches": 0}
    orders = list(permutations(range(n)))
    for code in range(start, stop):
        k = code
        labels = []
        for _ in range(1 << n):
            labels.append(k % alphabet - 1); k //= alphabet
        labels = tuple(labels)
        counts["models"] += 1
        counts["nonempty_models"] += int(any(v >= 0 for v in labels))
        for base in range(1 << n):
            if labels[base] < 0: continue
            counts["anchors"] += 1
            observed = direct_observations(n, labels, base)
            edges = difference_edges(labels, base)
            dual = minimal_hitting_sets(n, edges)
            counts["mismatches"] += int(observed != dual)
            counts["multiple_minima"] += int(len(observed) > 1)
            # A finite upward-closed family has a least element iff one minimum.
            counts["no_least_observation"] += int(len(observed) > 1)
            for order in orders:
                counts["greedy_orders"] += 1
                counts["mismatches"] += int(greedy(n, labels, base, order) not in observed)
            for delta in edges:
                one_minimal = all((delta & ~(1 << j)) not in edges for j in range(n) if delta & (1 << j))
                subset_minimal = not any(other != delta and (other & delta) == other for other in edges)
                counts["one_minimal_not_subset_minimal"] += int(one_minimal and not subset_minimal)
    return counts
