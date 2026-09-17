#!/usr/bin/env python3
"""Re-assert E3 and E3B from their committed observation rows.

These are the first measurements this repository produced, so the registry
entries that carry them (E3-001, E3B-001) must be re-derivable without the
models, without the network, and without the analyzer that produced them.

This script recomputes every registered quantity from
``experiments/<e>/results/observations.jsonl`` alone — the per-item, per-guard
flag and miss bits, 2,400 rows each — and asserts them against three places
that must agree:

  1. the run's own ``results/e3_result.json``
  2. the claim's ``expected`` block in ``claims.yaml``
  3. this recomputation

The bootstrap CI is re-derived, not copied: ``run/analyze.py`` seeds
``random.Random`` from the frozen seed string, so the interval is a
deterministic function of the committed rows and reproduces exactly here from
a clean clone. A drifting row, a re-thresholded flag, or an edited result file
fails.

What this does NOT do: it does not re-score any item, re-download any pool, or
load any model. It proves the registered numbers follow from the committed
rows. It does not prove the rows measure what the programme says they measure —
both RESULT.md files say so in their own non-claims, and so do the claims.

    python3 scripts/verify_e3.py            # the gate (exit 0 / 1)
    python3 scripts/verify_e3.py --show     # print the recomputed table
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
B = 2000
TOL = 1e-12

# experiment directory -> claim id in claims.yaml
BOUND: tuple[tuple[str, str], ...] = (
    ("e3", "E3-001"),
    ("e3b", "E3B-001"),
)

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL  {msg}")


def ok(msg: str) -> None:
    print(f"ok    {msg}")


def load_rows(exp: str) -> list[dict]:
    path = ROOT / "experiments" / exp / "results" / "observations.jsonl"
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def indicators(rows: list[dict], stratum: str, field: str) -> dict[str, dict[str, int]]:
    """{guard: {item_id: 0|1}} for one stratum, from one committed bit column."""
    out: dict[str, dict[str, int]] = {}
    for r in rows:
        if r["stratum"] != stratum:
            continue
        value = r[field]
        if value is None:
            raise ValueError(f"{stratum}/{r['guard']}/{r['item_id']}: {field} is null")
        out.setdefault(r["guard"], {})[r["item_id"]] = int(value)
    return out


def frechet(p1: float, p2: float) -> list[float]:
    return [max(0.0, p1 + p2 - 1.0), min(p1, p2)]


def stats(ind: dict[str, dict[str, int]], ids: list[str]) -> dict:
    a = [ind["G1"][i] for i in ids]
    b = [ind["G2"][i] for i in ids]
    n = len(ids)
    p1, p2 = sum(a) / n, sum(b) / n
    q_obs = sum(x and y for x, y in zip(a, b)) / n
    q_ind = p1 * p2
    lo, hi = frechet(p1, p2)
    return {
        "n": n, "p_miss_G1": p1, "p_miss_G2": p2, "q_obs": q_obs, "q_ind": q_ind,
        "delta": q_obs - q_ind, "frechet": [lo, hi],
        "inside_frechet": lo - 1e-12 <= q_obs <= hi + 1e-12,
    }


def bootstrap_ci(ind: dict[str, dict[str, int]], ids: list[str], seed: str) -> list[float]:
    """Byte-for-byte the analyzer's procedure: same seed derivation, same draws."""
    rng = random.Random(int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16))
    deltas = []
    for _ in range(B):
        samp = [ids[rng.randrange(len(ids))] for _ in ids]
        deltas.append(stats(ind, samp)["delta"])
    deltas.sort()
    return [deltas[int(0.025 * B)], deltas[int(0.975 * B) - 1]]


def close(a: float, b: float, tol: float = TOL) -> bool:
    return abs(float(a) - float(b)) <= tol


def compare(where: str, got: dict, want: dict, keys: tuple[str, ...]) -> None:
    for k in keys:
        if k not in want:
            fail(f"{where}: {k} absent from the recorded block")
            continue
        g, w = got[k], want[k]
        if isinstance(g, bool) or isinstance(w, bool):
            if bool(g) != bool(w):
                fail(f"{where}.{k}: recomputed {g}, recorded {w}")
        elif isinstance(g, list):
            if len(g) != len(w) or not all(close(x, y) for x, y in zip(g, w)):
                fail(f"{where}.{k}: recomputed {g}, recorded {w}")
        elif not close(g, w):
            fail(f"{where}.{k}: recomputed {g!r}, recorded {w!r}")


POINT_KEYS = ("n", "p_miss_G1", "p_miss_G2", "q_obs", "q_ind", "delta",
              "frechet", "inside_frechet")


def check(exp: str, claim_id: str, registry: dict, show: bool) -> None:
    rows = load_rows(exp)
    if len(rows) != 2400:
        fail(f"{exp}: expected 2400 committed observation rows, found {len(rows)}")
        return

    result_path = ROOT / "experiments" / exp / "results" / "e3_result.json"
    recorded = json.loads(result_path.read_text(encoding="utf-8"))
    seed = recorded["seed"]

    # harmful stratum: the joint MISS event
    miss = indicators(rows, "harmful", "miss")
    hids = sorted(miss["G1"])
    harmful = stats(miss, hids)
    ci = bootstrap_ci(miss, hids, seed)
    ci_excludes_zero = ci[0] > 0 or ci[1] < 0

    # benign evaluation stratum: the joint FLAG event (the analyzer's key names
    # say "miss"; the quantity is the flag rate, and the registry says so)
    flag = indicators(rows, "benign_evaluation", "flag")
    bids = sorted(flag["G1"])
    benign = stats(flag, bids)

    if show:
        print(f"\n--- {exp} ({claim_id}) recomputed from {len(rows)} committed rows")
        for k in POINT_KEYS:
            print(f"    harmful.{k:<16} {harmful[k]}")
        print(f"    delta_ci95            {ci}")
        print(f"    ci_excludes_zero      {ci_excludes_zero}")
        for k in POINT_KEYS:
            print(f"    benign.{k:<17} {benign[k]}")

    # 1 — against the run's own result file
    compare(f"{exp} run harmful", harmful, recorded["harmful"], POINT_KEYS)
    compare(f"{exp} run benign", benign, recorded["benign_evaluation_joint_flag"], POINT_KEYS)
    if len(ci) != len(recorded["delta_ci95"]) or not all(
        close(x, y) for x, y in zip(ci, recorded["delta_ci95"])
    ):
        fail(f"{exp} run delta_ci95: recomputed {ci}, recorded {recorded['delta_ci95']}")
    if bool(ci_excludes_zero) != bool(recorded["ci_excludes_zero"]):
        fail(f"{exp} run ci_excludes_zero: recomputed {ci_excludes_zero}, "
             f"recorded {recorded['ci_excludes_zero']}")
    if recorded["bootstrap_B"] != B:
        fail(f"{exp}: bootstrap B recorded {recorded['bootstrap_B']}, this check uses {B}")

    # 2 — against the registry
    claim = registry.get(claim_id)
    if claim is None:
        fail(f"{claim_id}: not present in claims.yaml — the rows have no registry home")
        return
    expected = claim.get("expected") or {}
    compare(f"{claim_id} harmful", harmful, expected.get("harmful", {}), POINT_KEYS)
    compare(f"{claim_id} benign", benign, expected.get("benign_evaluation_joint_flag", {}),
            POINT_KEYS)
    reg_ci = expected.get("delta_ci95")
    if reg_ci is None:
        fail(f"{claim_id}: expected.delta_ci95 absent")
    elif not all(close(x, y) for x, y in zip(ci, reg_ci)):
        fail(f"{claim_id}.delta_ci95: recomputed {ci}, registered {reg_ci}")
    if bool(expected.get("ci_excludes_zero")) != bool(ci_excludes_zero):
        fail(f"{claim_id}.ci_excludes_zero: recomputed {ci_excludes_zero}, "
             f"registered {expected.get('ci_excludes_zero')}")
    if expected.get("observation_rows") != len(rows):
        fail(f"{claim_id}.observation_rows: counted {len(rows)}, "
             f"registered {expected.get('observation_rows')}")

    # 3 — the failed predictions must still be recorded as failures
    verdicts = expected.get("prediction_verdicts") or {}
    if not verdicts:
        fail(f"{claim_id}: expected.prediction_verdicts absent — a pilot whose primary "
             f"prediction failed must carry the verdict in the registry")
    result_md = (ROOT / "experiments" / exp / "RESULT.md").read_text(encoding="utf-8")
    for pid, verdict in verdicts.items():
        if verdict.upper() not in {"FAILED", "HELD", "NOT_COMPUTED"}:
            fail(f"{claim_id}: prediction {pid} has an unrecognised verdict {verdict!r}")
        if verdict.upper() == "FAILED" and "FAILED" not in result_md:
            fail(f"{claim_id}: prediction {pid} is registered FAILED but "
                 f"experiments/{exp}/RESULT.md records no failure")

    ok(f"{claim_id}: {len(rows)} committed rows reproduce every registered quantity "
       f"(delta {harmful['delta']:+.6f}, CI [{ci[0]:+.6f}, {ci[1]:+.6f}], "
       f"Frechet width {harmful['frechet'][1] - harmful['frechet'][0]:.4f})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--show", action="store_true",
                    help="print the recomputed table before asserting")
    args = ap.parse_args()

    registry = {
        c["id"]: c
        for c in yaml.safe_load((ROOT / "claims.yaml").read_text(encoding="utf-8"))["claims"]
    }
    for exp, claim_id in BOUND:
        check(exp, claim_id, registry, args.show)

    if failures:
        print(f"\n{len(failures)} check(s) failed. The committed rows and the registered "
              f"numbers do not agree; neither is corrected here.")
        return 1
    print("\nE3 and E3B re-asserted from committed rows. Both pilots' primary predictions "
          "failed and are registered as failed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
