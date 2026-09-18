#!/usr/bin/env python3
"""Historical counterexamples and valid controls, not a prospective kill-rate study."""
import copy
import importlib.util
import itertools
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'research/contracts'
spec = importlib.util.spec_from_file_location('contract', BASE / 'validate_contract.py')
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


def fixture(name):
    return contract.load(BASE / 'fixtures' / (name + '.json'))


GROUP = {'width': 'identification', 'width_max': 'identification',
         'desired_ci_half_width': 'precision',
         'SESOI': 'decision', 'equivalence_margin': 'decision'}


def with_numbers(**changes):
    """The valid frozen contract with declared quantities replaced, one group at a time."""
    c = fixture('valid-frozen-inference')
    for key, value in changes.items():
        c['inference'][GROUP[key]][key] = value
    return c


class Contracts(unittest.TestCase):
    def test_valid_controls(self):
        for name in ('valid-guard-selection', 'valid-fixed-marginals'):
            self.assertEqual(contract.validate(fixture(name)), [])

    def test_historical_defects_rejected_for_relevant_reason(self):
        for name, reason in [('e7-threshold-direction', "'lowest' was expected"),
                             ('e6-marginal-failure', 'marginal mass changed'),
                             ('e7b-pool-mismatch', 'pool mismatch')]:
            self.assertTrue(any(reason in e for e in contract.validate(fixture(name))), name)

    def test_each_pool_mismatch_independently_rejected(self):
        bad = fixture('e7b-pool-mismatch')
        for role in ('calibration', 'evaluation'):
            c = fixture('valid-guard-selection')
            c['execution_plan'][role] = bad['execution_plan'][role]
            self.assertEqual(len(contract.validate(c)), 1)
            self.assertIn(role, contract.validate(c)[0])

    def test_alternative_matching_pool_is_not_universally_forbidden(self):
        c = fixture('e7b-pool-mismatch')
        c['declared_pools'] = copy.deepcopy(c['execution_plan'])
        self.assertEqual(contract.validate(c), [])

    def test_reverse_score_orientation(self):
        c = fixture('valid-guard-selection')
        c['operating_point'].update(comparator='le', direction='highest')
        self.assertEqual(contract.validate(c), [])
        c['operating_point']['direction'] = 'lowest'
        self.assertTrue(contract.validate(c))

    def test_actual_permutations_not_existence_of_some_valid_permutation(self):
        c = fixture('valid-fixed-marginals')
        accepted = []
        for p in itertools.permutations(range(3)):
            c['permutations'] = [list(p)]
            if not contract.validate(c):
                accepted.append(p)
        self.assertEqual(accepted, [(0, 1, 2), (2, 1, 0)])
        c['marginal_weights'] = [.5, .5]
        c['permutations'] = [[1, 0]]
        self.assertEqual(contract.validate(c), [])

    def test_bad_masses_indices_and_missing_choices(self):
        for key, value in [('marginal_weights', [.25, .5, .24]),
                           ('permutations', [[0, 0, 2]]), ('permutations', [[0, 1, 3]])]:
            c = fixture('valid-fixed-marginals'); c[key] = value
            self.assertTrue(contract.validate(c))
        c = fixture('valid-guard-selection')
        del c['operating_point']['no_feasible_candidate']
        self.assertTrue(contract.validate(c))
        c = fixture('valid-guard-selection'); c['silent_override'] = True
        self.assertTrue(contract.validate(c))

    def test_duplicate_keys_and_nonfinite_json_refuse(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'bad.json'
            for text in ('{"id":"first","id":"second"}', '{"budget":NaN}', '{"budget":Infinity}'):
                path.write_text(text)
                with self.assertRaises(ValueError): contract.load(path)


class InferentialAdequacy(unittest.TestCase):
    """C2's three quantities, each rejected on its own terms. Declared numbers only."""

    def only(self, c, reason):
        errors = contract.validate(c)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn(reason, errors[0])

    def test_valid_frozen_control(self):
        self.assertEqual(contract.validate(fixture('valid-frozen-inference')), [])

    def test_identification_limit_is_not_a_sample_size_problem(self):
        self.only(fixture('inference-identification-limited'), 'no sample size reduces')

    def test_admitted_width_wider_than_the_effect_it_would_act_on(self):
        self.only(with_numbers(width_max=.03), 'exceeds the SESOI')

    def test_precision_that_could_never_conclude_equivalence(self):
        self.only(with_numbers(SESOI=.05, desired_ci_half_width=.012), 'conclude equivalence')

    def test_margin_that_would_waive_an_effect_worth_acting_on(self):
        self.only(with_numbers(equivalence_margin=.03), 'would call equivalent')

    def test_minimum_information_is_not_implied_by_the_three_group_checks(self):
        # Every group passes alone; identification plus sampling still overruns the SESOI.
        self.only(with_numbers(desired_ci_half_width=.01, equivalence_margin=.012), 'minimum information')

    def test_boundary_admitted_under_exact_decimal_arithmetic(self):
        self.assertGreater(.1 + 2 * .1, .3)  # binary arithmetic would reject this design
        self.assertEqual(contract.validate(with_numbers(
            width=.1, width_max=.1, desired_ci_half_width=.1,
            equivalence_margin=.2, SESOI=.3)), [])

    def test_an_unimplemented_condition_fails_closed(self):
        c = with_numbers()
        c['inference']['minimum_information_condition'] = 'some_future_rule'
        self.assertTrue(any('no check implements' in e for e in contract.inference_errors(c)))
        self.assertTrue(contract.validate(c))  # today the schema refuses it first

    def test_the_gate_binds_to_frozen_status_in_both_kinds(self):
        c = with_numbers(); del c['inference']
        self.assertTrue(any('inference' in e for e in contract.validate(c)))
        c['status'] = 'draft'
        self.assertEqual(contract.validate(c), [])
        coupling = fixture('valid-fixed-marginals')
        self.assertEqual(contract.validate(coupling), [])
        coupling['status'] = 'frozen'
        self.assertTrue(any('inference' in e for e in contract.validate(coupling)))

    def test_informativeness_floor_must_reach_the_sesoi(self):
        # |q_obs - q_ind| never exceeds the marginal-only width, so a floor below the
        # SESOI admits a pool on which no actionable discrepancy can exist.
        c = with_numbers()
        c['inference']['informativeness'] = {'marginal_only_width_min': .02,
                                             'consequence_when_below': 'IDENTIFICATION-LIMITED'}
        self.assertEqual(contract.validate(c), [])
        c['inference']['informativeness']['marginal_only_width_min'] = .019
        self.only(c, 'below the SESOI')
        c['inference']['informativeness']['consequence_when_below'] = 'REPORT-ANYWAY'
        self.assertTrue(any('IDENTIFICATION-LIMITED' in e for e in contract.validate(c)))

    def test_historical_fixtures_are_not_retrofitted(self):
        for name in ('valid-guard-selection', 'valid-fixed-marginals', 'e6-marginal-failure',
                     'e7-threshold-direction', 'e7b-pool-mismatch'):
            c = fixture(name)
            self.assertEqual(c['status'], 'constructed_fixture', name)
            self.assertNotIn('inference', c, name)
            self.assertFalse([e for e in contract.validate(c) if 'inference' in e], name)


if __name__ == '__main__':
    unittest.main()
