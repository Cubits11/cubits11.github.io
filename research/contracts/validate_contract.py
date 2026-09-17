#!/usr/bin/env python3
"""Validate declared contracts; never execute or retrofit historical experiments."""
import argparse
from decimal import Decimal
from fractions import Fraction
import json
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA = Path(__file__).with_name('schema.json')


def inference_errors(contract):
    """Correction C2, asked as three separate questions instead of one power number."""
    inference = contract.get('inference')
    if inference is None:
        return []
    # Decimal, not float: 0.1 + 2 * 0.1 exceeds 0.3 in binary arithmetic, and a rounding
    # artifact must not decide whether a design can answer its own question.
    width, width_max = (Decimal(str(inference['identification'][key])) for key in ('width', 'width_max'))
    half = Decimal(str(inference['precision']['desired_ci_half_width']))
    sesoi = Decimal(str(inference['decision']['SESOI']))
    margin = Decimal(str(inference['decision']['equivalence_margin']))
    bad = []
    if width > width_max:
        bad.append(f'identification: declared width {width} exceeds the {width_max} this target admits, '
                   f'and no sample size reduces an identification width')
    if width_max > sesoi:
        bad.append(f'identification: the admitted width {width_max} exceeds the SESOI {sesoi}, so a design '
                   f'meeting its own identification bound still could not separate the smallest effect it '
                   f'would act on')
    if half >= margin:
        bad.append(f'precision: an interval half width of {half} is not smaller than the equivalence margin '
                   f'{margin}, so no observed value could conclude equivalence')
    if margin > sesoi:
        bad.append(f'decision: the equivalence margin {margin} exceeds the SESOI {sesoi}, so it would call '
                   f'equivalent a difference this contract says it would act on')
    condition = inference['minimum_information_condition']
    if condition != 'identification_width_plus_sampling_within_sesoi':
        bad.append(f'minimum information: no check implements {condition}')
    elif width + 2 * half > sesoi:
        # The boundary is admitted: a design that exactly meets its declared condition passes.
        bad.append(f'minimum information: identification {width} plus sampling {2 * half} = {width + 2 * half} '
                   f'exceeds the SESOI {sesoi}')
    return bad


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
                if contract['declared_pools'][role] != contract['execution_plan'][role]
                ] + inference_errors(contract)
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
    return bad + inference_errors(contract)


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
    contract = {}
    try:
        contract = load(args.contract)
        errors = validate(contract)
    except (ValueError, OSError) as exc:
        errors = [str(exc)]
    for error in errors:
        print('REJECT:', error)
    if not errors:
        print('PASS: declared contract is internally consistent; execution conformance is not established')
        if 'inference' in contract:
            print('NOTE  the inference block was compared with itself: no check here establishes that the '
                  'declared identification width is the width this design actually has')
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
