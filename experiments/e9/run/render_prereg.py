#!/usr/bin/env python3
"""Render experiments/e9/PREREG.md from the contract, the protocol, the freeze and any results.

    python3 experiments/e9/run/render_prereg.py            # write PREREG.md
    python3 experiments/e9/run/render_prereg.py --check    # exit 1 on drift

Correction C1: the contract is the canonical executable semantics and the
preregistration renders it into English. No number below is typed here; each is
read from contract.json, freeze/protocol.json, freeze/freeze.json or
results/analysis.json. tests/test_e8_runner.py holds the rendered file to this
renderer, so an edit to the prose that is not an edit to its source fails the
manifest.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
E9 = ROOT / "experiments/e9"
FREEZE = E9 / "freeze"


def load(path: Path) -> dict | None:
    return json.loads(path.read_text()) if path.exists() else None


def pct(x: float) -> str:
    return f"{100 * x:g} percentage points"


def cap(s: str) -> str:
    """The protocol stores clauses; a sentence in the rendering starts with a capital."""
    return s[:1].upper() + s[1:]


def render() -> str:
    c, p = load(E9 / "contract.json"), load(FREEZE / "protocol.json")
    f, a = load(FREEZE / "freeze.json"), load(E9 / "results" / "analysis.json")
    op, inf = c["operating_point"], c["inference"]
    ident, prec, dec, info = inf["identification"], inf["precision"], inf["decision"], inf["informativeness"]
    csha = hashlib.sha256((E9 / "contract.json").read_bytes()).hexdigest()
    tb, st, sz, draw = p["target_benign"], p["stress"], p["sizes"], p.get("draw", {})
    floor = info["marginal_only_width_min"]
    L = []
    L += ["# E9 — calibrated on the traffic the guards are built for",
          "",
          f"**Rendered from `contract.json` (`{c['id']}`, status `{c['status']}`, sha256 `{csha[:16]}…`),",
          "`freeze/protocol.json` and `freeze/freeze.json` by `run/render_prereg.py`. Nothing here is",
          "typed by hand; an edit to this file that is not an edit to its source fails the manifest.**",
          "",
          "## The decision, and the one variable it changes",
          "",
          f"Owner, {p['owner_decision']}",
          "",
          f"**Changed:** {p['changed_variable']}",
          "",
          "**Held fixed:**",
          ""]
    L += [f"- {h}" for h in p["held_fixed"]]
    L += ["", f"**The rule.** {p['rule']}", "",
          "## What E9 can separate", ""]
    L += [f"- **{k}.** {cap(v)}" for k, v in p["hypotheses"].items() if k in ("H1", "H2")]
    L += ["", cap(p["hypotheses"]["discrimination"]), "",
          "## Identification group — E8's, unchanged",
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
          f"| **marginal-only width floor** | **{floor}** ({pct(floor)}) |",
          f"| **consequence below the floor** | **{info['consequence_when_below']}** — no discrepancy is claimed |",
          f"| decision loss | false positive {dec['loss']['false_positive']} : false negative "
          f"{dec['loss']['false_negative']} — {dec['loss']['unit']} |",
          "",
          "## Operating point — from the contract, not restated",
          "",
          f"Per guard, the `{op['direction']}` observed benign score whose false-positive rate on the",
          f"calibration set does not exceed **{op['fpr_budget']}**, flagging when score `{op['comparator']}`",
          f"threshold (`{op['objective']}`). A guard with no feasible candidate is excluded",
          f"(`{op['no_feasible_candidate']}`). Calibration pool `{c['execution_plan']['calibration']}`,",
          f"evaluation pool `{c['execution_plan']['evaluation']}`.",
          "",
          p["threshold_rule"],
          "",
          "## Calibration population — representative benign traffic",
          "",
          f"{cap(tb['definition'])}.",
          "",
          f"Source: `{tb['source']['hf_id']}` @ `{tb['source']['revision'][:8]}`, {tb['source']['license']}, "
          f"ungated. Files, each verified by sha256 before a row is read:",
          ""]
    L += [f"- shard {x['shard']}: `{x['file']}` (`{x['sha256'][:12]}…`)" for x in tb["source"]["files"]]
    L += ["", f"Sampling frame: {tb['sampling_frame']}", "", "Filters, and nothing else:", ""]
    L += [f"- {x}" for x in tb["filters"]]
    marks = tb["exclude_markers"]
    L += ["",
          "Canonical attack markers, case-insensitive: "
          + ", ".join(f"`{m}`" for m in marks["substrings_case_insensitive"])
          + "; and the whole word " + ", ".join(f"`{w}`" for w in marks["whole_words_case_sensitive"])
          + ", case-sensitive.",
          "",
          f"**Toxicity is not a filter.** {tb['toxicity_not_filtered']}",
          "",
          f"**Residual attacks.** {tb['residual_attacks']}",
          "",
          f"**Contamination.** {tb['contamination']}",
          ""]
    if draw.get("target_benign"):
        fc = draw["target_benign"]["filter_counts"]
        L += ["| step | conversations |", "|---|---|"]
        L += [f"| {k} | {v:,} |" for k, v in fc.items()]
        L += [f"| after deduplication and removal of prior frozen hashes | "
              f"{draw['target_benign']['available_after_removal']:,} |", ""]
    L += ["Considered and excluded before any score:", "", "| source | why |", "|---|---|"]
    L += [f"| `{x['id']}` | {x['why']} |" for x in p["calibration_sources_excluded"]]
    L += ["",
          "## Hard-negative stress stratum — reported, never deciding",
          "",
          f"Source: `{st['source']}`, {st['provenance']}: `{st['path']}` (`{st['sha256'][:12]}…`), {st['license']}.",
          f"Reported: {st['reported_as']}. It never sets a threshold and never decides admission.",
          "",
          "## Partitions — drawn at once, before any score",
          "",
          "| partition | size | drawn | role |",
          "|---|---|---|---|"]
    parts = draw.get("partitions", {})
    L += [f"| calibration | {sz['calibration']} | {parts.get('items_calibration', '—')} | {p['partitions']['calibration']} |",
          f"| stress | {sz['stress']} | {parts.get('items_stress', '—')} | {p['partitions']['stress']} |",
          f"| scouting, per candidate | {sz['scout_harmful_per_candidate']} | see below | {p['partitions']['scouting']} |",
          f"| measurement, per candidate | {sz['measurement_harmful_per_candidate']} | see below | {p['partitions']['measurement']} |",
          "",
          cap(p["no_double_duty"]),
          "",
          f"Ranking: {p['ranking']} Seed `{p['seed']}`.",
          "",
          "## Admission",
          "",
          p["admission"],
          "",
          f"**Limitation, stated before any score.** {p['admission_limitation']}",
          "",
          "## Candidates — E8's three, unchanged",
          "",
          "| candidate | why it is a candidate | contamination | available after removal | measurement slice |",
          "|---|---|---|---|---|"]
    for cand in p["candidates"]:
        up, d = cand["upstream"], draw.get("candidates", {}).get(cand["id"], {})
        slice_note = (f"{d['measurement_n']} {'(complete)' if d['measurement_complete'] else '(incomplete: cannot be admitted)'}"
                      if d else "—")
        L += [f"| `{cand['id']}` — {up['hf_id']} @ `{up['revision'][:8]}`, {up['license']} | {cand['why']} | "
              f"{cand['contamination']} | {d.get('available_after_removal', '—')} | {slice_note} |"]
    L += ["", "## Freeze", ""]
    if f:
        L += [f"Frozen {f['frozen_on']}. Seed `{f['seed']}`; bootstrap B = {f['bootstrap']['B']} "
              f"({f['bootstrap']['interval']}).",
              f"Contract sha256 `{f['contract_sha256'][:16]}…`; protocol declaration digest "
              f"`{f['protocol_declared_sha256'][:16]}…`.",
              "",
              f['order_witness'],
              "",
              "| item list | sha256 |", "|---|---|"]
        L += [f"| `{k}` | `{v[:16]}…` |" for k, v in f["items"].items()]
    else:
        L += ["Not frozen. No E9 item may be scored."]
    L += ["",
          "## Predictions, fixed before any E9 item is scored",
          "",
          f"1. Admission. H2 predicts that at least one candidate's scouting width clears the floor {floor} at E9's "
          f"operating point; H1 predicts that none does. Whichever holds is the result; neither is a failure of E9.",
          f"2. If a pool is admitted, its realized marginal-only width on the "
          f"{sz['measurement_harmful_per_candidate']} measurement items is at or above {floor}. If not, the run is "
          f"{info['consequence_when_below']} and no discrepancy is claimed, whatever the rows say.",
          "3. The observed all-miss rate lies inside the Fréchet interval. If not, the instrument is wrong, not the world.",
          f"4. The 95% bootstrap interval on the discrepancy has half width at most {prec['desired_ci_half_width']}.",
          "5. The discrepancy is positive and its interval excludes zero. This is carried from E8, where no pool was",
          "   admitted to test it.",
          "",
          "## Forbidden rescues",
          "",
          "- no change to the calibration population, its filters, markers or sampling frame after any E9 score exists,",
          "  and no second calibration population within E9",
          "- no change to the budget, comparator, direction, SESOI, margin, floor or consequence: contract.json is frozen",
          "- no threshold retuned after any width is seen; analyze.py stops if the measurement thresholds differ from",
          "  the admission thresholds",
          "- no second admission pass, no added candidate, and no measurement item from a calibration, stress or",
          "  scouting slice",
          "- the stress stratum never sets a threshold and never decides admission",
          "- no adding, dropping or swapping a guard; a new guard is E10, under its own contract",
          "- no recomputation on E3's, E3B's or E8's frozen rows reported as evidence (correction C3)",
          "",
          "## Non-claims",
          "",
          "- Two research classifiers at one operating point are not a deployed stack.",
          "- Representative benign traffic here is a declared population: English first turns to one public chatbot",
          "  service, in three chronological shards. Another deployment's benign traffic is a different population.",
          "- G2's contamination status is unverifiable. G1's is checked against its declared training sets and their",
          "  stated components only.",
          "- The admission width is a point estimate on the scouting slice; the limitation above is part of the result.",
          "- A result on these three pools does not settle H1 or H2 for other pools, guards or budgets.",
          "- The stress stratum's false-positive rates describe these guards on seemingly-toxic prompts at E9's",
          "  thresholds. They are not a deployment false-positive rate.",
          "- Nothing here transfers to E2's guards, pools or operating points."]
    r = p.get("results")
    if r:
        L += ["", "## Admission result", ""]
        if r.get("candidates"):
            L += [f"Thresholds from the {r['calibration_n']} calibration items: "
                  + " ".join(f"{g} {t:.6f}" for g, t in r["thresholds"].items())
                  + ". E8's, calibrated on the stress population: "
                  + " ".join(f"{g} {t:.6f}" for g, t in r["e8_comparison"]["thresholds"]["E8"].items()) + ".",
                  "",
                  "| candidate | n | miss G1 | miss G2 | Fréchet width | E8 width | clears floor | complete | admitted |",
                  "|---|---|---|---|---|---|---|---|---|"]
            for row in r["candidates"]:
                e8w = r["e8_comparison"]["scouting"][row["id"]]["E8_width"]
                L += [f"| `{row['id']}` | {row['n']} | {row['miss_float'].get('G1', float('nan')):.4f} | "
                      f"{row['miss_float'].get('G2', float('nan')):.4f} | {row['width_float']:.4f} | {e8w:.4f} | "
                      f"{'yes' if row['width_clears_floor'] else 'no'} | {'yes' if row['measurement_complete'] else 'no'} | "
                      f"{'**yes**' if row['admitted'] else 'no'} |"]
            s = r["stress"]
            L += ["",
                  f"Stress stratum, {s['n']} seemingly-toxic benign prompts at E9's thresholds: false-positive rate "
                  + ", ".join(f"{g} {v:.4f}" for g, v in s["false_positive_rate_float"].items())
                  + f"; both flag {s['both_flagged_rate']:.4f}."]
        L += ["", f"**{r['verdict']}**"]
    if a:
        L += ["", "## Measurement result", "",
              f"Pool `{a['admitted_pool']}`, n = {a['n']}, at the admission thresholds (asserted equal).",
              "",
              "| quantity | value |", "|---|---|"]
        L += [f"| miss rate, {g} | {v:.4f} |" for g, v in a["miss_rates"].items()]
        L += [f"| q_obs, both miss | {a['q_obs']:.4f} |",
              f"| q_ind, independence plug-in | {a['q_ind']:.4f} |",
              f"| discrepancy | {a['delta']:+.4f} |",
              f"| 95% bootstrap interval, B = {a['bootstrap_B']} | [{a['delta_ci95'][0]:+.4f}, {a['delta_ci95'][1]:+.4f}] |",
              f"| realized marginal-only width | {a['marginal_only_width']:.4f} (floor {a['declared_floor']}) |",
              f"| Fréchet interval | [{a['frechet'][0]:.4f}, {a['frechet'][1]:.4f}]; q_obs inside: "
              f"{'yes' if a['inside_frechet'] else 'no'} |",
              "", f"**{a['verdict']}**"]
    return "\n".join(L) + "\n"


def main() -> int:
    out = render()
    target = E9 / "PREREG.md"
    if "--check" in sys.argv:
        if not target.exists() or target.read_text() != out:
            print("DRIFT: experiments/e9/PREREG.md is not the rendering of its sources")
            return 1
        print("ok    experiments/e9/PREREG.md renders its sources")
        return 0
    target.write_text(out)
    print("wrote experiments/e9/PREREG.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
