"""Benign finite construction controls; no Java, network, or native analyzer."""
from __future__ import annotations

import copy
import itertools
import unittest
from unittest.mock import patch

from rrc.factor import SharedMTBDD, _canonical, produce_factorized
from rrc.factor_checker import check_factorized
from rrc.fixtures import all_fixtures


def reference_build(dag, values, var=0):
    """Direct recursive specification without vector memoization or tokens."""
    enc = [_canonical(value) for value in values]
    if all(key == enc[0] for key in enc):
        return dag.terminal(values[0])
    half = len(values) // 2
    return dag.branch(var, reference_build(dag, values[:half], var + 1),
                      reference_build(dag, values[half:], var + 1))


class FactorTokenTests(unittest.TestCase):
    def test_every_ternary_vector_through_width_three(self):
        values = [False, True, {"kind": "skipped"}]
        for width in range(4):
            actual, reference = SharedMTBDD(width), SharedMTBDD(width)
            for vector in itertools.product(values, repeat=1 << width):
                self.assertEqual(actual.build(list(vector)), reference_build(reference, list(vector)))
            self.assertEqual(actual.nodes, reference.nodes)

    def test_canonical_equality_and_nonzero_start(self):
        vectors = [[False, 0, True, 1], ["a", "a", "b", "b"],
                   [{"a": 1, "b": False}, {"b": False, "a": 1}, [], ()],
                   ["\U0001f600", "\ud83d\ude00", "\n", "\\"]]
        actual, reference = SharedMTBDD(3), SharedMTBDD(3)
        for vector in vectors + vectors[::-1]:
            self.assertEqual(actual.build(vector, 1), reference_build(reference, vector, 1))
        self.assertEqual(_canonical(actual.nodes), _canonical(reference.nodes))

    def test_mutating_caller_does_not_change_token_representatives(self):
        value = {"key": ["A"]}
        actual = SharedMTBDD(1)
        first = actual.build([value, value])
        saved = copy.deepcopy(actual.nodes)
        value["key"][0] = "B"
        self.assertEqual(actual.nodes, saved)
        self.assertEqual(actual.build([{"key": ["A"]}] * 2), first)
        second = actual.build([value, value])
        self.assertNotEqual(second, first)
        self.assertEqual(actual.nodes[second]["value"], value)

    def test_one_canonicalization_per_input_cell(self):
        dag = SharedMTBDD(3)
        vector = [False, True] * 4
        with patch("rrc.factor._canonical", wraps=_canonical) as canonical:
            dag.build(vector)
            self.assertEqual(canonical.call_count, len(vector))
        self.assertTrue(all(type(token) is int for _, enc in dag._memo for token in enc))
        self.assertEqual(len(dag._value_tokens), 2)

    def test_all_fixture_objects_keep_reference_numbering_and_acceptance(self):
        for name, _, program in all_fixtures():
            with self.subTest(case=name):
                actual = produce_factorized(program)
                with patch.object(SharedMTBDD, "build", reference_build):
                    reference = produce_factorized(program)
                self.assertEqual(_canonical(actual), _canonical(reference))
                self.assertEqual(check_factorized(program, actual),
                                 check_factorized(program, reference))

    def test_vector_bounds(self):
        dag = SharedMTBDD(2)
        for vector, var in (([], 0), ([False], 0), ([False], -1), ([False], 3)):
            with self.assertRaises(ValueError):
                dag.build(vector, var)


if __name__ == "__main__":
    unittest.main()
