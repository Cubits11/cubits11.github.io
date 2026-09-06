#!/usr/bin/env python3
"""Pinned two-process Blender render harness; never saves the input world.

python3 films/lib/blender/render.py --blend WORLD --camera Camera_WorldHero \
    --frame 120 --output-dir /tmp/world-hero
Defaults preserve source resolution and appearance; PNG output is mandatory.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import determinism


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--blend', type=Path, required=True)
    p.add_argument('--camera', required=True)
    p.add_argument('--frame', type=int, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--engine', choices=['BLENDER_EEVEE', 'CYCLES'])
    p.add_argument('--resolution', nargs=2, type=int, metavar=('WIDTH', 'HEIGHT'))
    p.add_argument('--percentage', type=int)
    p.add_argument('--worker', type=int, choices=[1, 2], help=argparse.SUPPRESS)
    return p


def worker(args):
    import bpy

    bpy.ops.wm.open_mainfile(filepath=str(args.blend))
    scene = bpy.context.scene
    engine = args.engine or scene.render.engine
    if engine not in ('BLENDER_EEVEE', 'CYCLES'):
        raise ValueError('unsupported source engine: ' + engine)
    scene.render.engine = engine
    if scene.render.engine != engine:
        raise RuntimeError('engine assignment failed')
    camera = scene.objects.get(args.camera)
    if camera is None or camera.type != 'CAMERA':
        raise ValueError('camera not found in scene: ' + args.camera)
    # Timeline camera markers otherwise override the requested camera at frame_set
    # and during rendering. Override only in memory; never save the source.
    marker_overrides = [marker.name for marker in scene.timeline_markers if marker.camera]
    for marker in scene.timeline_markers:
        marker.camera = None
    scene.frame_set(args.frame)
    scene.camera = camera
    if args.resolution:
        scene.render.resolution_x, scene.render.resolution_y = args.resolution
    if args.percentage is not None:
        scene.render.resolution_percentage = args.percentage
    scene.render.image_settings.file_format = 'PNG'
    if engine == 'CYCLES':
        scene.cycles.device = 'CPU'
        scene.cycles.samples = 8
        scene.cycles.seed = 0
        scene.cycles.use_denoising = False
        scene.cycles.use_animated_seed = False
        scene.cycles.use_adaptive_sampling = False
        sample_names = ['device', 'samples', 'seed', 'use_denoising',
                        'use_animated_seed', 'use_adaptive_sampling']
        sample_owner = scene.cycles
    else:
        scene.eevee.taa_render_samples = 48
        scene.eevee.use_taa_reprojection = True
        scene.eevee.use_raytracing = False
        scene.eevee.use_shadows = True
        sample_names = ['taa_render_samples', 'use_taa_reprojection', 'use_raytracing', 'use_shadows']
        sample_owner = scene.eevee
    settings = {
        'engine': scene.render.engine,
        'res_x': scene.render.resolution_x,
        'res_y': scene.render.resolution_y,
        'res_percentage': scene.render.resolution_percentage,
        'format': scene.render.image_settings.file_format,
        'color_depth': scene.render.image_settings.color_depth,
        'color_mode': scene.render.image_settings.color_mode,
        'view_transform': scene.view_settings.view_transform,
        'look': scene.view_settings.look,
        'exposure': scene.view_settings.exposure,
        'gamma': scene.view_settings.gamma,
        'frame': scene.frame_current,
        'camera': scene.camera.name,
        'disabled_camera_markers': marker_overrides,
        'sampling': {name: getattr(sample_owner, name) for name in sample_names},
        'sampling_locator': 'films/lib/blender/API-FACTS.md:Settings a receipt must pin',
        'scene_locator': str(args.blend),
    }
    scene.render.filepath = str(args.output_dir / f'render-{args.worker}.png')
    bpy.ops.render.render(write_still=True)
    if scene.camera != camera or scene.frame_current != args.frame:
        raise RuntimeError('requested camera/frame changed during render')
    (args.output_dir / f'settings-{args.worker}.json').write_text(json.dumps(settings, indent=2) + '\n')


def publish_receipt(blend, renders, settings, destination):
    comparison = determinism.compare(*renders)
    if comparison['unexpected'] or not comparison['identical_pixels']:
        raise RuntimeError('receipt refused: ' + json.dumps(comparison))
    result = determinism.receipt(blend, renders, settings)
    if result['determinism']['unexpected'] or not result['determinism']['identical_pixels']:
        raise RuntimeError('receipt refused: outputs changed during verification')
    result['non_claims'].append('No device faithfulness, numeral provenance in scene text, or scene correctness was audited.')
    # Exclusive creation prevents an earlier receipt from being mistaken for this run.
    with destination.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    return result


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    args.blend = args.blend.expanduser().resolve(strict=True)
    args.output_dir = args.output_dir.expanduser().resolve()
    if args.resolution and min(args.resolution) <= 0:
        p.error('resolution must be positive')
    if args.percentage is not None and not 1 <= args.percentage <= 100:
        p.error('percentage must be in 1..100')
    if args.worker:
        worker(args)
        return
    args.output_dir.mkdir(parents=True, exist_ok=False)
    before = determinism.file_sha256(args.blend)
    command = [determinism.BLENDER, '-b', '--factory-startup', '-noaudio',
               '--python-exit-code', '1', '-P', str(Path(__file__).resolve()), '--',
               '--blend', str(args.blend), '--camera', args.camera,
               '--frame', str(args.frame), '--output-dir', str(args.output_dir)]
    if args.engine:
        command += ['--engine', args.engine]
    if args.resolution:
        command += ['--resolution', *map(str, args.resolution)]
    if args.percentage is not None:
        command += ['--percentage', str(args.percentage)]
    for run in (1, 2):
        with (args.output_dir / f'blender-{run}.log').open('w') as log:
            subprocess.run(command + ['--worker', str(run)], stdout=log, stderr=subprocess.STDOUT, check=True)
    settings = [json.loads((args.output_dir / f'settings-{run}.json').read_text()) for run in (1, 2)]
    if settings[0] != settings[1]:
        raise RuntimeError('receipt refused: settings differ between runs')
    if before != determinism.file_sha256(args.blend):
        raise RuntimeError('receipt refused: source blend changed')
    result = publish_receipt(args.blend, [args.output_dir / f'render-{run}.png' for run in (1, 2)],
                             settings[0], args.output_dir / 'receipt.json')
    print(json.dumps(result['determinism'], indent=2))
    print(args.output_dir / 'receipt.json')


if __name__ == '__main__':
    main(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
