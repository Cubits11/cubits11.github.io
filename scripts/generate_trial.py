#!/usr/bin/env python3
"""Generate /trials/necromancer/ — Trial IV — from trials/necromancer/manifest.yaml
and trials/necromancer/cases.json.

The page never carries a bare-case key. The trained case carries its key
because the debrief is the lesson; every trained move is bound to the template
whose rule and repository source the manifest declares. The arm table is
computed here from the frozen seed and embedded as data; the runtime only
looks it up. Strings come from the manifest, once.

--check fails on drift, so a manifest or case edit that the page does not
reflect fails the build until the page is regenerated and the pilot freeze
re-hashed.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from generate_missing_column import PAGE_FOOT, SITE, breadcrumbs, esc, jsonld_script, page_head  # noqa: E402

MANIFEST = ROOT / "trials" / "necromancer" / "manifest.yaml"
CASES = ROOT / "trials" / "necromancer" / "cases.json"
OUT = ROOT / "trials" / "necromancer" / "index.html"
KEYS = ("rescue", "correction", "surrender")
SPLIT = {"rescue": 3, "correction": 3, "surrender": 2}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def arm_table(seed: str, slots: int) -> dict:
    """Seeded hash within consecutive pairs (1,2), (3,4), …: in each pair the slot
    with the lower sha256(seed:slot) is arm A. Every even prefix of the
    enrolment order is then balanced, so eight acceptances give 4 and 4."""
    table = {}
    for lo in range(1, slots + 1, 2):
        hi = lo + 1
        a = lo if sha256_bytes(f"{seed}:{lo}".encode()) < sha256_bytes(f"{seed}:{hi}".encode()) else hi
        table[str(lo)] = "A" if a == lo else "B"
        table[str(hi)] = "A" if a == hi else "B"
    return table


def instrument_hash() -> str:
    return sha256_bytes(MANIFEST.read_bytes() + CASES.read_bytes())


def check_moves(case_id: str, moves: list, keyed: bool) -> None:
    ids = [m["id"] for m in moves]
    assert len(moves) == 8 and ids == [f"m{i}" for i in range(1, 9)], f"{case_id}: eight moves m1…m8 required"
    words = [len(m["text"].split()) for m in moves]
    assert max(words) - min(words) <= 16, f"{case_id}: move lengths spread {words}"
    if not keyed:
        banned = ("since ", "as i committed", "sealed", "falsifier", " also ", "along with", "not only")
        for m in moves:
            low = " " + m["text"].lower() + " "
            hit = [b for b in banned if b in low]
            assert not hit, f"{case_id} {m['id']}: lexical tell {hit}"
    if keyed:
        keys = [m["key"] for m in moves]
        assert {k: keys.count(k) for k in KEYS} == SPLIT, f"{case_id}: split is not 3/3/2"
        assert all(a != b for a, b in zip(keys, keys[1:])), f"{case_id}: adjacent moves share a key"
        assert keys[0] != "rescue", f"{case_id}: the first move must not be a rescue"
        templates = [m["template"] for m in moves]
        assert len(set(templates)) == 8, f"{case_id}: templates repeat"
    else:
        for m in moves:
            assert set(m) == {"id", "text"}, f"{case_id}: bare move {m['id']} carries more than id and text"


def build_data(m: dict, cases: dict) -> dict:
    t = m["trained"]
    check_moves("trained", t["moves"], keyed=True)
    tpl = {x["id"]: x for x in m["templates"]}
    assert set(tpl) == {mv["template"] for mv in t["moves"]}, "templates and trained moves disagree"
    for mv in t["moves"]:
        assert tpl[mv["template"]]["key"] == mv["key"], f"{mv['id']}: key disagrees with its template"
    for x in m["templates"]:
        for s in x["sources"]:
            p = ROOT / s["path"]
            assert p.exists(), f"template {x['id']}: source {s['path']} missing"
            assert s["quote"] in p.read_text(encoding="utf-8"), f"template {x['id']}: quote not found in {s['path']}: {s['quote']!r}"
        if x.get("mirror"):
            assert any(c["id"] == x["mirror"] for c in t["seal"]["forbidden_candidates"]), f"template {x['id']}: mirror names no candidate"
    bare = {c["id"]: c for c in cases["cases"]}
    assert set(bare) == {"pre", "cold"}, "cases.json must carry exactly pre and cold"
    for cid, c in bare.items():
        check_moves(cid, c["moves"], keyed=False)
        assert len(c["evidence"]) == 4, f"{cid}: four evidence bullets"
        assert c["commitment"]["consequence"] in ("REJECT", "NARROW", "HOLD")
    for mo in m["mythic_objects"]:
        assert mo.get("operation") and mo.get("deletion_test"), f"mythic object {mo.get('object')} lacks operation or deletion test"
    p = m["pilot"]
    arms = arm_table(p["seed"], int(p["slots"]))
    assert list(arms.values()).count("A") == p["slots"] // 2
    return {
        "id": m["id"], "version": m["version"], "experiment": m["experiment"],
        "instrument": instrument_hash(),
        "strings": m["strings"], "bins": m["bins"], "phases": m["phases"], "clock": m["clock_minutes"],
        "governing_rule": m["governing_rule"], "two_questions": m["two_questions"],
        "trained": {"id": t["id"], "field": t["field"], "title": t["title"], "setting": t["setting"],
                    "claim": t["claim"], "claim_short": t["claim_short"], "prediction_prompt": t["prediction_prompt"],
                    "seal": t["seal"], "evidence": t["evidence"],
                    "moves": [{"id": mv["id"], "text": mv["text"], "key": mv["key"], "template": mv["template"]} for mv in t["moves"]]},
        "templates": {x["id"]: {"name": x["name"], "key": x["key"], "rule": x["rule"], "sources": [s["path"] for s in x["sources"]], "mirror": x.get("mirror")} for x in m["templates"]},
        "cases": {cid: bare[cid] for cid in ("pre", "cold")},
        "pilot": {"seed": p["seed"], "slots": p["slots"], "arms": arms, "arm_gloss": p["arms"],
                  "primary_outcome": p["primary_outcome"], "decision_rule": p["decision_rule"]},
        "routes": m["routes"],
    }


CSS = """
.tr{--pad:clamp(1.25rem,4vw,2.4rem)}
.tr-hero{padding:6.4rem 0 1.4rem}
.tr-kicker{color:var(--gold);display:block;margin-bottom:.6rem}
.tr-h1{font-size:clamp(2.6rem,7vw,4.6rem);letter-spacing:-.02em;line-height:.98}
.tr-sub{font-family:var(--serif);font-style:italic;font-size:clamp(1.15rem,2.4vw,1.55rem);color:var(--muted);margin:.7rem 0 0}
.tr-strip{border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin-top:1.6rem}
.tr-strip .container{display:flex;flex-wrap:wrap;gap:.4rem 1.6rem;justify-content:space-between;padding-block:.55rem;color:var(--muted)}
.tr-strip b{color:var(--gold);font-weight:400}
.tr-clock{display:flex;gap:.6rem;align-items:baseline;white-space:nowrap}
.tr-clock[hidden]{display:none}
.tr-clock b{font-family:var(--serif);font-size:1.05rem;color:var(--ink);font-variant-numeric:tabular-nums}
.tr-phase{padding:2.4rem 0 3rem;border-bottom:1px solid var(--line)}
.tr-phase[hidden]{display:none}
.tr-phase h2{font-size:clamp(1.5rem,3.2vw,2.2rem);margin-bottom:.4rem;scroll-margin-top:5rem}
.tr-phase h2:focus{outline:none}
.tr-phase .lead{color:var(--muted);max-width:44em;font-size:1.02rem}
.tr-lbl{color:var(--gold);display:block;margin:1.4rem 0 .45rem}
.tr-case p,.tr-case li{max-width:46em}
.tr-case ul{padding-left:1.1rem;margin:0}
.tr-case li{margin:.35rem 0}
.tr-claim{font-family:var(--serif);font-size:clamp(1.3rem,2.6vw,1.8rem);line-height:1.25;border-left:2px solid var(--gold);padding:.4rem 0 .4rem 1rem;max-width:30em}
.tr-commit{border:1px solid var(--line-strong);background:var(--surface);padding:1rem 1.2rem;max-width:46em}
.tr-commit dl{margin:0;display:grid;grid-template-columns:8.5rem 1fr;gap:.45rem 1rem}
.tr-commit dt{color:var(--gold);font-family:var(--mono);font-size:.64rem;letter-spacing:.08em;text-transform:uppercase;padding-top:.2rem}
.tr-commit dd{margin:0}
.tr-commit dd ul{padding-left:1rem;margin:0}
.tr-moves{list-style:none;margin:0;padding:0;counter-reset:mv}
.tr-move{scroll-margin-top:5.5rem;border:1px solid var(--line-strong);background:var(--surface);padding:1rem 1.1rem 1.05rem;margin-top:.8rem}
.tr-move legend{font-family:var(--serif);font-size:1.08rem;line-height:1.4;padding:0;max-width:44em}
.tr-move legend::before{counter-increment:mv;content:counter(mv) " · ";color:var(--gold);font-family:var(--mono);font-size:.7rem;letter-spacing:.08em}
.tr-move fieldset{border:0;margin:0;padding:0;min-width:0}
.tr-bins{display:flex;flex-wrap:wrap;gap:.5rem;margin-top:.75rem}
.tr-bin{position:relative;scroll-margin-top:5.5rem}
.tr-bin input{position:absolute;opacity:0;width:1px;height:1px}
.tr-bin span{display:inline-flex;align-items:center;min-height:2.6rem;border:1px solid var(--line-strong);border-radius:999px;padding:.4rem .95rem;font-family:var(--mono);font-size:.66rem;letter-spacing:.08em;text-transform:uppercase;cursor:pointer;color:var(--muted);background:transparent}
.tr-bin input:checked+span{color:var(--ink);border-color:var(--ink);background:color-mix(in srgb,var(--ink) 8%,transparent)}
.tr-bin input:focus-visible+span{outline:2px solid var(--gold);outline-offset:3px}
.tr-actions{display:flex;flex-wrap:wrap;gap:.8rem 1.2rem;align-items:center;margin-top:1.4rem}
.tr-note{color:var(--muted);font-size:.9rem;margin:0}
.tr-err{color:var(--invalid);font-size:.9rem;margin:0}
.tr-field{margin-top:1rem;max-width:36em;scroll-margin-top:5.5rem}
.tr-field label{display:block;color:var(--muted);font-size:.9rem;margin-bottom:.35rem}
.tr-field input[type=text],.tr-field input[type=number],.tr-field textarea{width:100%;font:inherit;color:var(--ink);background:var(--surface);border:1px solid var(--line-strong);padding:.6rem .75rem}
.tr-field textarea{min-height:5.5rem;resize:vertical}
.tr-field input[type=number]{max-width:9rem}
.tr-published{margin-top:1.2rem;display:inline-block;border:1px solid var(--gold);padding:1rem 1.3rem;background:var(--surface)}
.tr-published .tr-claim{border:0;padding:0;margin:0}
.tr-stamp{display:inline-block;transform:rotate(-3deg);font-family:var(--mono);font-size:.62rem;letter-spacing:.1em;text-transform:uppercase;color:var(--gold);border:1px solid var(--gold);border-radius:2px;padding:.3rem .5rem;margin-top:.7rem}
.tr-seal{border:1px solid var(--gold);background:color-mix(in srgb,var(--gold) 6%,transparent);padding:1rem 1.2rem;max-width:46em;margin-top:1.2rem}
.tr-seal .tr-lbl{margin-top:0}
.tr-seal p{margin:0 0 .5rem}
.tr-seal .hash{font-family:var(--mono);font-size:.62rem;letter-spacing:.04em;color:var(--muted);overflow-wrap:anywhere}
.tr-radios label,.tr-checks label{scroll-margin-top:5.5rem;display:flex;gap:.6rem;align-items:flex-start;padding:.45rem 0;border-bottom:1px solid var(--line);max-width:40em;cursor:pointer}
.tr-radios input,.tr-checks input{margin-top:.35rem;flex:none;width:1.05rem;height:1.05rem}
.tr-radios small,.tr-checks small{display:block;color:var(--muted)}
.tr-evidence li{font-size:1.05rem;margin:.5rem 0}
.tr-evidence li:first-child{font-family:var(--serif);font-size:1.3rem}
.tr-key{list-style:none;margin:0;padding:0}
.tr-key li{border:1px solid var(--line-strong);background:var(--surface);padding:1rem 1.1rem;margin-top:.8rem}
.tr-key .verdict{display:flex;flex-wrap:wrap;gap:.5rem 1.2rem;align-items:baseline;margin:.45rem 0 .6rem}
.tr-key .verdict b{font-weight:400}
.tr-key .ok b{color:var(--evidence)}
.tr-key .no b{color:var(--invalid)}
.tr-key .ok .verdict::before{content:"✓ ";color:var(--evidence)}
.tr-key .no .verdict::before{content:"✗ ";color:var(--invalid)}
.tr-key .rule{margin:.4rem 0 0;max-width:46em}
.tr-key .src{color:var(--muted);font-size:.78rem;margin:.35rem 0 0;overflow-wrap:anywhere}
.tr-key .mirror{color:var(--review);margin:.5rem 0 0;font-size:.95rem}
.tr-score{font-family:var(--serif);font-size:clamp(1.6rem,4vw,2.4rem);margin:.6rem 0 0}
.tr-govern{font-family:var(--serif);font-size:clamp(1.25rem,2.6vw,1.7rem);line-height:1.3;border-left:2px solid var(--gold);padding:.4rem 0 .4rem 1rem;max-width:30em;margin:0}
.tr-qs{padding-left:1.1rem;color:var(--muted);max-width:40em}
.tr-receipt{width:100%;min-height:16rem;font-family:var(--mono);font-size:.72rem;line-height:1.45;color:var(--ink);background:var(--surface);border:1px solid var(--line-strong);padding:.75rem}
.tr-static{display:none;padding:2rem 0 1rem}
html:not(.tr-js) .tr-static{display:block}
html:not(.tr-js) .tr-phase{display:none}
.tr-static ul{padding-left:1.1rem;max-width:46em}
.tr-static li{margin:.35rem 0;color:var(--muted)}
.tr-legend{display:grid;grid-template-columns:repeat(auto-fit,minmax(15rem,1fr));gap:.8rem;margin-top:.8rem}
.tr-legend div{border-top:1px solid var(--line-strong);padding-top:.6rem}
.tr-legend .mono{color:var(--gold);display:block;margin-bottom:.3rem}
.tr-legend p{margin:0;color:var(--muted);font-size:.92rem}
@media (max-width:640px){.tr-commit dl{grid-template-columns:1fr}.tr-bins{flex-direction:column;align-items:stretch}.tr-bin span{width:100%;justify-content:center}}
@media (prefers-reduced-motion: no-preference){html.tr-js .tr-phase:not([hidden]){animation:tr-in .3s var(--ease)}@keyframes tr-in{from{opacity:0}to{opacity:1}}}
@media (forced-colors: active){.tr-bin input:checked+span{outline:2px solid Highlight}}
"""


def render_bins(bins: list) -> str:
    return '<div class="tr-legend">' + "".join(
        f'<div><span class="mono">{esc(b["label"])}</span><p>{esc(b["test"])}</p></div>' for b in bins) + "</div>"


def render_page(m: dict, data: dict) -> str:
    S = m["strings"]
    t = data["trained"]
    trained_key = "".join(
        f'<li><span class="mono">{esc(data["templates"][mv["template"]]["name"])}</span> — {esc(data["templates"][mv["template"]]["key"])}: {esc(mv["text"])}</li>'
        for mv in t["moves"])
    jsonld = breadcrumbs(("The record", "/"), ("Trial IV · The Necromancer", m["route"])) + jsonld_script({
        "@context": "https://schema.org", "@type": "WebPage", "name": m["page_title"],
        "description": m["page_description"], "url": SITE + m["route"], "isPartOf": {"@type": "WebSite", "url": SITE + "/"},
        "learningResourceType": "trial", "educationalLevel": "any"})
    head = page_head(m["page_title"], m["page_description"], m["route"], CSS, jsonld)
    head = head.replace("Source: census.yaml · renderer: scripts/generate_missing_column.py",
                        "Source: trials/necromancer/manifest.yaml + cases.json · renderer: scripts/generate_trial.py")
    head = head.replace("<script defer src=\"/assets/site.js\"></script>",
                        "<script defer src=\"/assets/site.js\"></script>\n<script defer src=\"/trials/necromancer/trial.js\"></script>")
    non_claims = "".join(f"<li>{esc(nc)}</li>" for nc in m["non_claims"])
    phases_html = "".join(render_phase(p["id"], p["label"], S) for p in m["phases"])
    return f'''{head}
<main id="main" class="tr" data-phase="enrol" data-arm="">
  <script type="application/json" id="tr-data">{json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")}</script>
  <div class="container">
    <div class="tr-hero">
      <span class="mono tr-kicker">{esc(S["h1_kicker"])} · {esc(m["experiment"])}</span>
      <h1 class="tr-h1">{esc(S["h1"])}</h1>
      <p class="tr-sub">{esc(S["h1_sub"])}</p>
    </div>
  </div>
  <div class="tr-strip mono"><div class="container"><span id="tr-status">{esc(S["status_strip"])}</span><span class="tr-clock" id="tr-clock" hidden>{esc(S["elapsed"])} <b id="tr-elapsed">00:00</b> <span>{esc(S["clock_budget"].format(minutes=m["clock_minutes"]))}</span></span></div></div>
  <div class="sr-only" aria-live="polite" id="tr-live"></div>
  <div class="container">
    {phases_html}
    <div class="tr-static">
      <p class="lead">{esc(S["nojs"])}</p>
      <span class="mono tr-lbl">{esc(S["bins_legend"])}</span>
      {render_bins(m["bins"])}
      <span class="mono tr-lbl">{esc(S["debrief_governing"])}</span>
      <p class="tr-govern">{esc(m["governing_rule"])}</p>
      <span class="mono tr-lbl">THE TRAINED CASE · KEY</span>
      <ul>{trained_key}</ul>
    </div>
    <section class="tr-phase" id="phase-boundaries" aria-labelledby="bd-h" data-always>
      <h2 id="bd-h" class="mono" style="font-size:.72rem;font-family:var(--mono);color:var(--gold)">{esc(S["boundaries_summary"])}</h2>
      <ul class="tr-qs" style="color:var(--ink)">{non_claims}</ul>
      <p class="tr-note">Falsifier: {esc(m["falsifier"])}</p>
      <p class="tr-note">Pilot protocol, frozen before any human answers: <a class="u" href="{esc(m["routes"]["pilot"])}">trials/necromancer/pilot/PILOT.md</a> · code: <a class="u" href="{esc(m["routes"]["code"])}">trials/necromancer</a> · the registry this trial is built from: <a class="u" href="{esc(m["routes"]["ledger"])}">/ledger/</a> · the sibling instrument: <a class="u" href="{esc(m["routes"]["worldspace"])}">/worldspace/</a></p>
    </section>
  </div>
</main>
{PAGE_FOOT}'''


def render_phase(pid: str, label: str, S: dict) -> str:
    h = f'<h2 id="ph-{pid}-h" tabindex="-1"><span class="mono tr-kicker">{esc(label)}</span>'
    body = {
        "enrol": f'''{h}{esc(S["h1_sub"])}</h2>
      <p class="lead">{esc(S["enrol_lead"])}</p>
      <form id="tr-enrol" novalidate>
        <div class="tr-field"><label for="tr-slot">{esc(S["enrol_label"])}</label><input id="tr-slot" type="number" inputmode="numeric" min="1" max="10" step="1" autocomplete="off" required></div>
        <div class="tr-actions"><button type="submit" class="btn btn-solid">{esc(S["enrol_button"])}</button><p class="tr-err" id="tr-enrol-err" hidden>{esc(S["enrol_error"])}</p></div>
      </form>''',
        "pre": f'''{h}<span id="pre-title"></span></h2>
      <p class="lead">{esc(S["pre_lead"])}</p>
      <div class="tr-case" id="pre-case"></div>''',
        "claim": f'''{h}<span id="claim-title"></span></h2>
      <p class="lead">{esc(S["claim_lead"])}</p>
      <div class="tr-case" id="claim-case"></div>
      <form id="tr-publish" novalidate>
        <div class="tr-field"><label for="tr-handle">{esc(S["handle_label"])}</label><input id="tr-handle" type="text" maxlength="40" autocomplete="off"></div>
        <div class="tr-field"><label for="tr-predict" id="tr-predict-l"></label><input id="tr-predict" type="number" inputmode="numeric" min="0" max="100" step="1" autocomplete="off"></div>
        <div class="tr-actions"><button type="submit" class="btn btn-solid">{esc(S["publish"])}</button></div>
      </form>
      <div id="tr-published" hidden></div>
      <div class="tr-actions"><button type="button" class="btn btn-solid" id="tr-publish-go" hidden>{esc(S["publish_continue"])}</button></div>''',
        "seal": f'''{h}<span id="seal-title"></span></h2>
      <p class="lead" id="seal-lead"></p>
      <form id="tr-seal" novalidate>
        <span class="mono tr-lbl">{esc(S["seal_falsifier_label"])}</span>
        <p class="tr-claim" id="seal-falsifier"></p>
        <span class="mono tr-lbl" id="seal-cons-l"></span>
        <div class="tr-radios" id="seal-cons" role="radiogroup" aria-labelledby="seal-cons-l"></div>
        <span class="mono tr-lbl" id="seal-forb-l"></span>
        <div class="tr-checks" id="seal-forb" role="group" aria-labelledby="seal-forb-l"></div>
        <div class="tr-actions"><button type="submit" class="btn btn-solid">{esc(S["seal_button"])}</button><p class="tr-err" id="tr-seal-err" hidden>{esc(S["seal_incomplete"])}</p></div>
      </form>
      <div class="tr-seal" id="seal-done" hidden></div>
      <div class="tr-actions"><button type="button" class="btn btn-solid" id="tr-seal-go" hidden>{esc(S["seal_continue"])}</button></div>''',
        "evidence": f'''{h}{esc(S["evidence_lead"])}</h2>
      <ul class="tr-evidence" id="evidence-list"></ul>
      <div class="tr-actions"><button type="button" class="btn btn-solid" id="tr-evidence-go">{esc(S["evidence_continue"])}</button></div>''',
        "sort": f'''{h}<span id="sort-title"></span></h2>
      <p class="lead">{esc(S["sort_lead"])}</p>
      <div class="tr-seal" id="sort-seal"></div>
      <div class="tr-case" id="sort-case"></div>''',
        "debrief": f'''{h}{esc(S["debrief_lead"])}</h2>
      <p class="tr-score" id="debrief-score"></p>
      <p class="tr-note" id="debrief-mirror"></p>
      <ol class="tr-key" id="debrief-key"></ol>
      <span class="mono tr-lbl">{esc(S["debrief_governing"])}</span>
      <p class="tr-govern" id="debrief-govern"></p>
      <ul class="tr-qs" id="debrief-qs"></ul>
      <div class="tr-actions"><button type="button" class="btn btn-solid" id="tr-debrief-go">{esc(S["debrief_continue"])}</button></div>''',
        "update": f'''{h}<span id="update-title"></span></h2>
      <form id="tr-update" novalidate>
        <p class="lead">{esc(S["update_lead"])}</p>
        <div class="tr-field"><label for="tr-updated">{esc(S["update_label"])}</label><textarea id="tr-updated" maxlength="400"></textarea></div>
        <p class="lead" style="margin-top:1.4rem">{esc(S["recall_lead"])}</p>
        <div class="tr-field"><label for="tr-recall">{esc(S["recall_label"])}</label><textarea id="tr-recall" maxlength="400"></textarea></div>
        <div class="tr-actions"><button type="submit" class="btn btn-solid">{esc(S["update_button"])}</button><p class="tr-err" id="tr-update-err" hidden>{esc(S["update_incomplete"])}</p></div>
      </form>''',
        "cold": f'''{h}<span id="cold-title"></span></h2>
      <p class="lead">{esc(S["cold_lead"])}</p>
      <div class="tr-case" id="cold-case"></div>''',
        "receipt": f'''{h}{esc(S["reactions_lead"])}</h2>
      <form id="tr-react" novalidate>
        <span class="mono tr-lbl" id="conf-l">{esc(S["confidence_label"])}</span>
        <div class="tr-bins" id="tr-conf" role="radiogroup" aria-labelledby="conf-l"></div>
        <span class="mono tr-lbl" id="help-l">{esc(S["helped_label"])}</span>
        <div class="tr-bins" id="tr-help" role="radiogroup" aria-labelledby="help-l"></div>
        <div class="tr-field"><label for="tr-comment">{esc(S["comment_label"])}</label><textarea id="tr-comment" maxlength="600"></textarea></div>
        <div class="tr-actions"><button type="submit" class="btn btn-solid">{esc(S["finish"])}</button></div>
      </form>
      <div id="tr-receipt-wrap" hidden>
        <p class="lead">{esc(S["receipt_lead"])}</p>
        <label for="tr-receipt" class="sr-only">The receipt</label>
        <textarea id="tr-receipt" class="tr-receipt" readonly></textarea>
        <div class="tr-actions"><button type="button" class="btn btn-solid" id="tr-copy">{esc(S["copy"])}</button><p class="tr-note" id="tr-copied" hidden>{esc(S["copied"])}</p></div>
      </div>''',
    }[pid]
    hidden = "" if pid == "enrol" else " hidden"
    return f'<section class="tr-phase" id="phase-{pid}" aria-labelledby="ph-{pid}-h"{hidden}>\n      {body}\n    </section>\n    '


def main() -> int:
    m = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    data = build_data(m, cases)
    html = render_page(m, data)
    if "--check" in sys.argv:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != html:
            print(f"DRIFT  {OUT.relative_to(ROOT)} is stale — run scripts/generate_trial.py")
            return 1
        print(f"ok    {OUT.relative_to(ROOT)} matches the manifest and cases ({len(html)} bytes)")
        return 0
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(html)} bytes) · instrument {data['instrument'][:12]}… · arms {''.join(data['pilot']['arms'][str(s)] for s in range(1, 11))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
