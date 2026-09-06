#!/usr/bin/env python3
"""Validate camera coverage without manufacturing atom bindings."""
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[1]

def verify():
    registry = yaml.safe_load((ROOT/'docs/foundations/devices.yaml').read_text())
    mapping = registry['room_atom_map']
    facts = (ROOT/'films/lib/blender/API-FACTS.md').read_text()
    import re
    camera_section = facts.split('Twelve cameras, one per room')[1].split('The earlier')[0]
    cameras = set(re.findall(r'Camera_[A-Za-z]+', camera_section))
    assert set(mapping) == cameras, 'Camera coverage differs from API-FACTS.md'
    for camera, row in mapping.items():
        assert set(row['atoms']) <= registry['atoms'].keys(), camera
        assert row['status'] == ('mapped' if row['atoms'] else 'concept_only' if row['concepts'] else 'unmapped'), camera
        assert row['reason'], camera
        for atom in row['atoms']:
            print(f'{row["room"]} / {camera}: {atom} — {registry["atoms"][atom]}')
        for concept in row['concepts']:
            print(f'{row["room"]} / {camera}: concept={concept} (not an invented atom)')
        if row['status'] == 'unmapped':
            print(f'{row["room"]} / {camera}: unmapped')
    print(f'unmapped rooms: {sum(r["status"] == "unmapped" for r in mapping.values())}; '
          f'rooms without atom binding: {sum(not r["atoms"] for r in mapping.values())} '
          '(locator: docs/foundations/devices.yaml:room_atom_map)')
    return mapping

if __name__ == '__main__':
    verify()
