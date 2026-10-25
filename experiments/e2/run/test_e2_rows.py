#!/usr/bin/env python3
"""E2 governing-schema emission regressions; fixtures never load a model."""
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
CONTRACT = Path(os.environ.get("E2_CONTRACT_ROOT", HERE.parents[3] / "e2-wave1-contract"))
os.environ["E2_CONTRACT_ROOT"] = str(CONTRACT)
spec = importlib.util.spec_from_file_location("e2_validator", CONTRACT / "scripts/validate_e2_observations.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
import collect


class RowEmissionTest(unittest.TestCase):
    def emit(self, **updates):
        params = dict(run_id="SYNTHETIC-fixture", item={"id": "a", "stratum": "harmful"},
                      guard="lg3", replicate=1, score=.99, threshold=.5,
                      status="observed", code="observed", synthetic=True)
        params.update(updates)
        buf = io.StringIO()
        collect.emit_row(buf, **params)
        return json.loads(buf.getvalue())

    def test_observed_and_missing_rows_conform(self):
        schema = json.loads((CONTRACT / "schemas/cc.e2_observation_row.v1.json").read_text())
        rows = [self.emit(), self.emit(item={"id": "b", "stratum": "benign_eval"}),
                self.emit(score=None, status="failed", code="timeout")]
        violations = validator.schema_violations(rows, schema)
        print("E2 schema violations:", len(violations), json.dumps(violations))
        self.assertEqual(violations, [])

    def test_invalid_row_never_written(self):
        buf = io.StringIO()
        with self.assertRaises(ValueError) as caught:
            collect.emit_row(buf, run_id="t", item={"id": "a", "stratum": "invalid"},
                             guard="lg3", replicate=[], score=.4, threshold=.5,
                             status="observed", code="observed", synthetic=True)
        self.assertIn("violations", str(caught.exception))
        self.assertEqual(buf.getvalue(), "")

    def test_adapter_hashes_rendered_bytes_and_unrounded_score(self):
        import adapters
        import hashlib
        score = .1234567890123456
        rendered = "rendered policy/template: \u03b1\n"
        self.assertEqual(adapters._record_score("lg3", rendered, score), score)
        record = adapters.OBSERVATIONS["lg3"]
        self.assertEqual(record["raw_input_hash"], hashlib.sha256(rendered.encode()).hexdigest())
        self.assertEqual(record["raw_output_hash"], hashlib.sha256(json.dumps(score).encode()).hexdigest())

    def test_original_ft11_calls_emit_no_invalid_rows(self):
        # Exact archived FT11 parameters. The original real call omits provenance
        # and the checked config, so it must now refuse before writing.
        schema = json.loads((CONTRACT / "schemas/cc.e2_observation_row.v1.json").read_text())
        item_id = (HERE.parent / "freeze/items_harmful.csv").read_text().splitlines()[1].split(",")[0]
        row = self.emit(run_id="ft11", item={"id": item_id, "stratum": "harmful"},
                        guard="FX1", replicate=0, score=.25, status="success")
        self.assertEqual(validator.schema_violations([row], schema), [])
        buf = io.StringIO()
        with self.assertRaises(ValueError) as caught:
            collect.emit_row(buf, run_id="ft11", item={"id": item_id, "stratum": "harmful"},
                             guard="FX2", replicate=0, score=.25, threshold=.5,
                             status="success", code="observed", synthetic=False)
        self.assertIn("violations", str(caught.exception))
        self.assertEqual(buf.getvalue(), "")
        print("FT11: emitted valid synthetic row=1, invalid real call refused=1, violations=0")

    def test_schema_valid_rows_load_in_analyzer(self):
        import analyze
        rows = [self.emit(guard=g) for g in collect.GUARDS]
        schema = json.loads((CONTRACT / "schemas/cc.e2_observation_row.v1.json").read_text())
        self.assertEqual(validator.schema_violations(rows, schema), [])
        self.assertEqual(validator.design_violations(rows), [])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"rows.jsonl"
            path.write_text("\n".join(json.dumps(r) for r in rows))
            events, missing, synthetic = analyze.load(path)
        self.assertTrue(synthetic)
        self.assertEqual(len(events["harmful"]["a"]), 3)


if __name__ == "__main__":
    unittest.main()
