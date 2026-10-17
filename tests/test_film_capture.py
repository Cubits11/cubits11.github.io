"""Browser captures must match the dimensions a receipt will assert."""
import importlib.util
from pathlib import Path
import struct
import unittest

path = Path(__file__).resolve().parents[1] / 'scripts/films/render_film.py'
spec = importlib.util.spec_from_file_location('render_film', path)
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)


def header(w, h):
    return b'\x89PNG\r\n\x1a\n' + struct.pack('>I', 13) + b'IHDR' + struct.pack('>II', w, h)


class CaptureTests(unittest.TestCase):
    def test_declared_formats(self):
        for w, h in [(1920, 1080), (1080, 1920), (1080, 1080)]:
            render.validate_frame_size(header(w, h), w, h)

    def test_observed_browser_clipping_is_refused(self):
        for w, h in [(1080, 1920), (1080, 1080)]:
            with self.assertRaisesRegex(ValueError, 'capture dimensions'):
                render.validate_frame_size(header(w, h - 87), w, h)

    def test_malformed_capture_is_refused(self):
        for data in [b'', b'not a PNG', header(1080, 1080)[:20]]:
            with self.assertRaisesRegex(ValueError, 'IHDR'):
                render.validate_frame_size(data, 1080, 1080)


if __name__ == '__main__':
    unittest.main()
