"""Browser captures must match the dimensions a receipt will assert."""
import importlib.util
import base64
import subprocess
import tempfile
from unittest.mock import patch
from pathlib import Path
import struct
import sys
import unittest

path = Path(__file__).resolve().parents[1] / 'scripts/films/render_film.py'
sys.path.insert(0, str(path.parent))  # render_film imports its sibling facts_digest
spec = importlib.util.spec_from_file_location('render_film', path)
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)


def header(w, h):
    return b'\x89PNG\r\n\x1a\n' + struct.pack('>I', 13) + b'IHDR' + struct.pack('>II', w, h)


class CaptureTests(unittest.TestCase):
    def test_phone_audit_refuses_small_or_missing_actual_text(self):
        good = {'minimum_canvas_px':54,'audited_draws':12,'minimum_examples':['shared misses']}
        self.assertEqual(render.phone_text_result(good,1080)['minimum_css_px'],14)
        for audit in [{},dict(good,minimum_canvas_px=44),dict(good,audited_draws=0),
                      dict(good,minimum_canvas_px=float('nan')),dict(good,minimum_canvas_px=float('inf')),
                      dict(good,audited_draws=True),dict(good,audited_draws=-1)]:
            with self.assertRaises(ValueError):
                render.phone_text_result(audit,1080)
        for width in (0, -1080, float('nan'), float('inf'), True):
            with self.assertRaises(ValueError):
                render.phone_text_result(good,width)

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

    def test_batch_refuses_missing_or_clipped_frames(self):
        class Page:
            def __init__(self, values): self.values = values
            def evaluate(self, script, spec): return self.values
        valid = base64.b64encode(header(1080,1920)).decode()
        self.assertEqual(len(render.capture_canvas_batch(Page([valid,valid]),0,2,30,1080,1920)),2)
        with self.assertRaisesRegex(ValueError,'frame count'):
            render.capture_canvas_batch(Page([valid]),0,2,30,1080,1920)
        clipped = base64.b64encode(header(1080,1833)).decode()
        with self.assertRaisesRegex(ValueError,'capture dimensions'):
            render.capture_canvas_batch(Page([valid,clipped]),0,2,30,1080,1920)

    def test_input_snapshot_accepts_unchanged_bytes_and_rejects_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'film.html'; source.write_text('original source')
            facts=Path(temp)/'facts.json'; facts.write_text('{"original": true}')
            paths={'film.html':source,'films/data/facts.json':facts}
            initial=render.snapshot_inputs(paths)
            render.require_unchanged_inputs(paths,initial)
            facts.write_text('{"changed": true}')
            with self.assertRaisesRegex(ValueError,'films/data/facts.json'):
                render.require_unchanged_inputs(paths,initial)
            self.assertEqual(initial['film.html'],render.sha256_file(source))
            self.assertNotEqual(initial['films/data/facts.json'],render.sha256_file(facts))

    def test_input_change_during_encoding_preserves_last_good_video(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'film.html'; source.write_text('captured source')
            paths={'film.html':source}; initial=render.snapshot_inputs(paths)
            out=Path(temp)/'film.mp4'; out.write_bytes(b'previous good video')
            def encoded_then_changed(command, **kwargs):
                Path(command[-1]).write_bytes(b'new encoded video')
                source.write_text('source changed while encoding')
                return subprocess.CompletedProcess(command,0)
            with patch.object(render.subprocess,'run',side_effect=encoded_then_changed):
                with self.assertRaisesRegex(ValueError,'render inputs changed'):
                    render.encode('ffmpeg',Path(temp),30,out,20,
                                  before_promote=lambda: render.require_unchanged_inputs(paths,initial))
            self.assertEqual(out.read_bytes(),b'previous good video')
            self.assertFalse((Path(temp)/'.film.rendering.mp4').exists())

    def test_failed_encoder_preserves_last_good_video(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'film.mp4'; out.write_bytes(b'previous good video')
            def failed(command, **kwargs):
                Path(command[-1]).write_bytes(b'partial failed video')
                raise subprocess.CalledProcessError(1,command)
            with patch.object(render.subprocess,'run',side_effect=failed):
                with self.assertRaises(subprocess.CalledProcessError):
                    render.encode('ffmpeg',Path(temp),30,out,20)
            self.assertEqual(out.read_bytes(),b'previous good video')
            self.assertFalse((Path(temp)/'.film.rendering.mp4').exists())


if __name__ == '__main__':
    unittest.main()
