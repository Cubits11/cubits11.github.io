#!/usr/bin/env python3
"""Negative-path tests for the finite audit and receipt publication boundary."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'films/lib/blender'))
import audit_device
import render


def png(path, pixel, text):
    def chunk(name, data):
        return struct.pack('>I', len(data)) + name + data + struct.pack('>I', zlib.crc32(name+data))
    path.write_bytes(b'\x89PNG\r\n\x1a\n' +
                     chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) +
                     chunk(b'tEXt', b'note\x00' + text) +
                     chunk(b'IDAT', zlib.compress(b'\x00' + pixel)) + chunk(b'IEND', b''))


class DeviceAuditTests(unittest.TestCase):
    def test_expected_enumerations(self):
        expected = {'D-002': (11, 11), 'D-003': (2, 2), 'D-004': (21, 21),
                    'D-005': (2, 2), 'D-006': (4, 3), 'D-007': (70, 2)}
        for key, model in audit_device.models().items():
            result = audit_device.audit(model)
            self.assertEqual(result['status'], 'equal', key)
            self.assertEqual((result['candidate_count'], result['feasible_count']), expected[key])
            self.assertEqual(result['rung'], 'SELF-AUDITED')

    def test_illegal_overlap_witness(self):
        model = audit_device.models()['D-002']
        model.moves = lambda s: [s+1] if s < 11 else []
        result = audit_device.audit(model)
        self.assertEqual(result['reachable_but_infeasible'], 11)
        self.assertEqual(result['rung'], 'ILLUSTRATIVE')

    def test_unreachable_world_witness(self):
        model = audit_device.models()['D-007']
        model.moves = lambda s: []
        result = audit_device.audit(model)
        self.assertEqual(result['status'], 'failed')
        self.assertTrue(model.feasible(result['feasible_but_unreachable']))

    def test_loose_bead_moves_fail(self):
        model = audit_device.models()['D-007']
        model.moves = lambda s: model.universe
        result = audit_device.audit(model)
        self.assertEqual(result['reachable_count'], 70)
        self.assertFalse(model.feasible(result['reachable_but_infeasible']))


class ReceiptTests(unittest.TestCase):
    def test_timeline_cannot_replace_requested_camera(self):
        with tempfile.TemporaryDirectory() as temp:
            wanted = NS(name='Camera_WorldHero', type='CAMERA')
            other = NS(name='Camera_EvidenceVault', type='CAMERA')
            marker = NS(name='bound camera', camera=other)
            scene = NS(camera=other, timeline_markers=[marker],
                       objects={wanted.name: wanted}, eevee=NS(),
                       render=NS(engine='BLENDER_EEVEE', resolution_x=1920,
                                 resolution_y=1080, resolution_percentage=100,
                                 image_settings=NS(file_format='PNG', color_depth='8', color_mode='RGBA')),
                       view_settings=NS(view_transform='AgX', look='fixture', exposure=0, gamma=1))

            def frame_set(frame):
                scene.frame_current = frame
                if marker.camera:
                    scene.camera = marker.camera

            scene.frame_set = frame_set
            bpy = NS(context=NS(scene=scene),
                     ops=NS(wm=NS(open_mainfile=lambda **kw: None),
                            render=NS(render=lambda **kw: frame_set(scene.frame_current))))
            args = NS(blend=Path(temp)/'fixture.blend', engine=None,
                      camera=wanted.name, frame=120, resolution=None, percentage=None,
                      output_dir=Path(temp), worker=1)
            with patch.dict(sys.modules, bpy=bpy):
                render.worker(args)
            self.assertIs(scene.camera, wanted)
            self.assertIsNone(marker.camera)

    def test_metadata_allowed_pixel_changes_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a, b, blend = root/'a.png', root/'b.png', root/'scene.blend'
            blend.write_bytes(b'fixture, not a Blender scene')
            png(a, b'\x00\x00\x00', b'first')
            png(b, b'\x00\x00\x00', b'second')
            with patch.object(render.determinism, 'blender_build', return_value={'fixture': True}):
                result = render.publish_receipt(blend, [a, b], {}, root/'receipt.json')
            self.assertTrue(result['determinism']['identical_pixels'])
            self.assertEqual(result['determinism']['unexpected'], [])
            png(b, b'\xff\x00\x00', b'second')
            with self.assertRaisesRegex(RuntimeError, 'receipt refused'):
                render.publish_receipt(blend, [a, b], {}, root/'refused.json')
            self.assertFalse((root/'refused.json').exists())

    def test_non_pixel_unexpected_chunk_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a, b = root/'a.png', root/'b.png'
            png(a, b'\x00\x00\x00', b'first')
            png(b, b'\x00\x00\x00', b'first')
            content = b.read_bytes()
            # Different IHDR width while keeping IDAT unchanged.
            b.write_bytes(content[:19] + b'\x02' + content[20:])
            with self.assertRaisesRegex(RuntimeError, 'IHDR'):
                render.publish_receipt(root/'unused.blend', [a, b], {}, root/'refused.json')
            self.assertFalse((root/'refused.json').exists())


if __name__ == '__main__':
    unittest.main()
