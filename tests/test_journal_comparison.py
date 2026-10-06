"""Current descriptive source counts must not overwrite frozen experiment evidence."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from compare_journal import compare
from journal_analysis import emit_csv, trust_surface


class JournalComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rrc-journal-comparison-")
        self.addCleanup(self.temp.cleanup)
        self.expected = Path(self.temp.name) / "expected"
        self.actual = Path(self.temp.name) / "actual"
        self.surface = trust_surface()
        old_surface = copy.deepcopy(self.surface)
        old_surface[-1]["significant_source_lines"] -= 1
        for path, surface in ((self.expected, old_surface), (self.actual, self.surface)):
            path.mkdir()
            emit_csv(path / "trust-surface.csv", surface)
            self.write_summary(path, {"trust_surface": surface, "stage_costs": [],
                                      "witness": {"records": 1826}})
            (path / "strata.csv").write_text("cases\n664\n", encoding="utf-8")

    def write_summary(self, path, value):
        (path / "summary.json").write_text(json.dumps(value), encoding="utf-8")

    def test_default_still_requires_frozen_source_counts(self):
        with self.assertRaisesRegex(SystemExit, "journal result differs"):
            compare(self.expected, self.actual)

    def test_current_counts_are_measured_and_reported_separately(self):
        result = compare(self.expected, self.actual, current_source_surface=True)
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["current_source_surface"], self.surface)
        self.assertTrue(result["source_surface_baseline_changed"])

    def test_wrong_current_summary_counts_are_rejected(self):
        summary = json.loads((self.actual / "summary.json").read_text(encoding="utf-8"))
        summary["trust_surface"][-1]["significant_source_lines"] -= 1
        self.write_summary(self.actual, summary)
        with self.assertRaisesRegex(SystemExit, "current-source trust surface differs: summary.json"):
            compare(self.expected, self.actual, current_source_surface=True)

    def test_wrong_current_csv_counts_are_rejected(self):
        bad = copy.deepcopy(self.surface)
        bad[-1]["significant_source_lines"] -= 1
        emit_csv(self.actual / "trust-surface.csv", bad)
        with self.assertRaisesRegex(SystemExit, "current-source trust surface differs: trust-surface.csv"):
            compare(self.expected, self.actual, current_source_surface=True)

    def test_scientific_summary_difference_is_still_rejected(self):
        summary = json.loads((self.actual / "summary.json").read_text(encoding="utf-8"))
        summary["witness"]["records"] -= 1
        self.write_summary(self.actual, summary)
        with self.assertRaisesRegex(SystemExit, "journal result differs: summary.json"):
            compare(self.expected, self.actual, current_source_surface=True)

    def test_other_csv_difference_is_still_rejected(self):
        (self.actual / "strata.csv").write_text("cases\n663\n", encoding="utf-8")
        with self.assertRaisesRegex(SystemExit, "journal result differs: strata.csv"):
            compare(self.expected, self.actual, current_source_surface=True)


if __name__ == "__main__":
    unittest.main()
