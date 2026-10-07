"""Owned finite equality/pipeline fixtures; no Java, corpus or private paths."""
from __future__ import annotations

import copy
import itertools
import json
import unittest
from unittest.mock import patch

from rrc.schema import Invalid, strict_equal, validate
from rrc.producer import produce
from rrc.checker import check
from rrc.factor import produce_factorized
from rrc.factor_checker import check_factorized
from rrc.dispatch import produce_direct_dispatch
from rrc.dispatch_checker import check_direct_dispatch
from rrc.missing_witness import produce_missing_target_witness
from rrc.witness_checker import check_missing_target_witness


class StringSubclass(str):
    def __eq__(self, other):
        raise AssertionError("subclass equality must not define JSON equality")


class IntegerSubclass(int):
    def __eq__(self, other):
        raise AssertionError("subclass equality must not define JSON equality")


def canonical_outcome(a, b):
    """Specification oracle via the standard JSON encoder, not a DSL evaluator."""
    try:
        encodings = [json.dumps(value, sort_keys=True, separators=(",", ":"),
                                allow_nan=False) for value in (a, b)]
        return ("value", encodings[0] == encodings[1])
    except (TypeError, ValueError) as exc:
        return ("error", type(exc).__name__, str(exc))


def observed_outcome(fn, a, b):
    try:
        return ("value", fn(a, b))
    except (TypeError, ValueError) as exc:
        return ("error", type(exc).__name__, str(exc))


def equality_values():
    cycle = []
    cycle.append(cycle)
    return [None, False, True, 0, 1, -1, 0.0, -0.0, 1.0, 1.5,
            "", "a", "b", "false", "0", 'quote"', "\\", "\n", "\x00",
            "\u00e9", "\U0001f600", "\ud83d\ude00", "\ud800", "\udc00",
            [], [False], [0], (), (False,), {}, {"a": False, "b": ["x"]},
            {"b": ["x"], "a": False}, {"a": 0, "b": ["x"]},
            {1: "x"}, {"1": "x"}, {1: "x", "a": "y"},
            StringSubclass("a"), IntegerSubclass(1),
            float("nan"), float("inf"), -float("inf"), [float("nan")],
            {"x": float("inf")}, b"a", {1}, 1j, object(), cycle]


def owned_program():
    # Feasible iff not h0; enabled iff h1. r0 selects A (target) or B (error).
    # Both Boolean and string equalities occur in certified expression roots.
    nodes = [{"op": "input", "index": i} for i in range(3)] + [
        {"op": "lit", "value": True},       # 3
        {"op": "lit", "value": "L"},        # 4
        {"op": "lit", "value": "A"},        # 5
        {"op": "lit", "value": "B"},        # 6
        {"op": "lit", "value": "f"},        # 7
        {"op": "lit", "value": "()"},       # 8
        {"op": "lit", "value": ""},         # 9
        {"op": "not", "args": [0]},          # 10 feasibility
        {"op": "eq", "args": [1, 3]},        # 11 Boolean equality
        {"op": "cat", "args": [9, 5]},       # 12
        {"op": "eq", "args": [12, 5]},       # 13 string equality
        {"op": "and", "args": [11, 13]},     # 14 guard
        {"op": "ite", "args": [2, 5, 6]},    # 15 class
    ]
    return {"external": ["h0", "h1"], "choices": ["r0"], "nodes": nodes,
            "feasible": 10, "table": [["L", "A", "f", "()"]],
            "sites": [{"guard": 14, "loader": 4, "class": 15,
                       "method": 7, "signature": 8}]}


def owned_expected_rows():
    rows = []
    for h0, h1, r0 in itertools.product((False, True), repeat=3):
        feasible = not h0
        if not feasible:
            outcomes = []
        elif not h1:
            outcomes = [{"kind": "skipped"}]
        else:
            outcomes = [{"kind": "target" if r0 else "lookup_error",
                         "key": ["L", "A" if r0 else "B", "f", "()"]}]
        rows.append({"feasible": feasible, "outcomes": outcomes})
    return rows


class StrictEqualTests(unittest.TestCase):
    def test_cartesian_canonical_json_oracle(self):
        values = equality_values()
        for i, a in enumerate(values):
            for j, b in enumerate(values):
                with self.subTest(left=i, right=j):
                    self.assertEqual(observed_outcome(strict_equal, a, b),
                                     canonical_outcome(a, b))

    def test_exact_ascii_and_bool_path_avoids_serialization(self):
        strings = ["", "a", "b", "\x00", "\n", '"\\', "A" * 48]
        cases = list(itertools.product(strings, repeat=2)) + list(
            itertools.product((False, True), repeat=2))
        expected = [canonical_outcome(a, b) for a, b in cases]
        with patch("rrc.schema.json.dumps", side_effect=AssertionError("serialized")):
            for (a, b), outcome in zip(cases, expected):
                self.assertEqual(("value", strict_equal(a, b)), outcome)

    def test_subclasses_and_errors_keep_fallback(self):
        pairs = [(StringSubclass("a"), StringSubclass("a")),
                 (StringSubclass("a"), "a"), ("a", StringSubclass("a")),
                 (IntegerSubclass(1), IntegerSubclass(1)), (False, 0), (True, 1),
                 (0, False), (1, True), (0, 0.0), ([], ()),
                 (float("nan"), False), (False, float("nan")),
                 (float("inf"), float("inf")), ({1: "x", "a": "y"}, {}),
                 ({1}, {1}), ("a", b"a"), ([True], [1])]
        dumps = json.dumps
        for a, b in pairs:
            expected = canonical_outcome(a, b)
            with patch("rrc.schema.json.dumps", wraps=dumps) as encoder:
                self.assertEqual(observed_outcome(strict_equal, a, b), expected)
                self.assertGreaterEqual(encoder.call_count, 1)

    def test_unicode_canonical_collisions_keep_fallback(self):
        astral, surrogate_pair = "\U0001f600", "\ud83d\ude00"
        self.assertNotEqual(astral, surrogate_pair)
        self.assertTrue(strict_equal(astral, surrogate_pair))
        for a, b in itertools.product(("\u00e9", "e", astral, surrogate_pair,
                                       "\ud800", "\udc00"), repeat=2):
            self.assertEqual(observed_outcome(strict_equal, a, b), canonical_outcome(a, b))

    def test_owned_source_pipeline_matches_independent_rows(self):
        p = owned_program()
        saved = copy.deepcopy(p)
        flat = produce(p)
        self.assertEqual([{"feasible": r["feasible"], "outcomes": r["outcomes"]}
                          for r in flat["rows"]], owned_expected_rows())
        factor = produce_factorized(p)
        accepted = check_factorized(p, factor)
        self.assertEqual(check(p, flat)["summary"], accepted["summary"])
        direct = produce_direct_dispatch(p, factor)
        replay = check_direct_dispatch(p, direct)
        self.assertEqual([replay[k] for k in ("assignments", "invocations", "lookup_errors",
                                             "skipped", "infeasible")], [8, 1, 1, 2, 4])
        target = ["L", "A", "f", "()"]
        for reverse in (False, True):
            witness = produce_missing_target_witness(accepted["summary"], 0, target, [], 1,
                                                     reverse=reverse)
            self.assertEqual(witness["selected"], [1])
            self.assertEqual(witness["necessity"], [{"removed": 1, "world": 0}])
            self.assertTrue(check_missing_target_witness(accepted["summary"], witness))
        self.assertEqual(p, saved)

    def test_owned_mutations_preserve_rejection_boundaries(self):
        p = owned_program()
        flat = produce(p)
        factor = produce_factorized(p)
        accepted = check_factorized(p, factor)
        direct = produce_direct_dispatch(p, factor)
        bad = copy.deepcopy(flat)
        bad["rows"][0]["values"][0] = 0
        with self.assertRaises(Invalid):
            check(p, bad)
        bad = copy.deepcopy(factor)
        next(n for n in bad["diagram"]["nodes"]
             if n["kind"] == "terminal" and n["value"] is False)["value"] = 0
        with self.assertRaises(Invalid):
            check_factorized(p, bad)
        bad = copy.deepcopy(factor)
        bad["program"]["nodes"][3]["value"] = 1
        with self.assertRaisesRegex(Invalid, "binding"):
            check_factorized(p, bad)
        bad = copy.deepcopy(factor)
        bad["summary"]["worlds"][0]["external"][0] = 0
        with self.assertRaisesRegex(Invalid, "aggregation"):
            check_factorized(p, bad)
        bad = copy.deepcopy(direct)
        next(n for n in bad["diagram"]["nodes"]
             if n["kind"] == "terminal" and n["action"]["kind"] == "invoke")["action"]["target"] = False
        with self.assertRaises(Invalid):
            check_direct_dispatch(p, bad)
        witness = produce_missing_target_witness(accepted["summary"], 0,
                                                 ["L", "A", "f", "()"], [], 1)
        witness["selected"] = [True]
        with self.assertRaises(Invalid):
            check_missing_target_witness(accepted["summary"], witness)
        bad = copy.deepcopy(p)
        bad["nodes"][3]["value"] = IntegerSubclass(1)
        with self.assertRaises(Invalid):
            validate(bad)


if __name__ == "__main__":
    unittest.main()
