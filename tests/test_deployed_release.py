"""A 200 response cannot stand in for the release we actually verified."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import smoke_deployed as smoke


class DeployedRelease(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.files = {'index.html': b'current page', 'claims/index.json': b'{}',
                      'ns/falsifiable/v1/context.json': b'{}',
                      'films/example/renders/example__square.mp4': b'current video',
                      'films/example/renders/poster.jpg': b'current poster'}
        for name, data in self.files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        (self.root / 'films/example/manifest.yaml').write_text('id: example\nrender:\n  primary: square\n')
        (self.root / 'films/example/renders/example__square.receipt.json').write_text(json.dumps(
            {'outputs': {'master': 'renders/example__square.mp4', 'poster': 'renders/poster.jpg'}}))
        self.remote = dict(self.files)

    def check(self, page=b'current page'):
        def fetch(url):
            rel = url.removeprefix('https://example.test/')
            return (self.remote[rel], None) if rel in self.remote else (None, 'HTTP 404: ' + rel)
        with patch.object(smoke, 'ROOT', self.root), patch.object(smoke, 'fetch', fetch):
            return smoke.release_bytes('https://example.test', {'https://example.test/': page})

    def test_exact_release_passes_including_square_primary(self):
        self.assertEqual(self.check(), [])

    def test_stale_successful_page_fails(self):
        self.assertTrue(any('page bytes' in f for f in self.check(b'old release')))

    def test_damaged_video_fails(self):
        self.remote['films/example/renders/example__square.mp4'] = b'damaged'
        self.assertTrue(any('asset bytes' in f for f in self.check()))

    def test_missing_context_fails(self):
        del self.remote['ns/falsifiable/v1/context.json']
        self.assertTrue(any('404' in f for f in self.check()))


if __name__ == '__main__':
    unittest.main()
