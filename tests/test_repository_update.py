"""Scheduled commits must use protected PRs without a direct main push."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import queue_repository_update as update


class RepositoryUpdate(unittest.TestCase):
    def test_queue_requests_merge_commit_and_returns_to_main(self):
        branch = 'claude/cycle-cadence-fixture'
        calls = []
        def git(*args):
            calls.append(args)
            return {('branch', '--show-current'): branch, ('status', '--porcelain'): '',
                    ('remote', 'get-url', '--push', 'origin'): 'https://github.com/Cubits11/cubits11.github.io.git',
                    ('log', '-1', '--format=%s'): 'cadence: fixture'}.get(args, '')
        with patch.object(update, 'git', git), patch.object(update, 'request') as request:
            request.side_effect = [{'html_url': 'https://github.com/example/pr/1', 'node_id': 'PR_fixture'}, {}]
            update.queue(branch)
        self.assertIn(('push', '-u', 'origin', 'HEAD:refs/heads/' + branch), calls)
        self.assertNotIn(('push', 'origin', 'main'), calls)
        self.assertEqual(calls[-1], ('checkout', 'main'))
        self.assertIn('mergeMethod:MERGE', request.call_args.args[1]['query'])

    def test_wrong_branch_or_dirty_tree_refuses_without_network(self):
        for actual, status in [('main', ''), ('claude/cycle-fixture', ' M evidence')]:
            with patch.object(update, 'git', side_effect=[actual, status]), patch.object(update, 'request') as request:
                with self.assertRaises(ValueError): update.queue('claude/cycle-fixture')
                request.assert_not_called()

    def test_unrelated_branch_name_refuses(self):
        with patch.object(update, 'git') as git:
            with self.assertRaises(ValueError): update.queue('main')
            git.assert_not_called()

    def test_api_failure_keeps_recovery_branch(self):
        branch = 'claude/cycle-fixture'
        def git(*args):
            return {('branch', '--show-current'): branch, ('status', '--porcelain'): '',
                    ('remote', 'get-url', '--push', 'origin'): 'https://github.com/Cubits11/cubits11.github.io.git'}.get(args, '')
        with patch.object(update, 'git', side_effect=git) as commands, patch.object(update, 'request', side_effect=RuntimeError('unavailable')):
            with self.assertRaises(RuntimeError): update.queue(branch)
        self.assertNotIn(('checkout', 'main'), [c.args for c in commands.call_args_list])


if __name__ == '__main__':
    unittest.main()
