"""Independent closed-form row expectations for the 24 authored boundary fixtures.

This module deliberately imports neither the fixture builder nor any producer/checker.
Each case is specified directly by its intended Boolean relation and lookup identity.
The rows remain outside ``inputs/F*.json`` and are compared exactly during input
verification, unit tests, and every reproduction run.  Producer output never becomes gold.
"""
from __future__ import annotations

from itertools import product
from typing import Any, Callable, Iterable


def _target(loader: str = "L", class_name: str = "A", member: str = "f",
            signature: str = "()") -> dict[str, Any]:
    return {"kind": "target", "key": [loader, class_name, member, signature]}


def _lookup_error(loader: str = "L", class_name: str = "A", member: str = "f",
                  signature: str = "()") -> dict[str, Any]:
    return {"kind": "lookup_error", "key": [loader, class_name, member, signature]}


def _rows(width: int, rule: Callable[[tuple[bool, ...]], tuple[bool, list[dict[str, Any]]]]) \
        -> list[dict[str, Any]]:
    output = []
    for bits in product((False, True), repeat=width):
        feasible, outcomes = rule(bits)
        output.append({"feasible": feasible, "outcomes": outcomes if feasible else []})
    return output


def all_fixture_expectations() -> dict[str, list[dict[str, Any]]]:
    long_name = "a" * 24 + "b" * 24
    expected: dict[str, list[dict[str, Any]]] = {
        "F01": _rows(0, lambda _: (True, [_target()])),
        "F02": _rows(0, lambda _: (True, [_target(member="read")])),
        "F03": _rows(1, lambda b: (True, [_target(class_name="A" if b[0] else "B")])),
        "F04": _rows(1, lambda b: (True, [_target(
            class_name="A" if b[0] else "B", member="f" if b[0] else "g")])),
        "F05": _rows(1, lambda b: (True, [_target(class_name="B" if b[0] else "A")])),
        "F06": _rows(2, lambda b: (
            b[0] == b[1],
            [_target(class_name="B" if b[0] else "A")],
        )),
        "F07": _rows(3, lambda b: (
            ((not b[1]) and (not b[2])) or (b[0] and b[1] and b[2]),
            [_target(class_name="B" if b[0] else "A")],
        )),
        "F08": _rows(2, lambda b: (True, [_target(class_name="B" if b[0] == b[1] else "A")])),
        "F09": _rows(1, lambda b: (True, [_target(class_name="A" if b[0] else "B")])),
        "F10": _rows(1, lambda b: (True, [_target(loader="L" if b[0] else "M")])),
        "F11": _rows(1, lambda b: (True, [_target(signature="()" if b[0] else "(I)")])),
        "F12": _rows(1, lambda b: (True, [
            _target(class_name="A") if b[0] else _lookup_error(class_name="B")
        ])),
        "F13": _rows(1, lambda b: (True, [_target()] if b[0] else [{"kind": "skipped"}])),
        "F14": _rows(1, lambda b: (b[0], [_target(class_name="A")])),
        "F15": _rows(0, lambda _: (False, [])),
        "F16": _rows(1, lambda _: (True, [_target()])),
        "F17": _rows(0, lambda _: (True, [_target(class_name=long_name)])),
        "F18": _rows(0, lambda _: (True, [_target(class_name="abc")])),
        "F19": _rows(1, lambda b: (True, [
            _target(class_name="A" if b[0] else "B"),
            _target(class_name="B" if b[0] else "A"),
        ])),
        "F20": _rows(1, lambda b: (True, [_target(class_name="AA" if b[0] else "BB")])),
        "F21": _rows(1, lambda b: (True, [_target(member="f" if b[0] else "g")])),
        "F22": _rows(1, lambda b: (True, [_target(class_name="A")] if b[0]
                                             else [{"kind": "skipped"}])),
        "F23": _rows(2, lambda b: (True, [_target(class_name="A" if b[0] or b[1] else "B")])),
        "F24": _rows(12, lambda b: (True, [
            _target(class_name="A" if sum(b) % 2 == 1 else "B") for _ in range(8)
        ])),
    }
    if list(expected) != [f"F{index:02d}" for index in range(1, 25)]:
        raise AssertionError("fixture expectation inventory")
    return expected
