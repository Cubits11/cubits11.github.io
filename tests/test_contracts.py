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


if __name__ == '__main__':
    unittest.main()
