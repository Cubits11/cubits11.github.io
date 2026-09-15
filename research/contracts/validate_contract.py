#!/usr/bin/env python3
"""Validate declared contracts; never execute or retrofit historical experiments."""
import argparse
from fractions import Fraction
import json
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA = Path(__file__).with_name('schema.json')


def validate(contract):
    schema = json.loads(SCHEMA.read_text())
    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema).iter_errors(contract))
    if errors:
        # Include branch diagnostics: the oneOf summary alone hides the cause.
        def leaves(error):
            return [s for child in error.context for s in leaves(child)] if error.context else [error.message]
        return ['schema: ' + message for error in errors for message in leaves(error)]
    if contract['kind'] == 'guard_selection':
        return [f'pool mismatch: {role}: declared {contract["declared_pools"][role]}, '
                f'planned {contract["execution_plan"][role]}'
                for role in ('calibration', 'evaluation')
                if contract['declared_pools'][role] != contract['execution_plan'][role]]
    # Exact decimal arithmetic: do not let a tolerance silently admit changed mass.
    weights = [Fraction(str(w)) for w in contract['marginal_weights']]
    bad = []
    if sum(weights) != 1:
        bad.append('marginal weights must sum exactly to one')
    for perm in contract['permutations']:
        if sorted(perm) != list(range(len(weights))):
            bad.append(f'not a permutation of the atom indices: {perm}')
            continue
        moved = [sum((weights[i] for i, j in enumerate(perm) if j == k), Fraction(0))
                 for k in range(len(weights))]
        if moved != weights:
            bad.append(f'marginal mass changed under permutation {perm}')
    return bad


def load(path):
    def reject_constant(value):
        raise ValueError(f'non-finite JSON number: {value}')
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError(f'duplicate JSON key: {key}')
            out[key] = value
        return out
    return json.loads(Path(path).read_text(), parse_constant=reject_constant, object_pairs_hook=unique)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('contract', type=Path)
    args = parser.parse_args()
    try:
        errors = validate(load(args.contract))
    except (ValueError, OSError) as exc:
        errors = [str(exc)]
    for error in errors:
        print('REJECT:', error)
    if not errors:
        print('PASS: declared contract is internally consistent; execution conformance is not established')
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
