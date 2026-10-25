"""Validate at the governing CONTRACT boundary before a JSONL write.

E2_CONTRACT_ROOT selects the paired CONTRACT checkout; schema authority stays
there rather than being copied into SITE. Analysis remains stdlib-only.
"""
from functools import lru_cache
import importlib.util
import json
import os
from pathlib import Path


class RowValidationError(ValueError):
    pass


@lru_cache(maxsize=None)
def _contract(root):
    root = Path(root)
    schema = json.loads((root / "schemas/cc.e2_observation_row.v1.json").read_text())
    spec = importlib.util.spec_from_file_location(
        "e2_contract_validator", root / "scripts/validate_e2_observations.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, schema


def validate_row(row):
    default = Path(__file__).resolve().parents[4] / "cc-framework"
    root = os.environ.get("E2_CONTRACT_ROOT", str(default))
    try:
        module, schema = _contract(root)
        violations = module.schema_violations([row], schema)
    except (OSError, ImportError, ValueError) as exc:
        violations = [f"governing schema unavailable: {exc}"]
    if violations:
        raise RowValidationError(json.dumps({"error": "row_conformance", "violations": violations}))
