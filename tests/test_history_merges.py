"""Merging a release must neither lose nor double-count its claim transitions."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import claims_history as history


class HistoryMerges(unittest.TestCase):
    def test_two_branch_changes_survive_merge_once_and_removal_survives(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            def git(*args):
                return subprocess.check_output(['git', *args], cwd=root, text=True, stderr=subprocess.PIPE).strip()
            git('init', '-q', '-b', 'main')
            git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.invalid')
            git('config', 'commit.gpgsign', 'false')
            def claim(value):
                (root / 'claims.yaml').write_text('claims: []\n' if value is None else
                    'claims:\n- id: A\n  proposition: ' + value + '\n')
                git('add', 'claims.yaml'); git('commit', '-qm', 'state ' + str(value))
            claim('zero')
            (root / 'claims_history.yaml').write_text('genesis:\n  anchor_commit: ' + git('rev-parse', 'HEAD') + '\n')
            git('checkout', '-qb', 'feature')
            claim('one'); claim('two')
            with patch.object(history, 'ROOT', root), patch.object(history, 'HISTORY', root / 'claims_history.yaml'):
                before = history.commitment_events()
                git('checkout', '-q', 'main')
                git('merge', '--no-ff', '-qm', 'merge feature', 'feature')
                self.assertEqual(history.commitment_events(), before)
                self.assertEqual([e['kind'] for e in before], ['BIRTH', 'CHANGE', 'CHANGE'])
                git('checkout', '-qb', 'remove')
                claim(None)
                expected = history.commitment_events()
                git('checkout', '-q', 'main')
                git('merge', '--no-ff', '-qm', 'merge removal', 'remove')
                self.assertEqual(history.commitment_events(), expected)
                self.assertEqual(expected[-1]['kind'], 'REMOVAL')


if __name__ == '__main__':
    unittest.main()
