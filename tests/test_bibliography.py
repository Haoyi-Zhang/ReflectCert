from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from verify_bibliography import parse_bib, verify


ROOT = Path(__file__).resolve().parents[1]
BIB = ROOT / "docs" / "references.bib"
AUDIT = ROOT / "docs" / "bibliography-audit.csv"
LITERATURE = ROOT / "docs" / "literature.csv"


class BibliographyTests(unittest.TestCase):
    def test_frozen_bibliography_and_audit_match(self):
        result = verify(BIB, AUDIT, LITERATURE)
        self.assertEqual(result["entries"], 66)
        self.assertEqual(result["unique_dois"], 60)
        self.assertEqual(result["no_doi_records"], 6)
        self.assertGreaterEqual(result["entries"], result["minimum_required"])

    def test_duplicate_doi_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "references.bib"
            text = BIB.read_text(encoding="utf-8")
            text = text.replace("10.1145/3440033", "10.1145/2931037.2931044", 1)
            path.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate DOI"):
                verify(path, AUDIT, LITERATURE)

    def test_audit_inventory_omission_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "audit.csv"
            with AUDIT.open(newline="", encoding="utf-8") as stream:
                reader = csv.DictReader(stream)
                rows = list(reader)
                fields = reader.fieldnames
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows[:-1])
            with self.assertRaisesRegex(ValueError, "audit inventory mismatch"):
                verify(BIB, path, LITERATURE)

    def test_required_bibliographic_fields_are_present(self):
        entries = parse_bib(BIB)
        for key, fields in entries.items():
            with self.subTest(key=key):
                self.assertTrue(fields["author"])
                self.assertTrue(fields["title"])
                self.assertTrue(fields["year"])
                self.assertTrue(fields.get("journal") or fields.get("booktitle") or fields.get("organization"))


if __name__ == "__main__":
    unittest.main()
