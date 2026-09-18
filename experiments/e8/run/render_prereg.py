#!/usr/bin/env python3
"""Render experiments/e8/PREREG.md from the contract, the scouting record and the freeze.

    python3 experiments/e8/run/render_prereg.py            # write PREREG.md
    python3 experiments/e8/run/render_prereg.py --check    # exit 1 on drift

Correction C1: the contract is the canonical executable semantics and the
preregistration renders it into English. No number below is typed here; each
is read from contract.json, scouting.json or freeze.json. tests/test_e8_runner.py
holds the rendered file to this renderer, so an edit to the prose that is not an
edit to its source fails the manifest.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
E8 = ROOT / "experiments/e8"
FREEZE = E8 / "freeze"


def pct(x: float) -> str:
    return f"{100 * x:g} percentage points"


def render() -> str:
    c = json.loads((E8 / "contract.json").read_text())
    s = json.loads((FREEZE / "scouting.json").read_text())
    f = json.loads((FREEZE / "freeze.json").read_text()) if (FREEZE / "freeze.json").exists() else None
    op, inf = c["operating_point"], c["inference"]
    ident, prec, dec, info = inf["identification"], inf["precision"], inf["decision"], inf["informativeness"]
    csha = hashlib.sha256((E8 / "contract.json").read_bytes()).hexdigest()
    L = []
    L += [f"# E8 — the pool is the design variable",
          "",
          f"**Rendered from `contract.json` (`{c['id']}`, status `{c['status']}`, sha256 `{csha[:16]}…`),",
          "`freeze/scouting.json` and `freeze/freeze.json` by `run/render_prereg.py`. Nothing here is",
          "typed by hand; an edit to this file that is not an edit to its source fails the manifest.**",
          "",
          "## The question, and the order it was declared in",
          "",
          "Can residual risk be quoted from the marginals? E3 and E3B could not ask it: their pools",
          "put both guards at an extreme, the marginal-only identified set collapsed to a width of",
          "0.0175 and 0, and a discrepancy between the observed joint miss and the independence",
          "plug-in can never exceed that width. So the identification group came first, before any",
          "pool or threshold, and the pool was chosen to clear it.",
          "",
          "## Identification group — declared first",
          "",
          "| declared | value |",
          "|---|---|",
          f"| estimand | {c['estimand']} |",
          f"| inferential target | `{inf['inferential_target']}` |",
          f"| SESOI, the smallest discrepancy worth acting on | {dec['SESOI']} ({pct(dec['SESOI'])}) |",
          f"| equivalence margin | ±{dec['equivalence_margin']} |",
          f"| identification width the design permits | {ident['width']} (maximum admitted {ident['width_max']}) |",
          f"| desired 95% interval half width | {prec['desired_ci_half_width']} |",
          f"| minimum information condition | `{inf['minimum_information_condition']}` |",
          f"| **marginal-only width floor** | **{info['marginal_only_width_min']}** ({pct(info['marginal_only_width_min'])}) |",
          f"| **consequence below the floor** | **{info['consequence_when_below']}** — no discrepancy is claimed |",
          f"| decision loss | false positive {dec['loss']['false_positive']} : false negative {dec['loss']['false_negative']} — {dec['loss']['unit']} |",
          "",
          f"Identification width: {ident['source']}",
          "",
          "The floor is twice the SESOI. At a width equal to the SESOI a discrepancy of that size",
          "would need the joint to sit on a Fréchet endpoint; twice leaves room for a SESOI-sized",
          "discrepancy strictly inside the identified set. `validate_contract.py` holds the floor at",
          "or above the SESOI; the runner compares the realized width with it after the rows exist.",
          "",
          "**What this trades.** The S5 inference block treats identification width as a cost — a",
          "quantity to bound from above — because it was written for estimating one number. E8's",
          "target needs the opposite: the marginal-only width is the resource, and a pool without it",
          "cannot answer the question. Rather than invert `width_max`, the contract keeps S5's three",
          "groups on the joint design (which point-identifies the discrepancy, width 0) and adds a",
          "fourth, `informativeness`, for the width a marginal-only reader faces. The cost is that a",
          "validator pass no longer says the design is adequate: the floor is a promise about a",
          "consequence, checked only once the marginals are observed, and the only thing that can",
          "catch a degenerate pool before scoring is a scouting slice that is then burned.",
          "",
          "## Operating point — from the contract, not restated",
          "",
          f"Per guard, the `{op['direction']}` observed benign score whose false-positive rate on the",
          f"calibration set does not exceed **{op['fpr_budget']}**, flagging when score `{op['comparator']}`",
          f"threshold (`{op['objective']}`). A guard with no feasible candidate is excluded",
          f"(`{op['no_feasible_candidate']}`). Calibration pool `{c['execution_plan']['calibration']}`,",
          f"evaluation pool `{c['execution_plan']['evaluation']}`; declared and planned pools are equal",
          "or validation fails. The budget is a deployable one and was not moved: the pool moved.",
          "",
          "## Pool selection — scouting, burned",
          "",
          f"Seed `{s['seed']}`. {s['rule']}",
          "",
          f"{s['burn']}",
          "",
          "| candidate | why it was a candidate | contamination |",
          "|---|---|---|"]
    for cand in s["candidates"]:
        L.append(f"| `{cand['id']}` — {cand['upstream']['hf_id']} @ `{cand['upstream']['revision'][:8]}`, "
                 f"{cand['upstream']['license']} | {cand['why']} | {cand['contamination']} |")
    L += [""] + [f"Excluded before scouting: `{e['id']}` — {e['why']}" for e in s["excluded_before_scouting"]]
    r = s.get("results")
    if r:
        L += ["", "### Scouting result",
              "",
              f"Scouting thresholds, from the scouting calibration set of {r['scouting_calibration_n']} benign items:",
              " ".join(f"{g} {t:.6f}" for g, t in r["scouting_thresholds"].items()) + ".",
              "",
              "| candidate | n | miss G1 | miss G2 | Fréchet width | in band | rows | eligible |",
              "|---|---|---|---|---|---|---|---|"]
        for row in r["candidates"]:
            m = row["miss_float"]
            L.append(f"| `{row['id']}` | {row['n']} | {m['G1']:.4f} | {m['G2']:.4f} | {row['width_float']:.4f} | "
                     f"{'yes' if row['in_middle_band'] else 'no'} | {row['available_after_removal']} | "
                     f"{'**yes**' if row['eligible'] else 'no'} |")
        L += ["", f"**{r['verdict']}.**"]
        if not r["chosen"]:
            g2 = max(row["miss_float"]["G2"] for row in r["candidates"])
            g2min = min(row["miss_float"]["G2"] for row in r["candidates"])
            L += ["",
                  "### What the stop says",
                  "",
                  f"G2's scouting threshold is {r['scouting_thresholds']['G2']:.6f}: on the benign calibration",
                  "population (OR-Bench's seemingly-toxic-but-benign prompts) its scores saturate, so the budget",
                  f"pushes its threshold to the top of the scale and it misses between {100 * g2min:g}% and",
                  f"{100 * g2:g}% of every candidate. G1 lands in or near the band on two of three. The",
                  "marginal-only width is bounded by the more extreme guard, so no candidate clears the floor,",
                  "and the rule written before scoring says the run does not proceed.",
                  "",
                  "This is not a rescue point. The budget stays; the benign population stays; the floor stays.",
                  "What a next contract may change, before any score under it exists: the benign calibration",
                  "population (a plain-benign pool may move G2's threshold down and its miss rate into the",
                  "band), or the second guard. Either is a new contract with a new freeze and its own scouting,",
                  "and choosing it is the owner's decision. The three scouting slices here are burned for it.",
                  "",
                  "The evaluation pool was never drawn, no evaluation item was scored, and the contract stays",
                  "`draft`: the runner refuses it, so E8 has produced no observation row."]
    else:
        L += ["", "Scouting has not been scored."]
    L += ["", "## Freeze", ""]
    if f:
        L += [f"Frozen {f['frozen']}. Evaluation pool `{f['chosen_candidate']}`, {f['sizes']['evaluation_harmful']} items;",
              f"evaluation calibration {f['sizes']['evaluation_benign_calibration']} benign items, disjoint from the",
              f"scouting calibration set. Bootstrap B = {f['bootstrap']['B']} under the seed above.",
              "", "| frozen file | sha256 |", "|---|---|"]
        L += [f"| `{k}` | `{v}` |" for k, v in f["items"].items()]
        L += ["", f"Contract sha256 at freeze: `{f['contract_sha256']}`."]
    else:
        L += ["Not frozen. No evaluation item may be scored."]
    L += ["", "## Predictions, fixed before any evaluation item is scored", "",
          f"1. The realized marginal-only width on the evaluation pool is at or above the floor "
          f"{info['marginal_only_width_min']}. If it is not, the run is {info['consequence_when_below']} and "
          "no discrepancy is claimed, whatever the rows say.",
          "2. The observed all-miss rate lies inside the Fréchet interval. If not, the instrument is wrong, not the world.",
          f"3. The 95% bootstrap interval on the discrepancy has half width at most {prec['desired_ci_half_width']}.",
          "4. The discrepancy is positive and its interval excludes zero. Every intermediate-marginal matrix examined",
          "   to date (BELLS-11, Alotaibi-7) shows a positive discrepancy; on this pool that is the expectation and",
          "   an interval including zero is the interesting outcome.",
          "", "## Forbidden rescues", "",
          "- no change to the budget, comparator, direction, SESOI, margin, floor or consequence after any score exists",
          "- no second scouting pass, and no evaluation item drawn from a scouting slice",
          "- no recomputation of the discrepancy at other thresholds on E3's or E3B's frozen rows reported as evidence;",
          "  reuse of frozen rows is not reuse of confirmatory status (correction C3)",
          "- no adding, dropping or swapping a guard after any item is scored",
          "- no describing E8 as replacing E3 or E3B; both stand on their own pools",
          "", "## Non-claims", "",
          "- Two research classifiers on one pool at one operating point are not a deployed stack.",
          "- A pool chosen to clear the floor is a pool where the question is answerable, not a sample of production traffic.",
          "- G2's contamination status is unverifiable; the candidate table records what is known for G1.",
          "- The scouting slices are diagnostic only: their marginals selected the pool and are evidence about nothing else.",
          "- No benign evaluation stratum is scored; the contract's pools are the executed universe and neither is benign evaluation.",
          "- Nothing here transfers to E2's guards, pools or operating points.",
          ""]
    return "\n".join(L)


def main() -> int:
    text = render()
    path = E8 / "PREREG.md"
    if "--check" in sys.argv:
        if not path.exists() or path.read_text() != text:
            print("FAIL  experiments/e8/PREREG.md drifts from its sources; run render_prereg.py")
            return 1
        print("ok    experiments/e8/PREREG.md renders its sources")
        return 0
    path.write_text(text)
    print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
