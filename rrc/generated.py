"""Deterministic structured finite-reflection corpus.

The 600 cases are generated from compact field/guard specifications.  Expected row
outcomes are computed from those specifications, not by either certificate producer
or checker.  They are synthetic conformance cases, not application benchmarks.
"""
from __future__ import annotations

import itertools
import random
from dataclasses import dataclass
from typing import Any, Callable

from .fixtures import Builder

SEED = 291731
COUNT = 600


@dataclass(frozen=True)
class FieldSpec:
    kind: str
    bits: tuple[int, ...]
    values: tuple[str, ...]

    def value(self, assignment: tuple[bool, ...]) -> str:
        if self.kind == "constant":
            return self.values[0]
        if self.kind == "choice":
            index = 0
            for bit in self.bits:
                index = (index << 1) | int(assignment[bit])
            return self.values[index]
        if self.kind == "concat":
            suffix = 0
            for bit in self.bits:
                suffix = (suffix << 1) | int(assignment[bit])
            return self.values[0] + self.values[1 + suffix]
        raise AssertionError(self.kind)


@dataclass(frozen=True)
class GuardSpec:
    mode: str
    bits: tuple[int, ...] = ()

    def value(self, assignment: tuple[bool, ...]) -> bool:
        if self.mode == "true":
            return True
        if self.mode == "bit":
            return assignment[self.bits[0]]
        if self.mode == "not":
            return not assignment[self.bits[0]]
        if self.mode == "all":
            return all(assignment[bit] for bit in self.bits)
        if self.mode == "pair_or":
            assert len(self.bits) == 4
            a, b, c, d = self.bits
            return (assignment[a] and assignment[b]) or (assignment[c] and assignment[d])
        raise AssertionError(self.mode)


def _bit_rows(width: int):
    return itertools.product((False, True), repeat=width)


def _field_node(builder: Builder, spec: FieldSpec, literals: dict[str, int]) -> int:
    def literal(value: str) -> int:
        if value not in literals:
            literals[value] = builder.lit(value)
        return literals[value]

    if spec.kind == "constant":
        return literal(spec.values[0])
    if spec.kind == "concat":
        suffix_spec = FieldSpec("choice", spec.bits, spec.values[1:])
        return builder.node("cat", literal(spec.values[0]), _field_node(builder, suffix_spec, literals))
    refs = [literal(value) for value in spec.values]
    current = refs
    # Build a compact complete decision tree over at most two selected bits.
    for bit in reversed(spec.bits):
        next_level = []
        for pos in range(0, len(current), 2):
            next_level.append(builder.node("ite", builder.inputs[bit], current[pos + 1], current[pos]))
        current = next_level
    assert len(current) == 1
    return current[0]


def _guard_node(builder: Builder, spec: GuardSpec) -> int:
    if spec.mode == "true":
        return builder.true
    if spec.mode == "bit":
        return builder.inputs[spec.bits[0]]
    if spec.mode == "not":
        return builder.node("not", builder.inputs[spec.bits[0]])
    if spec.mode == "all":
        node = builder.inputs[spec.bits[0]]
        for bit in spec.bits[1:]:
            node = builder.node("and", node, builder.inputs[bit])
        return node
    if spec.mode == "pair_or":
        a, b, c, d = spec.bits
        left = builder.node("and", builder.inputs[a], builder.inputs[b])
        right = builder.node("and", builder.inputs[c], builder.inputs[d])
        return builder.node("or", left, right)
    raise AssertionError(spec.mode)


def _feasibility(builder: Builder, mode: int, external: int) -> tuple[int, Callable[[tuple[bool, ...]], bool]]:
    h = builder.inputs[:external]
    if mode == 0 or external == 0:
        return builder.true, lambda bits: True
    if mode == 1:
        return h[0], lambda bits: bits[0]
    if mode == 2 and external >= 2:
        node = builder.node("eq", h[0], h[1])
        return node, lambda bits: bits[0] is bits[1]
    if mode == 3 and external >= 2:
        node = builder.node("or", h[0], h[1])
        return node, lambda bits: bits[0] or bits[1]
    if mode == 4 and external >= 2:
        node = builder.node("not", builder.node("and", h[0], h[1]))
        return node, lambda bits: not (bits[0] and bits[1])
    # Parity-like feasibility over up to three external bits, expressed through typed equality.
    chosen = min(external, 3)
    node = h[0]
    for index in range(1, chosen):
        node = builder.node("not", builder.node("eq", node, h[index]))
    return node, lambda bits, chosen=chosen: sum(bool(bits[index]) for index in range(chosen)) % 2 == 1


def _choose_bits(rng: random.Random, width: int, count: int) -> tuple[int, ...]:
    if width == 0:
        return ()
    count = min(count, width)
    return tuple(sorted(rng.sample(range(width), count)))


def _field_spec(rng: random.Random, width: int, family: str, case: int, site: int) -> FieldSpec:
    mode = rng.randrange(3) if width else 0
    if family == "loader":
        base = ("L0", "L1", "L2", "L3")
    elif family == "class":
        base = tuple(f"C{case % 17}_{site}_{i}" for i in range(4))
    elif family == "method":
        base = ("read", "write", "open", "close")
    else:
        base = ("()", "(I)", "(S)", "(II)")
    if mode == 0:
        return FieldSpec("constant", (), (base[rng.randrange(len(base))],))
    bit_count = min(2, width) if (mode == 2 and family == "class") else 1
    bits = _choose_bits(rng, width, bit_count)
    values = base[: 1 << len(bits)]
    if family == "class" and rng.random() < 0.35:
        suffixes = tuple(str(index) for index in range(1 << len(bits)))
        return FieldSpec("concat", bits, (f"C{case % 17}_{site}_",) + suffixes)
    return FieldSpec("choice", bits, values)


def _program(case: int, rng: random.Random) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    # Sixty conjunction cases make one target identity depend independently on
    # four external coordinates.  Another sixty disjunctive-guard cases have
    # two incomparable two-coordinate explanations at an all-true world.  The
    # remaining 480 cases use the mixed random family below.  This prevents the
    # witness evaluation from degenerating to singleton explanations only.
    profile = case % 10
    external = 4 if profile in (0, 1) else 1 + (case % 6)
    choices = (case // 6) % 3
    width = external + choices
    builder = Builder(external, choices)
    # Keep the full Boolean cube for the two witness-stress profiles so no
    # feasibility invariant silently supplies one of the explanation bits.
    feasible_node, feasible_fn = _feasibility(builder, 0 if profile in (0, 1) else case % 6, external)
    builder.p["feasible"] = feasible_node
    literals: dict[str, int] = {}
    site_specs = []
    site_count = 1 + (case % 2)
    all_identities: set[tuple[str, str, str, str]] = set()
    for site in range(site_count):
        if profile == 0 and site == 0:
            fields = {
                "loader": FieldSpec("choice", (0,), ("L0", "L1")),
                "class": FieldSpec("choice", (1,), (f"C{case}_0", f"C{case}_1")),
                "method": FieldSpec("choice", (2,), ("read", "write")),
                "signature": FieldSpec("choice", (3,), ("()", "(I)")),
            }
            guard = GuardSpec("true")
        elif profile == 1 and site == 0:
            fields = {
                "loader": FieldSpec("constant", (), ("L0",)),
                "class": FieldSpec("constant", (), (f"Guarded{case}",)),
                "method": FieldSpec("constant", (), ("open",)),
                "signature": FieldSpec("constant", (), ("()",)),
            }
            guard = GuardSpec("pair_or", (0, 1, 2, 3))
        else:
            fields = {
                name: _field_spec(rng, width, name, case, site)
                for name in ("loader", "class", "method", "signature")
            }
            guard_mode = (case + site) % 3
            if guard_mode == 0:
                guard = GuardSpec("true")
            else:
                bit = (case * 7 + site * 3) % width
                guard = GuardSpec("bit" if guard_mode == 1 else "not", (bit,))
        refs = {name: _field_node(builder, spec, literals) for name, spec in fields.items()}
        builder.probe(class_ref=refs["class"], method=refs["method"], loader=refs["loader"],
                      signature=refs["signature"], guard=_guard_node(builder, guard))
        site_specs.append((guard, fields))
        for assignment in _bit_rows(width):
            all_identities.add(tuple(fields[name].value(assignment)
                                     for name in ("loader", "class", "method", "signature")))
    identities = sorted(all_identities)
    # The structured witness cases retain all identities so their target
    # conditions are controlled only by field dependencies or the guard.
    # Other generated cases deterministically drop some identities to exercise
    # lookup-error handling.  Every case also gets one unreachable distractor.
    if profile in (0, 1):
        kept = identities
    else:
        kept = [identity for position, identity in enumerate(identities)
                if (position + case) % 5 != 0]
        if not kept:
            kept = identities[:1]
    kept.append(("LX", f"Unused{case}", "never", "()"))
    builder.table([list(identity) for identity in kept])
    program = builder.finish()

    expected_rows = []
    table = set(kept)
    for assignment in _bit_rows(width):
        feasible = feasible_fn(assignment[:external])
        outcomes = []
        if feasible:
            for guard, fields in site_specs:
                if not guard.value(assignment):
                    outcomes.append({"kind": "skipped"})
                    continue
                key = [fields[name].value(assignment)
                       for name in ("loader", "class", "method", "signature")]
                outcomes.append({"kind": "target" if tuple(key) in table else "lookup_error", "key": key})
        expected_rows.append({"feasible": feasible, "outcomes": outcomes})
    return program, expected_rows


def all_generated() -> list[tuple[str, dict[str, Any], list[dict[str, Any]]]]:
    rng = random.Random(SEED)
    output = []
    for case in range(COUNT):
        program, expected = _program(case, rng)
        output.append((f"G{case + 1:03d}", program, expected))
    return output
