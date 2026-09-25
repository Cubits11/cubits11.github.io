#!/usr/bin/env python3
"""Render experiments/e9/PREREG.md from frozen sources, and RESULT.md once results exist.

    python3 experiments/e9/run/render_prereg.py            # write PREREG.md (and RESULT.md)
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
    return "\n".join(L) + "\n"


def render_result() -> str | None:
    """RESULT.md: what the frozen design produced. None until analysis exists.

    PREREG.md is a pre-result object and stays one. Outcomes, and the record of
    how they were checked against the predictions PREREG.md fixed, render here
    and only here. Every number is read from freeze/protocol.json's results,
    results/analysis.json or the contract; the prose below states scope and
    threats, never a value."""
    c, p = load(E9 / "contract.json"), load(FREEZE / "protocol.json")
    f, a = load(FREEZE / "freeze.json"), load(E9 / "results" / "analysis.json")
    r = (p or {}).get("results")
    if not (a and r):
        return None
    dec, prec = c["inference"]["decision"], c["inference"]["precision"]
    sesoi, floor = dec["SESOI"], c["inference"]["informativeness"]["marginal_only_width_min"]
    lo, hi = a["delta_ci95"]
    declared = {k: v for k, v in p.items() if k != "results"}
    digest = hashlib.sha256(json.dumps(declared, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    digest_holds = digest == f["protocol_declared_sha256"]
    yes = lambda b: "held" if b else "**did not hold**"
    preds = [
        ("1. Admission", f"H2: at least one scouting width at or above {floor}",
         f"`{r['admitted']}` admitted; {r['hypothesis']}", r["hypothesis"] == "H2"),
        ("2. Realized width", f"marginal-only width on the measurement set at or above {floor}",
         f"{a['marginal_only_width']:.4f} ({a['identification_status']})", a["marginal_only_width"] >= floor),
        ("3. Instrument", "observed all-miss rate inside the Fréchet interval",
         f"{a['q_obs']:.4f} in [{a['frechet'][0]:.4f}, {a['frechet'][1]:.4f}]", a["inside_frechet"]),
        ("4. Precision", f"95% interval half width at most {prec['desired_ci_half_width']}",
         f"{a['realized_ci_half_width']:.4f}", a["precision_met"]),
        ("5. Direction", "discrepancy positive, interval excludes zero",
         f"{a['delta']:+.4f}, [{lo:+.4f}, {hi:+.4f}]", a["delta"] > 0 and a["ci_excludes_zero"]),
    ]
    L = ["# E9 — result",
         "",
         "**Rendered by `run/render_prereg.py` from `freeze/protocol.json` (its `results` block), "
         "`results/analysis.json` and `contract.json`. No number here is typed by hand; an edit that is "
         "not an edit to those sources fails the manifest.** The design, predictions and forbidden rescues "
         "are in `PREREG.md`, which renders only frozen sources and holds no outcome.",
         "",
         "## The result, at its scope",
         "",
         f"On the admitted pool `{a['admitted_pool']}`, for guards {', '.join(a['guards'])} at the frozen "
         f"operating point, on {a['n']} measurement items, the observed rate at which both guards miss is "
         f"{a['q_obs']:.4f}; the independence plug-in from the two observed miss rates is {a['q_ind']:.4f}. "
         f"The discrepancy is {a['delta']:+.4f} (95% bootstrap interval [{lo:+.4f}, {hi:+.4f}], "
         f"B = {a['bootstrap_B']}). The two miss rates alone leave the all-miss rate anywhere in "
         f"[{a['frechet'][0]:.4f}, {a['frechet'][1]:.4f}], a width of {a['marginal_only_width']:.4f}.",
         "",
         f"Preregistered verdict: **{a['verdict'].split(':', 1)[0]}**. The rule is the one "
         "`run/analyze.py` carried in the freeze commit, before any E9 score existed: the interval "
         "excludes zero and the point discrepancy reaches the SESOI.",
         ""]
    if lo < sesoi <= a["delta"]:
        L += [f"The point estimate reaches the SESOI of {sesoi}; the interval does not lie wholly beyond it "
              f"(its lower end is {lo:.4f}). The measurement establishes a discrepancy from zero. It does not "
              f"establish that the discrepancy exceeds {sesoi}.", ""]
    L += ["## The predictions PREREG.md fixed, checked",
          "",
          "| prediction | stated before any score | observed | |",
          "|---|---|---|---|"]
    L += [f"| {n} | {s} | {o} | {yes(b)} |" for n, s, o, b in preds]
    L += ["", "## Admission", "",
          f"Thresholds from the {r['calibration_n']} calibration items: "
          + " ".join(f"{g} {t:.6f}" for g, t in r["thresholds"].items())
          + ". E8's, calibrated on the stress population: "
          + " ".join(f"{g} {t:.6f}" for g, t in r["e8_comparison"]["thresholds"]["E8"].items())
          + f". The measurement run recomputed the same thresholds: "
          f"{'asserted equal' if a['thresholds_equal_admission'] else '**differ**'}.",
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
          + f"; both flag {s['both_flagged_rate']:.4f}. Reported, never deciding.",
          "",
          "## Measurement",
          "",
          "| quantity | value |", "|---|---|"]
    L += [f"| miss rate, {g} | {v:.4f} |" for g, v in a["miss_rates"].items()]
    L += [f"| both miss, observed | {a['q_obs']:.4f} |",
          f"| both miss, independence plug-in | {a['q_ind']:.4f} |",
          f"| discrepancy | {a['delta']:+.4f} (exact {a['delta_exact']}) |",
          f"| 95% bootstrap interval | [{lo:+.4f}, {hi:+.4f}] |",
          f"| marginal-only Fréchet interval | [{a['frechet'][0]:.4f}, {a['frechet'][1]:.4f}] |",
          f"| marginal-only width | {a['marginal_only_width']:.4f} (floor {a['declared_floor']}) |",
          "",
          "## Threats to validity",
          "",
          "- **Pool selection.** Admission chose the pool whose scouting marginals left the widest identified "
          "set among candidates with a complete measurement slice. The measurement items are disjoint from "
          "every scouting item, so no item decided admission and measured the joint, but the result describes "
          "a pool selected for intermediate marginals, not pools in general.",
          "- **The interval omits calibration uncertainty.** The bootstrap resamples measurement items with "
          "the thresholds held at their admission values. Variation from re-drawing the calibration set is "
          "not in the interval.",
          "- **The operating point is declared, not deployed.** Thresholds sit at a 5% false-positive budget "
          "on representative benign traffic; the stress stratum shows how much higher one guard's "
          "false-positive rate is on hard negatives.",
          "- **Training contamination.** The second guard's fine-tuning corpus could not be verified; the "
          "admitted pool is not among the first guard's declared training sets (see `PREREG.md`).",
          "- **Where the verdict rule lives.** SESOI and margin are in the frozen contract; the rule that "
          "combines them into a verdict is in `run/analyze.py`, committed in the freeze commit and unchanged "
          "since, but not rendered into `PREREG.md`'s prose. Correction C1 asks for claim-critical choices to "
          "live in the contract; this one does not.",
          "- **The protocol file gained a results block.** `run/admit.py` appended the admission record to "
          "`freeze/protocol.json`. Everything above that block still hashes to the frozen declaration digest: "
          + ("**holds**." if digest_holds else "**FAILS**.")
          + " The file is therefore not byte-immutable after freeze; later experiments keep outcomes out of "
          "`freeze/`.",
          "- **One analyst, no independent replication.** Every step ran on the owner's machine from this "
          "repository. Re-running the committed scripts is replay, not reproduction.",
          "",
          "## What this does not establish",
          "",
          "- that guard pairs in general depart from independence, or in which direction;",
          "- anything about a deployed stack, a routing policy, or either guard's vendor;",
          "- that either guard, or the pair, is safe or unsafe;",
          "- the size of the discrepancy on other pools, other thresholds or other benign populations.",
          "",
          "## Provenance",
          "",
          "| object | sha256 |", "|---|---|"]
    L += [f"| `{v['path']}` | `{v['sha256'][:16]}…` |" for k, v in a["provenance"].items() if isinstance(v, dict)]
    L += ["",
          "Replay from a clone: `python3 experiments/e9/run/runner.py --contract experiments/e9/contract.json "
          "--scores experiments/e9/results/scores.json --out experiments/e9/results` then "
          "`python3 experiments/e9/run/analyze.py`. Scoring itself needs the pinned guards and "
          "`run/score.py`'s refusals; see `PREREG.md`."]
    return "\n".join(L) + "\n"


def main() -> int:
    outputs = {E9 / "PREREG.md": render(), E9 / "RESULT.md": render_result()}
    if "--check" in sys.argv:
        bad = 0
        for target, out in outputs.items():
            if out is None:
                continue
            if not target.exists() or target.read_text() != out:
                print(f"DRIFT: {target.relative_to(ROOT)} is not the rendering of its sources")
                bad = 1
            else:
                print(f"ok    {target.relative_to(ROOT)} renders its sources")
        return bad
    for target, out in outputs.items():
        if out is not None:
            target.write_text(out)
            print(f"wrote {target.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
