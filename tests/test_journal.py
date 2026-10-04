from __future__ import annotations
import ast
import copy
from pathlib import Path
import unittest
from unittest.mock import patch
from rrc.schema import Invalid
from rrc.missing_witness import produce_missing_target_witness
from rrc.witness_checker import check_missing_target_witness
from rrc.witness_counterexamples import unequal_cardinality_summary, TARGET
from rrc.target_presence_oracle import check_target_presence
from rrc.journal_bridge import journal_bridge_record
from journal_analysis import deterministic_gzip


class JournalValidationTests(unittest.TestCase):
    def setUp(self):
        self.summary = unequal_cardinality_summary()
        self.witness = produce_missing_target_witness(self.summary, 0, TARGET, [], 0)

    def test_witness_checker_does_not_call_producer_retention(self):
        with patch('rrc.missing_witness.retains_target', side_effect=AssertionError('producer invoked')):
            self.assertTrue(check_missing_target_witness(self.summary, self.witness))

    def test_witness_checker_imports_only_schema(self):
        path = Path(__file__).resolve().parents[1] / 'rrc/witness_checker.py'
        modules = {n.module for n in ast.walk(ast.parse(path.read_text()))
                   if isinstance(n, ast.ImportFrom) and n.level}
        self.assertEqual(modules, {'schema'})

    def test_boolean_necessity_index_is_not_integer(self):
        bad = copy.deepcopy(self.witness)
        bad['necessity'][0]['removed'] = True  # numerically equal to index 1 in Python
        with self.assertRaises(Invalid):
            check_missing_target_witness(self.summary, bad)

    def test_nonhashable_coordinate_is_cleanly_rejected(self):
        bad = copy.deepcopy(self.witness); bad['selected'] = [[1]]
        with self.assertRaises(Invalid):
            check_missing_target_witness(self.summary, bad)

    def test_false_sufficiency_is_rejected(self):
        bad = copy.deepcopy(self.witness); bad['selected'] = []; bad['necessity'] = []
        with self.assertRaisesRegex(Invalid, 'retain'):
            check_missing_target_witness(self.summary, bad)

    def test_membership_oracle_exhaustive_up_to_two_bits(self):
        result = check_target_presence(2)
        self.assertEqual(result['tables'], 93)
        self.assertEqual(result['target_present_bases'], 115)
        self.assertEqual(result['checked_order_records'], 230)
        self.assertEqual(result['mismatches'], 0)


    def test_transport_gzip_is_deterministic(self):
        payload = b'{"a":[1,2,3],"b":"repeated repeated repeated"}'
        first = deterministic_gzip(payload)
        second = deterministic_gzip(payload)
        self.assertEqual(first, second)
        self.assertEqual(first[4:8], b"\x00\x00\x00\x00")

    def test_extra_source_bridge_controls_run_and_reject(self):
        result = journal_bridge_record()
        self.assertEqual(result['jvm_executions'], 2)
        self.assertEqual(result['observed_output_rows'], 7)
        self.assertEqual(result['rejected_events'], 4)


if __name__ == '__main__': unittest.main()
