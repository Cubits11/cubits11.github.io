"""Canonical E2 configuration integrity; no statistical or threshold changes.

Digest scheme: SHA-256 of UTF-8 JSON, sorted keys, compact separators,
ensure_ascii=False, with config_hash set to the empty string. The separate
freeze record is created once by make_config.py and retained with the config.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
FROZEN_ANALYSIS = json.loads((HERE / "analysis_config.json").read_text())


class ConfigError(ValueError):
    pass


def config_digest(cfg: dict) -> str:
    canonical = json.dumps(dict(cfg, config_hash=""), sort_keys=True,
                           separators=(",", ":"), ensure_ascii=False,
                           allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def synthetic_config(thresholds: dict | None = None) -> dict:
    cfg = {"mode": "SYNTHETIC", "analysis": dict(FROZEN_ANALYSIS),
           "results": {g: {"threshold": t} for g, t in
                       (thresholds or {"lg4": .95, "lg3": .95, "sg2b": .95}).items()}}
    cfg["config_hash"] = config_digest(cfg)
    return cfg


def load_config(path: str | Path, freeze_record: str | Path | None = None) -> dict:
    try:
        path = Path(path)
        cfg = json.loads(path.read_text())
        digest = config_digest(cfg)
        if cfg.get("config_hash") != digest:
            raise ConfigError("configuration_hash_mismatch")
        if cfg.get("analysis") != FROZEN_ANALYSIS:
            raise ConfigError("analysis_configuration_differs_from_preregistration")
        record = json.loads(Path(freeze_record or path.with_name(
            "e2_config.freeze.json")).read_text())
        if record.get("config_hash") != digest:
            raise ConfigError("freeze_record_hash_mismatch")
        for guard in ("lg4", "lg3", "sg2b"):
            value = cfg["results"][guard]["threshold"]
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ConfigError("invalid_threshold")
        return cfg
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ConfigError(str(exc)) from exc
