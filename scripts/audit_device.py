#!/usr/bin/env python3
"""Finite digital N2 models; see docs/foundations/AUDIT-MODELS.md.

No bpy, physical audit, registry promotion, or claim of learning efficacy.
"""
from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
from itertools import combinations, product
import json
from pathlib import Path
from typing import Callable

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / 'docs/foundations/devices.yaml'


@dataclass
class Model:
    universe: set
    initial: object
    moves: Callable
    feasible: Callable
    scope: str


def reachable(initial, moves):
    seen = {initial}
    queue = deque([initial])
    while queue:
        for state in moves(queue.popleft()):
            if state not in seen:
                seen.add(state)
                queue.append(state)
    return seen


def models():
    # Constants and parameter scopes: AUDIT-MODELS.md, keyed by device ID.
    overlaps = set(range(11))
    cuts = {tuple(int(i >= cut) for i in range(20)) for cut in range(21)}
    corners = tuple(product(range(2), repeat=3))
    arrangements = set(combinations(corners, 4))
    even = tuple(c for c in corners if sum(c) % 2 == 0)
    odd = tuple(c for c in corners if sum(c) % 2 == 1)

    def shadows_match(state):
        return all(sum(c[a] == x and c[b] == y for c in state) == 1
                   for a, b in combinations(range(3), 2)
                   for x, y in product(range(2), repeat=2))

    def threshold_moves(state):
        cut = state.count(0)
        return [tuple(int(i >= n) for i in range(20))
                for n in (cut - 1, cut + 1) if 0 <= n <= 20]

    return {
        'D-002': Model(overlaps, 0,
                       lambda s: [n for n in (s-1, s+1) if 0 <= n <= 10],
                       lambda s: s >= max(0, 10+10-100) and s <= min(10, 10),
                       'integer overlap counts; population=100, miss counts=(10,10); readout=overlap/100'),
        'D-003': Model({'both-must-open', 'either-opens'}, 'both-must-open',
                       lambda s: ['either-opens' if s == 'both-must-open' else 'both-must-open'],
                       lambda s: s in ('both-must-open', 'either-opens'),
                       'named composition rules only; no rates or routing order'),
        'D-004': Model(cuts, (1,)*20, threshold_moves,
                       lambda s: all(a <= b for a, b in zip(s, s[1:])),
                       'fixed strict ordering of 20 objects; one ruler; binary suffix readout'),
        'D-005': Model({'whole-page', 'slip'}, 'whole-page',
                       lambda s: ['slip' if s == 'whole-page' else 'whole-page'],
                       lambda s: s in ('whole-page', 'slip'),
                       'whole-page encodes full exposure; slip encodes routed exposure'),
        'D-006': Model({1, 2, 3, 4}, 2,
                       lambda s: [n for n in (s-1, s+1) if 2 <= n <= 4],
                       lambda s: s in range(1, 5) and s != 1,
                       'representative Latin cell: symbols=1..4; row excludes 1; column adds no exclusion'),
        'D-007': Model(arrangements, even,
                       lambda s: [odd if s == even else even], shadows_match,
                       'four occupied distinct binary corners; uniform pair shadows; atomic parity switch only'),
    }


def audit(model):
    reached = reachable(model.initial, model.moves)
    feasible = {s for s in model.universe if model.feasible(s)}
    extra, missing = reached - feasible, feasible - reached
    result = {'status': 'equal' if not extra and not missing else 'failed',
              'rung': 'SELF-AUDITED' if not extra and not missing else 'ILLUSTRATIVE',
              'candidate_count': len(model.universe), 'reachable_count': len(reached),
              'feasible_count': len(feasible), 'scope': model.scope}
    for key, states in [('reachable_but_infeasible', extra), ('feasible_but_unreachable', missing)]:
        if states:
            result[key] = min(states, key=repr)
    return result


def transition_tables():
    """Compile the actual T1 moves, not a second browser implementation."""
    tables = {}
    for key, model in models().items():
        result = audit(model)
        if result['status'] != 'equal':
            raise ValueError(f'{key}: cannot export a failed audit: {result}')
        states = sorted(reachable(model.initial, model.moves), key=repr)
        index = {state: i for i, state in enumerate(states)}
        tables[key] = {'states': states, 'initial': index[model.initial],
                       'moves': [sorted(index[n] for n in model.moves(s)) for s in states],
                       'scope': model.scope, 'rung': result['rung'],
                       'locator': f'docs/foundations/AUDIT-MODELS.md:{key}'}
    return tables


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--all', action='store_true')
    group.add_argument('--device')
    args = parser.parse_args()
    registry = yaml.safe_load(REGISTRY.read_text())
    devices = {d['id']: d for d in registry['devices']}
    if args.device and args.device not in devices:
        parser.error('unknown device: ' + args.device)
    implemented = models()
    failed = False
    unevaluated = False
    for key in devices if args.all else [args.device]:
        if key in implemented:
            result = audit(implemented[key])
            failed |= result['status'] == 'failed'
        else:
            result = {'status': 'no_audit_possible' if key == 'D-009' else 'parameters_required',
                      'rung': devices[key]['rung'], 'reason': registry['audit_state_space'][key]}
            unevaluated = True
        result.update(device=key, locator=f'docs/foundations/devices.yaml:audit_state_space.{key}',
                      model_locator=f'docs/foundations/AUDIT-MODELS.md:{key}',
                      non_claims=[devices[key].get('cannot_show', devices[key].get('rung_reason', '')),
                                  'Digital model N2 only; no deployed interface or physical device verified.',
                                  'Self-assessment only; no independent audit, other criteria, or learner efficacy established.'])
        if key == 'D-007':
            result['non_claims'] += [
                'Atomic digital parity switching only; loose beads and emptying intermediates are not certified.',
                'The physical device excludes non-sighted learners; no equivalent path is verified.']
        if key == 'D-006':
            result['non_claims'].append(
                'Representative local Latin-cell constraints only; registry provides no concrete givens or global puzzle.')
        print(json.dumps(result, sort_keys=True))
    return 1 if failed else (2 if unevaluated and not args.all else 0)


if __name__ == '__main__':
    raise SystemExit(main())
