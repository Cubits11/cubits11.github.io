#!/usr/bin/env python3
"""E3 analysis. Estimands are PREREG.md's, unchanged.

q_obs = P(M1 and M2)   both guards miss a harmful item
q_ind = P(M1) P(M2)    the independence plug-in
delta = q_obs - q_ind  excess joint miss
Frechet interval on the joint miss from the two marginals, and a
95% bootstrap CI on delta, B = 2000, seed as frozen.

Prediction 2 is a stop condition, not a diagnostic: if q_obs falls outside the
Frechet interval the instrument is wrong, not the world, and collection stops.
"""
from __future__ import annotations
import json, hashlib, random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RES = ROOT / "experiments/e3/results"
B = 2000


def flags(setname: str, cfg: dict) -> dict[str, dict[str, int]]:
    d = json.loads((RES / f"{setname}.probs.json").read_text())
    out = {}
    for slot, probs in d["guards"].items():
        t = cfg["guards"][slot]["threshold"]
        out[slot] = {k: int(v >= t) for k, v in probs.items()}
    return out


def frechet(p1: float, p2: float) -> tuple[float, float]:
    return max(0.0, p1 + p2 - 1.0), min(p1, p2)


def stats(miss: dict[str, dict[str, int]], ids: list[str]) -> dict:
    m1 = [miss["G1"][i] for i in ids]
    m2 = [miss["G2"][i] for i in ids]
    n = len(ids)
    p1, p2 = sum(m1) / n, sum(m2) / n
    q_obs = sum(a and b for a, b in zip(m1, m2)) / n
    q_ind = p1 * p2
    lo, hi = frechet(p1, p2)
    return {"n": n, "p_miss_G1": p1, "p_miss_G2": p2, "q_obs": q_obs,
            "q_ind": q_ind, "delta": q_obs - q_ind,
            "frechet": [lo, hi], "inside_frechet": lo - 1e-12 <= q_obs <= hi + 1e-12}


def main() -> int:
    cfg = json.loads((ROOT / "experiments/e3/e3_config.json").read_text())
    harm = flags("items_harmful", cfg)
    ids = sorted(harm["G1"])
    # miss on harmful = NOT flagged
    miss = {g: {i: 1 - v for i, v in d.items()} for g, d in harm.items()}
    s = stats(miss, ids)

    rng = random.Random(int(hashlib.sha256(cfg["seed"].encode()).hexdigest()[:8], 16))
    deltas = []
    for _ in range(B):
        samp = [ids[rng.randrange(len(ids))] for _ in ids]
        deltas.append(stats(miss, samp)["delta"])
    deltas.sort()
    ci = [deltas[int(.025 * B)], deltas[int(.975 * B) - 1]]

    # benign: joint FLAG rate on the held-out evaluation stratum
    ben = flags("items_benign_evaluation", cfg)
    bids = sorted(ben["G1"])
    bs = stats(ben, bids)

    out = {"harmful": s, "delta_ci95": ci, "ci_excludes_zero": ci[0] > 0 or ci[1] < 0,
           "benign_evaluation_joint_flag": bs, "bootstrap_B": B, "seed": cfg["seed"],
           "config_sha256": hashlib.sha256((ROOT / "experiments/e3/e3_config.json").read_bytes()).hexdigest()}
    (RES / "e3_result.json").write_text(json.dumps(out, indent=1))

    print(f"HARMFUL n={s['n']}")
    print(f"  miss rate  G1 {s['p_miss_G1']:.4f}   G2 {s['p_miss_G2']:.4f}")
    print(f"  q_obs      {s['q_obs']:.4f}")
    print(f"  q_ind      {s['q_ind']:.4f}   (independence plug-in)")
    print(f"  delta      {s['delta']:+.4f}   95% CI [{ci[0]:+.4f}, {ci[1]:+.4f}]")
    print(f"  Frechet    [{s['frechet'][0]:.4f}, {s['frechet'][1]:.4f}]   q_obs inside: {s['inside_frechet']}")
    print(f"  CI excludes zero: {out['ci_excludes_zero']}")
    if not s["inside_frechet"]:
        print("  KILL: q_obs outside the Frechet interval. The instrument is wrong, not the world.")
        return 1
    print(f"BENIGN EVALUATION n={bs['n']}  joint flag {bs['q_obs']:.4f}  plug-in {bs['q_ind']:.4f}  delta {bs['delta']:+.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
