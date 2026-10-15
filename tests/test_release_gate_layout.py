"""Owned temporary layouts; never compile a paper or rerun a campaign."""
from pathlib import Path
import tempfile
import unittest

from release_gate import project_layout_matches


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


if __name__ == '__main__':
    unittest.main()
