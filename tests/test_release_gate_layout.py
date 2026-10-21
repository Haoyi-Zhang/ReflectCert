"""Owned temporary layouts; never compile a paper or rerun a campaign."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from release_gate import pdf_page_count, project_layout_matches, scope_limits_present


class ProjectLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.artifact = self.project / 'artifact'
        self.artifact.mkdir()
        (self.project / 'paper').mkdir()

    def test_candidate_two_directory_layout(self):
        self.assertTrue(project_layout_matches(self.project, self.artifact))

    def test_repository_metadata_does_not_break_consumed_layout(self):
        (self.project / '.github').mkdir()
        (self.project / '.git').mkdir()
        (self.project / 'README.md').write_text('Project entry point', encoding='utf-8')
        self.assertTrue(project_layout_matches(self.project, self.artifact))

    def test_missing_paper_is_rejected(self):
        (self.project / 'paper').rmdir()
        self.assertFalse(project_layout_matches(self.project, self.artifact))

    def test_unrelated_artifact_directory_is_rejected(self):
        other = self.project / 'other'
        other.mkdir()
        self.assertFalse(project_layout_matches(self.project, other))

    def test_current_scope_with_line_wrapping_is_recognized(self):
        source=('The events establish operation identity, not\nAndroid data flow, '
                'whole-app execution, or classpath completeness.\n'
                'We distinguish minimum-cardinality witnesses and 11 manual projections.')
        self.assertTrue(scope_limits_present(source))

    def test_scope_guard_does_not_accept_a_positive_completeness_claim(self):
        self.assertFalse(scope_limits_present(
            'We prove Android data flow, whole-app execution, or classpath completeness. '
            'minimum-cardinality manual projections'))

    def test_scope_guard_retains_manual_and_minimality_conditions(self):
        source='not Android data flow, whole-app execution, or classpath completeness'
        self.assertFalse(scope_limits_present(source+' manual projections'))
        self.assertFalse(scope_limits_present(source+' minimum-cardinality'))

    def test_localized_pdfinfo_is_read_without_decoding_metadata(self):
        info='CreationDate: 中国标准时间\nPages: 39\n'.encode('gbk')
        with patch('subprocess.check_output',return_value=info):
            self.assertEqual(pdf_page_count(Path('main.pdf')),39)

    def test_pdfinfo_missing_page_count_fails(self):
        with patch('subprocess.check_output',return_value=b'Title: Example\n'):
            with self.assertRaisesRegex(ValueError,'cannot determine'):
                pdf_page_count(Path('main.pdf'))


if __name__ == '__main__':
    unittest.main()
