#!/usr/bin/env python3
"""Independent recomputation of T1 — the BELLS-11 selection-regret table —
from the raw released rows, outside the analyzer's reporting path.

Different code, same definitions (ARTIFACTS/12-WEEK-PROGRAM.md §7):
per-system bitmasks over the harmful and benign rows; union = popcount of
the OR; M(A) = highest marginal catch (tie: fewer benign flags, then earlier
column); J(A) = highest union with A (tie: lower benign union, then earlier
column); R(A) = U(A,J) − U(A,M) in items. Standard library only.

    python3 independent_t1.py --csv non_adversarial_prompts.csv \
        [--compare bells11.json]

Exit 0 only if the file hash is the pinned one and, with --compare, every
pick, union and regret equals the analyzer's output exactly.
"""
import argparse
import csv
import hashlib
import json
import sys

PINNED_SHA256 = "791dd4b0a168f2eb5831b308083a492e83200a9fa82585643c739023b03f57c3"
META = {"question", "harm_level", "source", "category"}
SPECIALIZED = ["lakera_guard", "prompt_guard", "langkit", "nemo", "llm_guard"]


def masks(rows: list, systems: list, level: str) -> dict:
    out = {s: 0 for s in systems}
    for idx, r in enumerate(x for x in rows if x["harm_level"] == level):
        for s in systems:
            if r[s].strip() == "1":
                out[s] |= 1 << idx
    return out


def regret_table(systems: list, H: dict, Bn: dict, n: int) -> list:
    pc = int.bit_count
    table = []
    for a in systems:
        cands = [b for b in systems if b != a]
        m = min(cands, key=lambda b: (-pc(H[b]), pc(Bn[b]), cands.index(b)))
        j = min(cands, key=lambda b: (-pc(H[a] | H[b]), pc(Bn[a] | Bn[b]), cands.index(b)))
        um, uj = pc(H[a] | H[m]), pc(H[a] | H[j])
        table.append({"incumbent": a, "marginal_choice": m, "joint_choice": j,
                      "flip": m != j, "regret_items": uj - um,
                      "regret_points": (uj - um) / n, "U_marg": um, "U_joint": uj,
                      "benign_union_marg": pc(Bn[a] | Bn[m]),
                      "benign_union_joint": pc(Bn[a] | Bn[j]), "n": n})
    return table


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--compare")
    args = ap.parse_args()
    raw = open(args.csv, "rb").read()
    got = hashlib.sha256(raw).hexdigest()
    if got != PINNED_SHA256:
        print(f"FAIL  sha256 {got[:16]}… is not the pinned BELLS file")
        return 1
    rows = list(csv.DictReader(raw.decode("utf-8").splitlines()))
    systems = [c for c in rows[0] if c not in META]
    n = sum(r["harm_level"] == "harmful" for r in rows)
    H, Bn = masks(rows, systems, "harmful"), masks(rows, systems, "benign")
    results = {"harmful[all11]": regret_table(systems, H, Bn, n),
               "harmful[specialized5]": regret_table(SPECIALIZED, H, Bn, n)}
    for label, table in results.items():
        print(f"\n{label} (n={n}) — independent recomputation")
        print("incumbent | marginal_choice | joint_choice | flip | regret | U_marg | U_joint")
        for r in table:
            print(f"{r['incumbent']} | {r['marginal_choice']} | {r['joint_choice']} | "
                  f"{r['flip']} | {r['regret_items']} | {r['U_marg']} | {r['U_joint']}")
    if args.compare:
        rep = json.load(open(args.compare))
        keys = ("marginal_choice", "joint_choice", "flip", "regret_items",
                "U_marg", "U_joint", "benign_union_marg", "benign_union_joint", "n")
        for t in rep["tables"]:
            mine = {r["incumbent"]: r for r in results[t["stratum"]]}
            for r in t["incumbents"]:
                for k in keys:
                    if mine[r["incumbent"]][k] != r[k]:
                        print(f"FAIL  {t['stratum']} {r['incumbent']} {k}: "
                              f"independent {mine[r['incumbent']][k]} vs analyzer {r[k]}")
                        return 1
                if abs(mine[r["incumbent"]]["regret_points"] - r["regret_points"]) > 1e-12:
                    print("FAIL  regret_points differs beyond 1e-12")
                    return 1
        print("\nok    independent T1 recomputation agrees with the analyzer on every "
              "pick, union, regret and benign union (exact; points to 1e-12)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
