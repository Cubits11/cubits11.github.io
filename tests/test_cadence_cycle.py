"""Exercise unattended recording/publication against disposable Git remotes."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/cadence_cycle.sh'


class CadenceCycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'work'
        self.remote = Path(self.tmp.name) / 'remote.git'
        subprocess.run(['git', 'init', '--bare', '-q', str(self.remote)], check=True)
        self.root.mkdir()
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'commit.gpgsign', 'false')
        (self.root / 'scripts').mkdir()
        (self.root / 'metrics').mkdir()
        (self.root / '_private').mkdir()
        (self.root / '.gitignore').write_text('_private/\n')
        shutil.copy2(SCRIPT, self.root / 'scripts/cadence_cycle.sh')
        (self.root / 'metrics/repo_state.jsonl').write_text('initial\n')
        (self.root / 'owner.txt').write_text('initial\n')
        (self.root / 'scripts/cadence.py').write_text(
            "import sys\nfrom pathlib import Path\n"
            "if sys.argv[1]=='record':\n"
            " with Path('metrics/repo_state.jsonl').open('a') as f: f.write('recorded\\n')\n")
        (self.root / 'scripts/verification_manifest.py').write_text(
            "from pathlib import Path\n"
            "if Path('_private/mutate').exists(): Path('owner.txt').write_text('concurrent edit')\n"
            "raise SystemExit(int(Path('_private/red').exists()))\n")
        (self.root / 'scripts/queue_repository_update.py').write_text(
            "import subprocess,sys\n"
            "from pathlib import Path\n"
            "Path('_private/queued').write_text(sys.argv[1])\n"
            "subprocess.run(['git','push','-q','origin','HEAD:refs/heads/'+sys.argv[1]],check=True)\n"
            "subprocess.run(['git','checkout','-q','main'],check=True)\n")
        self.git('add', '.')
        self.git('commit', '-qm', 'initial')
        self.git('remote', 'add', 'origin', str(self.remote))
        self.git('push', '-q', 'origin', 'main')
        self.initial = self.git('rev-parse', 'HEAD')

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.root, text=True).strip()

    def cycle(self):
        return subprocess.run(['sh', 'scripts/cadence_cycle.sh'], cwd=self.root,
                              capture_output=True, text=True).returncode

    def assert_local_only(self, expected=0):
        self.assertEqual(self.cycle(), expected)
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.initial)
        remote = subprocess.check_output(['git', '--git-dir', str(self.remote),
                                          'rev-parse', 'refs/heads/main'], text=True).strip()
        self.assertEqual(remote, self.initial)
        self.assertIn('recorded', (self.root / 'metrics/repo_state.jsonl').read_text())

    def test_clean_main_publishes_only_record(self):
        self.assertEqual(self.cycle(), 0)
        branch = (self.root / '_private/queued').read_text()
        self.assertTrue(branch.startswith('claude/cycle-cadence-'))
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.initial)
        self.assertEqual(self.git('diff-tree', '--no-commit-id', '--name-only', '-r', branch),
                         'metrics/repo_state.jsonl')
        self.assertEqual(self.git('rev-parse', 'origin/main'), self.initial)
        self.assertEqual(self.git('rev-parse', 'origin/' + branch), self.git('rev-parse', branch))

    def test_feature_branch_records_without_pull_or_push(self):
        self.git('checkout', '-qb', 'feature')
        self.assert_local_only()

    def test_staged_owner_work_is_preserved(self):
        (self.root / 'owner.txt').write_text('owner work')
        self.git('add', 'owner.txt')
        self.assert_local_only()
        self.assertEqual(self.git('diff', '--cached', '--name-only'), 'owner.txt')

    def test_uncommitted_metrics_are_not_swept_into_commit(self):
        (self.root / 'metrics/other.json').write_text('{}')
        self.assert_local_only()

    def test_failed_pull_records_without_publish(self):
        self.git('remote', 'set-url', 'origin', str(self.remote.parent / 'missing.git'))
        self.assert_local_only()

    def test_red_manifest_retains_record(self):
        (self.root / '_private/red').touch()
        self.assert_local_only(1)

    def test_concurrent_owner_edit_stops_publication(self):
        (self.root / '_private/mutate').touch()
        self.assert_local_only(1)

    def test_other_cycle_holds_shared_lock(self):
        (self.root / '_private/cron/repository-cycle.lock').mkdir(parents=True)
        self.assertEqual(self.cycle(), 1)
        self.assertEqual((self.root / 'metrics/repo_state.jsonl').read_text(), 'initial\n')


class DistributionCycleTests(CadenceCycleTests):
    """Exercise branch, lock and concurrent-edit boundaries before API access."""
    def setUp(self):
        super().setUp()
        shutil.copy2(SCRIPT.with_name('distribute_cycle.sh'), self.root / 'scripts/distribute_cycle.sh')
        self.git('add', '.')
        self.git('commit', '-qm', 'distribution fixture')
        self.git('push', '-q', 'origin', 'main')
        self.initial = self.git('rev-parse', 'HEAD')

    def test_distribution_feature_branch_refuses_before_credentials(self):
        self.git('checkout', '-qb', 'feature')
        result = subprocess.run(['sh', 'scripts/distribute_cycle.sh'], cwd=self.root)
        self.assertEqual(result.returncode, 1)
        log = next((self.root / '_private/cron').glob('cycle-*.log')).read_text()
        self.assertIn('not on main', log)
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.initial)

    def test_distribution_shared_lock_refuses_before_credentials(self):
        (self.root / '_private/cron/repository-cycle.lock').mkdir(parents=True)
        result = subprocess.run(['sh', 'scripts/distribute_cycle.sh'], cwd=self.root)
        self.assertEqual(result.returncode, 1)
        log = next((self.root / '_private/cron').glob('cycle-*.log')).read_text()
        self.assertIn('already running', log)


if __name__ == '__main__':
    unittest.main()
