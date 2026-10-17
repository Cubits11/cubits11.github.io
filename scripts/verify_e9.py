#!/usr/bin/env python3
"""Check E9-001 against committed rows and replay its frozen analyzer safely.

This is conditional numerical replay of owner-produced artifacts, not independent
replication, validity on other pools, or complete preregistration conformance.
The analyzer runs only in a temporary copy. No frozen experiment file is written.
Exit 0: agrees; 1: mismatch; 2: absent/malformed inputs (not a pass or refutation).
"""
from __future__ import annotations

import contextlib
import io
import json
import math
import shutil
import sys
import tempfile
import types
from fractions import Fraction
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TOL = 1e-12
GUARDS = ("G1", "G2")


class Mismatch(ValueError):
    """A registered or committed quantity does not follow its stored inputs."""


def require(condition: bool, label: str) -> None:
    if not condition:
        raise Mismatch(label)


def agrees(label: str, got, want) -> None:
    """Recursive comparison, with finite numeric tolerance and strict booleans."""
    if isinstance(want, bool) or isinstance(got, bool):
        require(type(got) is type(want) and got == want, f"{label}: {got!r} != {want!r}")
    elif isinstance(want, (int, float)) and isinstance(got, (int, float)):
        require(math.isfinite(got) and math.isfinite(want) and abs(got - want) <= TOL,
                f"{label}: {got!r} != {want!r} within {TOL}")
    elif isinstance(want, dict) and isinstance(got, dict):
        require(set(got) == set(want), f"{label}: object keys differ")
        for key in want:
            agrees(f"{label}.{key}", got[key], want[key])
    elif isinstance(want, list) and isinstance(got, list):
        require(len(got) == len(want), f"{label}: list lengths differ")
        for i, (actual, expected) in enumerate(zip(got, want)):
            agrees(f"{label}[{i}]", actual, expected)
    else:
        require(type(got) is type(want) and got == want, f"{label}: {got!r} != {want!r}")


def load_inputs(root: Path = ROOT) -> dict:
    e9 = root / "experiments/e9"
    claims = yaml.safe_load((root / "claims.yaml").read_text())["claims"]
    claim = next(c for c in claims if c["id"] == "E9-001")
    data = {"claim": claim}
    for key, name in (("contract", "contract.json"), ("freeze", "freeze/freeze.json"),
                      ("protocol", "freeze/protocol.json"), ("scores", "results/scores.json"),
                      ("result", "results/result.json"), ("analysis", "results/analysis.json")):
        data[key] = json.loads((e9 / name).read_text())
    data["rows"] = [json.loads(line) for line in (e9 / "results/observations.jsonl").read_text().splitlines()]
    data["prereg_text"] = (e9 / "PREREG.md").read_text()
    data["result_text"] = (e9 / "RESULT.md").read_text()
    data["analyzer_text"] = (e9 / "run/analyze.py").read_text()
    return data


def replay_analyzer(e9: Path = ROOT / "experiments/e9") -> dict:
    """Execute the committed analyzer after redirecting every experiment path."""
    with tempfile.TemporaryDirectory(prefix="verify-e9-") as temporary:
        copied = Path(temporary) / "experiments/e9"
        for name in ("contract.json", "freeze/freeze.json", "freeze/protocol.json",
                     "results/result.json", "results/observations.jsonl", "run/analyze.py"):
            target = copied / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(e9 / name, target)
        source = copied / "run/analyze.py"
        module = types.ModuleType("e9_analyzer_replay")
        module.__file__ = str(source)
        # compile/exec avoids importing bytecode into the frozen source directory.
        exec(compile(source.read_text(), str(source), "exec"), module.__dict__)
        module.E9 = copied
        module.RESULTS = copied / "results"
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                code = module.main()
            except (AssertionError, KeyError, ValueError, ZeroDivisionError) as exc:
                raise Mismatch(f"frozen analyzer refused temporary replay: {exc}") from exc
        require(code == 0, "frozen analyzer refused temporary replay (including admission thresholds)")
        return json.loads((module.RESULTS / "analysis.json").read_text())


def score(value, label: str) -> float:
    require(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1,
            f"{label}: score must be finite and within [0, 1]")
    return value


def derive(data: dict) -> dict:
    """Independent score/threshold/row arithmetic; never imports the runner."""
    contract, scores = data["contract"], data["scores"]
    require(scores["guards"] == list(GUARDS), "scores must declare exactly G1 and G2")
    op = contract["operating_point"]
    require(op["comparator"] == "ge" and op["direction"] == "lowest"
            and op["candidates"] == "observed_benign_scores"
            and op["objective"] == "maximum_sensitivity_under_fpr_budget"
            and op["no_feasible_candidate"] == "exclude_judge",
            "operating point differs from the frozen E9 rule")
    calibration = scores["pools"][contract["execution_plan"]["calibration"]]
    evaluation = scores["pools"][contract["execution_plan"]["evaluation"]]
    require(bool(calibration) and bool(evaluation), "calibration and measurement pools must be nonempty")
    require(not set(calibration).intersection(evaluation), "calibration and measurement item IDs overlap")
    for pool_name, pool in (("calibration", calibration), ("measurement", evaluation)):
        for item, vector in pool.items():
            require(isinstance(item, str) and bool(item) and set(vector) == set(GUARDS),
                    f"{pool_name} {item!r}: both guards required")
            for guard in GUARDS:
                score(vector[guard], f"{pool_name} {item}.{guard}")
    agrees("calibration item count", len(calibration), data["protocol"]["results"]["calibration_n"])
    budget = Fraction(str(op["fpr_budget"]))
    require(0 <= budget <= 1, "false-positive budget must lie in [0, 1]")
    thresholds = {}
    for guard in GUARDS:
        values = [v[guard] for v in calibration.values()]
        feasible = [t for t in sorted(set(values))
                    if Fraction(sum(v >= t for v in values), len(values)) <= budget]
        require(bool(feasible), f"{guard}: no feasible calibration threshold")
        thresholds[guard] = feasible[0]
    rows, seen = data["rows"], set()
    require(bool(rows), "measurement rows must be nonempty")
    counts = dict.fromkeys(GUARDS, 0)
    cells = {"00": 0, "01": 0, "10": 0, "11": 0}
    for i, row in enumerate(rows):
        item = row["item_id"]
        require(isinstance(item, str) and bool(item) and item not in seen,
                f"row {i}: duplicate or invalid measurement item ID {item!r}")
        seen.add(item)
        require(item in evaluation, f"row {i}: item absent from committed measurement scores")
        require(row["experiment"] == "E9" and row["contract_id"] == contract["id"]
                and row["pool"] == contract["execution_plan"]["evaluation"],
                f"row {i}: experiment, contract or pool differs")
        for kind in ("scores", "flag", "miss"):
            require(set(row[kind]) == set(GUARDS), f"row {i}: {kind} must contain exactly both guards")
        for guard in GUARDS:
            actual_score = score(row["scores"][guard], f"row {i}.{guard}")
            agrees(f"row {i}.{guard} committed score", actual_score, evaluation[item][guard])
            for kind in ("flag", "miss"):
                require(type(row[kind][guard]) is int and row[kind][guard] in (0, 1),
                        f"row {i}.{guard}: {kind} must be a binary integer")
            flag = int(actual_score >= thresholds[guard])
            require(row["flag"][guard] == flag and row["miss"][guard] == 1 - flag,
                    f"row {i}.{guard}: flag/miss does not follow frozen threshold")
            counts[guard] += row["miss"][guard]
        cells["".join(str(row["miss"][g]) for g in GUARDS)] += 1
    require(seen == set(evaluation), "measurement IDs do not match the committed score pool")
    n, both = len(rows), cells["11"]
    q_ind = Fraction(counts["G1"] * counts["G2"], n * n)
    q_obs = Fraction(both, n)
    lo, hi = max(0, sum(counts.values()) - n), min(counts.values())
    return {"n": n, "miss_counts": counts, "both": both, "cells": cells,
            "q_obs": float(q_obs), "q_ind": float(q_ind), "delta": float(q_obs - q_ind),
            "delta_exact": str(q_obs - q_ind), "band_counts": [lo, hi],
            "frechet": [lo / n, hi / n], "plug_in_count": str(q_ind * n),
            "width_exact": str(Fraction(hi - lo, n)), "thresholds": thresholds}


def verify(data: dict, replay: dict) -> dict:
    d = derive(data)
    claim, result, analysis = data["claim"], data["result"], data["analysis"]
    expected, admission = claim["expected"], data["protocol"]["results"]
    agrees("full frozen analyzer replay", replay, analysis)
    require(result["active_guards"] == result["guards"] == list(GUARDS)
            and result["excluded_guards"] == [], "result must retain both declared guards")
    agrees("result operating point", result["operating_point"], data["contract"]["operating_point"])
    for label, thresholds in (("measurement", result["thresholds"]), ("admission", admission["thresholds"]),
                              ("analysis", analysis["thresholds"]), ("registry", expected["thresholds"])):
        agrees(f"{label} thresholds", thresholds, d["thresholds"])
    ev = result["evaluation"]
    for key, derived_key in (("n", "n"), ("miss_counts", "miss_counts"), ("all_miss", "both"),
                             ("band_counts", "band_counts"), ("plug_in_all_miss_count", "plug_in_count"),
                             ("cells_derived_from_rows", "cells")):
        agrees(f"result evaluation.{key}", ev[key], d[derived_key])
    agrees("result discrepancy", result["identification"]["delta_all_miss"], d["delta_exact"])
    agrees("result marginal-only width", result["identification"]["marginal_only_width"], d["width_exact"])
    for key in ("q_obs", "q_ind", "delta", "delta_exact", "frechet", "n"):
        agrees(f"analysis.{key}", analysis[key], d[key])
    agrees("analysis miss rates", analysis["miss_rates"], {g: d["miss_counts"][g] / d["n"] for g in GUARDS})
    require(analysis["thresholds_equal_admission"] is True, "analysis must retain admission thresholds")
    require(analysis["guards"] == list(GUARDS), "analysis must retain both guards")
    for key, derived_key in (("observation_rows", "n"), ("miss_counts", "miss_counts"),
                             ("both_miss_count", "both"), ("q_obs", "q_obs"), ("q_ind", "q_ind"),
                             ("delta_exact", "delta_exact"), ("frechet", "frechet")):
        agrees(f"registry expected.{key}", expected[key], d[derived_key])
    for label, pool in (("registry", expected["admitted_pool"]), ("analysis", analysis["admitted_pool"])):
        agrees(f"{label} admitted pool", pool, admission["admitted"])
    agrees("registry bootstrap B", expected["bootstrap_B"], data["freeze"]["bootstrap"]["B"])
    agrees("analysis bootstrap B", analysis["bootstrap_B"], expected["bootstrap_B"])
    agrees("analysis seed", analysis["seed"], data["freeze"]["seed"])
    agrees("registry interval", expected["delta_ci95"], analysis["delta_ci95"])
    sesoi = data["contract"]["inference"]["decision"]["SESOI"]
    agrees("registry SESOI", expected["SESOI"], sesoi)
    low, high = analysis["delta_ci95"]
    require(low <= high, "confidence interval endpoints are reversed")
    excludes = low > 0 or high < 0
    wholly_beyond = low > sesoi or high < -sesoi
    agrees("analysis excludes zero", analysis["ci_excludes_zero"], excludes)
    agrees("registry excludes zero", expected["ci_excludes_zero"], excludes)
    agrees("registry interval wholly beyond SESOI", expected["ci_wholly_beyond_sesoi"], wholly_beyond)
    require(excludes and low < sesoi < high and not wholly_beyond,
            "retain limit: interval excludes zero but lower endpoint is below SESOI")
    require(analysis["verdict"].startswith("DISCREPANT:"), "recorded frozen-analyzer verdict differs")
    # These are envelope checks, not a machine judgment of preregistration quality.
    # The omission itself is part of this post-result claim and must stay visible.
    non_claims = [" ".join(s.lower().split()) for s in claim["non_claims"]]
    require(any("verdict rule" in s and "omitted" in s and "contract.json" in s
                and "c1 conformance is not established" in s for s in non_claims),
            "retain verdict-rule omission and unestablished C1 conformance")
    proposition = " ".join(claim["proposition"].lower().split())
    require("does not lie wholly beyond" in proposition and "effect-size threshold" in proposition,
            "registration must retain that the interval is not wholly beyond SESOI")
    require("does not certify complete preregistration conformance" in proposition,
            "registration must not certify complete preregistration conformance")
    require(claim["dimensions"]["evidential_status"] == "partially_supported",
            "registration must retain partial support")
    require("DISCREPANT" not in data["prereg_text"] and "verdict" not in data["contract"]["inference"]["decision"],
            "readable preregistration/contract changed to add the omitted verdict rule")
    require('elif out["ci_excludes_zero"] and out["point_at_or_beyond_sesoi"]:' in data["analyzer_text"],
            "frozen analyzer verdict rule differs")
    require("not rendered into `PREREG.md`" in data["result_text"] and "Correction C1" in data["result_text"],
            "frozen result must retain its verdict-rule omission disclosure")
    return {"rows": d["n"], "miss_counts": d["miss_counts"], "both_miss_count": d["both"],
            "q_obs": d["q_obs"], "q_ind": d["q_ind"], "delta": d["delta"],
            "ci95": [low, high], "ci_excludes_zero": excludes,
            "ci_wholly_beyond_sesoi": wholly_beyond, "rule_omission_retained": True}


def main() -> int:
    try:
        data = load_inputs()
        # Reject invalid rows before spending time on the 2,000 bootstrap draws.
        derive(data)
        report = verify(data, replay_analyzer())
    except Mismatch as exc:
        print(f"E9 FAIL: {exc}")
        return 1
    except (OSError, json.JSONDecodeError, yaml.YAMLError, KeyError, TypeError, StopIteration, ValueError) as exc:
        print(f"E9 EXIT 2: absent or malformed input: {exc}")
        print("Not a pass and not a refutation.")
        return 2
    print("E9-001 conditional numerical replay passed at tolerance 1e-12:")
    print(json.dumps(report, sort_keys=True))
    print("Replay is not independent replication or validity on other pools. The readable verdict-rule omission remains.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
