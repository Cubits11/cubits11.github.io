"""Private cached pages must not become public sitemap or frontend inputs."""
import importlib.util
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class PublicDiscovery(unittest.TestCase):
    def test_every_public_player_has_a_native_proof_link(self):
        class Players(HTMLParser):
            def __init__(self):
                super().__init__()
                self.in_video = False
                self.waiting = False
                self.links = []
            def handle_starttag(self, tag, attrs):
                if tag == 'video':
                    if self.waiting:
                        self.links.append(None)
                    self.in_video = True
                elif tag == 'a' and self.waiting and not self.in_video:
                    self.links.append(dict(attrs).get('href'))
                    self.waiting = False
            def handle_endtag(self, tag):
                if tag == 'video':
                    self.in_video = False
                    self.waiting = True
        players = 0
        for page in load('generate_sitemap').discover_pages():
            parsed = Players()
            parsed.feed(page.read_text())
            if parsed.waiting:
                parsed.links.append(None)
            for href in parsed.links:
                players += 1
                self.assertIn(href, ('/try/', '/try/#try-a'), page.relative_to(ROOT))
        self.assertGreater(players, 0, 'No public players were checked')

    def test_private_caches_are_not_public_pages(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ['index.html', 'explore/index.html', '_private/cache/index.html',
                         '.cache/index.html', 'explore/_draft/index.html']:
                page = root / name
                page.parent.mkdir(parents=True, exist_ok=True)
                page.write_text('<html></html>')
            for name, function in [('generate_sitemap', 'discover_pages'),
                                   ('verify_growth', 'pages'), ('verify_frontend', 'page_files')]:
                module = load(name)
                module.ROOT = root
                found = {p.relative_to(root).as_posix() for p in getattr(module,function)()}
                self.assertEqual(found, {'index.html', 'explore/index.html'}, name)

if __name__ == '__main__':
    unittest.main()
