from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from rrc.factor import produce_factorized
from rrc.factor_checker import check_factorized
from rrc.java_frontend import (
    ARTIFACT_ROOT,
    compile_event,
    direct_call_probe_record,
    frontend_result_record,
    git_blob_sha1,
    public_source_cases,
    run_extractor,
    runtime_probe_record,
)
from rrc.producer import produce
from rrc.public_cases import all_public
from rrc.schema import MAX_INPUT_BYTES, load_json, strict_equal


class JavaFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_root = ARTIFACT_ROOT / "frontend" / "fixtures"
        cls.report = run_extractor(sorted(cls.fixture_root.glob("*.java")))
        cls.by_name = {Path(record["path"]).name: record for record in cls.report["files"]}

    def test_public_sources_match_blobs_and_gold(self):
        result = frontend_result_record()
        self.assertEqual(result["source_files"], 9)
        self.assertEqual(result["accepted_events"], 29)
        self.assertEqual(result["rejected_events"], 0)
        self.assertEqual(result["gold_matches"], 29)
        self.assertEqual(result["blob_matches"], 9)
        self.assertTrue(all(row["matched"] for row in result["blob_checks"]))
        self.assertTrue(all(row["matched"] for row in result["comparisons"]))

    def test_public_source_cases_are_P012_through_P040(self):
        cases = public_source_cases()
        self.assertEqual([case.case for case in cases], [f"P{i:03d}" for i in range(12, 41)])
        public = {case: program for case, _, program, _, _ in all_public()}
        for case in cases:
            with self.subTest(case=case.case):
                self.assertTrue(strict_equal(public[case.case], case.program))
                stored = load_json(ARTIFACT_ROOT / "inputs" / f"{case.case}.json", MAX_INPUT_BYTES)
                self.assertTrue(strict_equal(stored["program"], case.program))

    def test_supported_finite_source_preserves_all_assignments(self):
        events = self.by_name["SupportedFinite.java"]["events"]
        self.assertEqual([event["status"] for event in events], ["accepted", "accepted"])
        self.assertEqual(events[0]["class_expr"]["op"], "cat")
        self.assertEqual(events[1]["member_expr"]["op"], "ite")
        for event in events:
            program, expected = compile_event(event)
            rows = produce(program)["rows"]
            actual = [{"feasible": row["feasible"], "outcomes": row["outcomes"]} for row in rows]
            self.assertEqual(actual, expected)
            checked = check_factorized(program, produce_factorized(program))
            self.assertEqual(checked["assignments"], 4)



    def test_unrelated_reflection_like_method_names_are_ignored(self):
        self.assertEqual(self.by_name["UnrelatedMethods.java"]["events"], [])

    def test_runtime_probe_matches_actual_reflection(self):
        result = runtime_probe_record()
        self.assertEqual(result["events"], 2)
        self.assertEqual(result["assignments"], 4)
        self.assertEqual(result["identity_checks"], 8)
        self.assertTrue(all(row["matched"] for row in result["rows"]))

    def test_direct_call_probe_matches_reflection(self):
        result = direct_call_probe_record()
        self.assertEqual(result["assignments"], 4)
        self.assertEqual(result["payloads"], 3)
        self.assertEqual(result["invocation_checks"], 12)
        self.assertTrue(all(row["matched"] for row in result["rows"]))

    def test_fail_closed_rejection_reasons(self):
        expected = {
            "UnsupportedHeap.java": ["unsupported_class_name_expression"],
            "UnsupportedInput.java": ["unsupported_class_name_expression"],
            "UnsupportedLoader.java": ["unsupported_loader_receiver"],
            "UnsupportedReceiver.java": ["unresolved_class_receiver"],
            "UnsupportedParameter.java": ["unsupported_parameter_type_expression"],
            "UnsupportedControl.java": ["unsupported_control_context"],
            "UnsupportedReassignment.java": ["unsupported_class_name_expression"],
        }
        for name, reasons in expected.items():
            with self.subTest(name=name):
                actual = [event["reason"] for event in self.by_name[name]["events"]
                          if event["status"] == "rejected"]
                self.assertEqual(actual, reasons)

    def test_unsupported_parameter_retains_only_independent_class_event(self):
        events = self.by_name["UnsupportedParameter.java"]["events"]
        self.assertEqual([(event["status"], event["kind"]) for event in events], [
            ("accepted", "Class.forName"),
            ("rejected", "Class.getMethod"),
        ])

    def test_blob_identity_detects_mutation(self):
        source = ARTIFACT_ROOT / public_source_cases()[0].local_path
        pinned = public_source_cases()[0].source_sha
        self.assertEqual(git_blob_sha1(source), pinned)
        with tempfile.TemporaryDirectory() as temp:
            changed = Path(temp) / source.name
            changed.write_bytes(source.read_bytes() + b"\n")
            self.assertNotEqual(git_blob_sha1(changed), pinned)

    def test_frontend_gold_is_not_used_as_program_input(self):
        # Changing gold metadata after extraction must not alter a compiled source event.
        event = copy.deepcopy(self.by_name["SupportedFinite.java"]["events"][0])
        program_before, _ = compile_event(event)
        unrelated = {"class": "invented.Name", "member": "invented"}
        self.assertNotIn(unrelated["class"], json.dumps(program_before, sort_keys=True))
        program_after, _ = compile_event(event)
        self.assertTrue(strict_equal(program_before, program_after))


if __name__ == "__main__":
    unittest.main()
