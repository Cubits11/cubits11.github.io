#!/usr/bin/env python3
"""Generate /try/ — the experiment entry surface — from distribution/experiments.yaml.

One question, three escalating experiments, structured intake, a public
external-status block bound to distribution/outcomes.yaml, and the
counterexample route. Every number comes from films/data/facts.json (derived
from the registries) or the outcomes ledger; census numerals are emitted
through facts.fact_span so verify_facts.py binds them. --check fails on drift,
so a ledger or registry change that the page does not reflect fails CI.
"""

from __future__ import annotations

import json
import sys
import urllib.parse
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import facts as fact_registry  # noqa: E402
import outcomes as outcomes_ledger  # noqa: E402
import verify_census  # noqa: E402
from generate_missing_column import PAGE_FOOT, SITE, breadcrumbs, esc, jsonld_script, page_head  # noqa: E402

OUT = ROOT / "try" / "index.html"
ISSUES = "https://github.com/Cubits11/cubits11.github.io/issues/new"

CSS = """
.try-hero{font-family:var(--serif);font-size:clamp(1.9rem,4.6vw,3.1rem);line-height:1.08;letter-spacing:-.01em;margin:.2rem 0 .6rem}
.try-hero b{color:var(--gold);font-weight:520}
.q{font-size:clamp(1.05rem,2vw,1.28rem);line-height:1.5;max-width:36em;color:var(--muted)}
.exp{border:1px solid var(--line-strong);background:var(--surface);padding:1.5rem 1.5rem 1.3rem;margin-top:1.4rem;scroll-margin-top:5.5rem}
.exp h3{margin:0;font-size:1.25rem}
.exp .meta{color:var(--muted);font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;margin:.35rem 0 1rem}
.exp dl{margin:0;display:grid;grid-template-columns:9.5rem 1fr;gap:.5rem 1rem;font-size:.94rem}
.exp dt{color:var(--gold);font-size:.68rem;letter-spacing:.06em;text-transform:uppercase;padding-top:.25rem}
.exp dd{margin:0;color:var(--muted)}
.exp dd.ink{color:var(--ink)}
.exp pre{margin:0;padding:.7rem .9rem;background:var(--bg);border:1px solid var(--line);overflow-x:auto;font-size:.86rem;line-height:1.5}
.exp .row{display:flex;flex-wrap:wrap;gap:.7rem;margin-top:1.1rem}
.status{border:1px solid var(--line-strong);background:var(--surface);padding:1.3rem 1.5rem;margin-top:1.4rem}
.status table{border-collapse:collapse;width:100%;max-width:34rem;font-variant-numeric:tabular-nums}
.status td{padding:.35rem 0;border-bottom:1px solid var(--line)}
.status td:last-child{text-align:right;font-family:var(--serif);font-size:1.35rem}
.status .diag{color:var(--muted);font-size:.9rem;margin:.9rem 0 0}
.routes{display:grid;grid-template-columns:repeat(auto-fit,minmax(15rem,1fr));gap:.8rem;margin-top:1.2rem}
.routes a{display:block;border:1px solid var(--line-strong);background:var(--surface);padding:.9rem 1rem;text-decoration:none;color:var(--ink);font-size:.95rem}
.routes a:hover{border-color:var(--gold)}
.routes a span{display:block;color:var(--muted);font-size:.78rem;margin-top:.25rem}
.film{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,1fr);gap:1.6rem;align-items:start;margin-top:1.2rem}
.film video{width:100%;height:auto;display:block;border:1px solid var(--line-strong);background:#0B0F0A}
.ladder{margin:1rem 0 0;padding-left:1.1rem;color:var(--muted);font-size:.94rem}
.ladder li{margin:.3rem 0}
@media (max-width:720px){.exp dl{grid-template-columns:1fr}.exp dt{padding-top:.6rem}.film{grid-template-columns:1fr}}
"""


def issue_url(template: str, prefill: dict) -> str:
    return ISSUES + "?" + urllib.parse.urlencode({"template": template, **{k: str(v) for k, v in prefill.items()}})


def a(href: str, label: str, solid: bool = False) -> str:
    cls = "btn btn-solid" if solid else "btn"
    return f'<a class="{cls}" href="{esc(href)}">{esc(label)}</a>'


def render_experiment(e: dict, facts: dict, films: dict) -> str:
    anchor = e["id"].lower()
    film = films.get(e["film"], {})
    film_line = ""
    if film:
        film_line = (f'<dt>Film</dt><dd><a class="u" href="/films/{esc(e["film"])}/renders/{esc(e["film"])}__master.mp4">'
                     f'{esc(film["title"])}</a> — {esc(film["thesis"].strip())}</dd>')
    facts_used = "; ".join(f"{esc(f)} = <code>{esc(json.dumps(facts[f]['value']))}</code> ({esc(facts[f]['kind'])})"
                           for f in e["expected_facts"])
    agree = issue_url(e["report_agree"]["template"], {**e["report_agree"]["prefill"],
                      "title": f"Reproduction: {e['id']} — match", "outcome": "Match — exit 0, final line matched the page's expected output"}
                      if e["report_agree"]["template"] == "reproduction.yml" else e["report_agree"]["prefill"])
    disagree = issue_url(e["report_disagree"]["template"], {**e["report_disagree"]["prefill"],
                         "title": f"Reproduction: {e['id']} — mismatch", "outcome": "Mismatch — a FAIL line, a different count, or a nonzero exit"}
                         if e["report_disagree"]["template"] == "reproduction.yml" else e["report_disagree"]["prefill"])
    claims = ", ".join(f'<a class="u" href="/ledger/#{esc(c)}">{esc(c)}</a>' for c in e["claims"])
    return f'''
    <article class="exp" id="{anchor}" aria-labelledby="{anchor}-h">
      <h3 id="{anchor}-h">{esc(e["title"])}</h3>
      <p class="meta mono">{esc(e["id"])} · about {e["minutes"]} minute{"s" if e["minutes"] != 1 else ""} · claims {claims}</p>
      <dl>
        <dt>Question</dt><dd class="ink">{esc(e["question"])}</dd>
        <dt>Needs</dt><dd>{esc(e["input"])}</dd>
        <dt>Run</dt><dd><pre><code>git clone https://github.com/Cubits11/cubits11.github.io.git &amp;&amp; cd cubits11.github.io
{esc(e["command"])}</code></pre></dd>
        <dt>Variant</dt><dd><code>{esc(e["variant"])}</code></dd>
        <dt>Expected</dt><dd class="ink">final line: <code>{esc(e["expected_final_line"])}</code></dd>
        <dt>Bound to</dt><dd>{facts_used}</dd>
        <dt>Status</dt><dd>{esc(e["epistemic_status"])}</dd>
        <dt>Falsifier</dt><dd>{esc(e["falsifier"])}</dd>
        <dt>Non-claim</dt><dd>{esc(e["non_claim"])}</dd>
        {film_line}
      </dl>
      <div class="row">
        {a(disagree, "I got a different result", True)}
        {a(agree, "It matched — record it")}
        {a(e["deeper"], "Go deeper")}
      </div>
    </article>'''


def render(data: dict, ledger: dict, facts: dict, counts: dict) -> str:
    q = ledger["qualified"]
    films = {}
    for m in sorted(ROOT.glob("films/*/manifest.yaml")):
        d = yaml.safe_load(m.read_text())
        films[d["id"]] = d
    title = "Try it: reproduce the missing column in 60 seconds, 3 minutes, or 15"
    desc = ("Three experiments anyone can run in 60 seconds, 3 minutes, or 15: two worlds from the same "
            "guardrail scores, a released file recomputed, an evaluation audited. Commands, expected "
            "results, falsifiers.")
    path = "/try/"
    head = page_head(title, desc, path, CSS, jsonld=jsonld_script({
        "@context": "https://schema.org", "@type": "WebPage", "name": title, "description": desc,
        "url": f"{SITE}{path}", "inLanguage": "en"}))
    crumbs = breadcrumbs(("The record", "/"), ("Try it", None))
    exps = "".join(render_experiment(e, facts, films) for e in data["experiments"])
    fs = fact_registry.fact_span
    n, k, absent, m3 = counts["N"], counts["K"], counts["by_classification"].get("ABSENT", 0), counts["M_strata"]["threshold_documented_full_exposure"]
    rows = "".join(f'<tr><td>{esc(b.replace("_", " "))}</td><td>{len(q[b])}</td></tr>' for b in outcomes_ledger.QUALIFIED_BUCKETS)
    interactions = ledger["diagnostics"]["technical_interactions"]
    trials = len(ledger["diagnostics"].get("cold_comprehension_trials", []))
    same = films.get("same-scores-different-worlds", {})
    return head + f'''
<div class="class-bar mono">
  <div class="container">
    <span><b>Try it</b> — three experiments, each with its command, expected result, and falsifier</span>
    <span>a result, not a compliment</span>
  </div>
</div>
<header class="page">
  <div class="container">
    {crumbs}
    <h1 class="try-hero">DON'T TRUST THE GRAPHIC.<br><b>REPRODUCE IT.</b></h1>
    <p class="q">{esc(data["question"])} Below: a 60-second proof, a 3-minute reconstruction from a public file, and a 15-minute audit you can run on an evaluation you know. Each says what it needs, what it should print, what would prove it wrong, and what it does not claim — before you run anything.</p>
  </div>
</header>
<main class="container" id="main">
  <section class="zone" id="film" aria-labelledby="film-h" style="margin-top:0;border-top:none;padding-top:0">
    <h2 id="film-h">Thirty seconds, sound off</h2>
    <div class="film">
      <video controls preload="none" playsinline poster="/films/same-scores-different-worlds/renders/same-scores-different-worlds__master.poster.png" aria-label="Same Scores, Different Worlds — a 30-second film">
        <source src="/films/same-scores-different-worlds/renders/same-scores-different-worlds__master.mp4" type="video/mp4">
      </video>
      <div>
        <p><strong>{esc(same.get("title", "Same Scores, Different Worlds"))}.</strong> {esc(same.get("thesis", "").strip())}</p>
        <p class="mono" style="color:var(--muted);font-size:.8rem">Every number in the film is read from the claim registry; the film's manifest and render receipt are in <a class="u" href="https://github.com/Cubits11/cubits11.github.io/tree/main/films/same-scores-different-worlds">films/same-scores-different-worlds/</a>. Don't trust the animation. Run it: experiment A is the same construction as a script.</p>
      </div>
    </div>
  </section>

  <section class="zone" id="experiments" aria-labelledby="exp-h">
    <h2 id="exp-h">Three experiments</h2>
    {exps}
  </section>

  <section class="zone" id="status" aria-labelledby="status-h">
    <h2 id="status-h">External status</h2>
    <div class="status">
      <p class="mono" style="margin:0 0 .6rem;color:var(--muted);font-size:.78rem;letter-spacing:.06em">QUALIFIED OUTCOMES — work done by someone who is not the author · bound to distribution/outcomes.yaml</p>
      <table>{rows}</table>
      <p class="diag">Diagnostics, kept apart and never counted as outcomes: technical interactions {interactions}; blinded comprehension trials {trials}. Zero is the recorded value. Be the first independent rerun → <a class="u" href="#try-a">experiment A</a>.</p>
    </div>
  </section>

  <section class="zone" id="report" aria-labelledby="report-h">
    <h2 id="report-h">Report what you found</h2>
    <p class="zone-intro">Prefilled forms, no vocabulary required. A different result is the most useful thing you can send; it is placed beside the claim it disagrees with, dated, and credited if you want it to be.</p>
    <div class="routes">
      <a href="{esc(issue_url("reproduction.yml", {"title": "Reproduction: <experiment> — match", "outcome": "Match — exit 0, final line matched the page's expected output"}))}">I reproduced it<span>match — becomes the claim's independent-reproduction record</span></a>
      <a href="{esc(issue_url("reproduction.yml", {"title": "Reproduction: <experiment> — mismatch", "outcome": "Mismatch — a FAIL line, a different count, or a nonzero exit"}))}">I got a different result<span>handled as a correction the same day</span></a>
      <a href="{esc(issue_url("counterexample.yml", {"kind": "I found a counterexample to a registered claim"}))}">I found a counterexample<span>to a claim, a bound, or a classification</span></a>
      <a href="{esc(issue_url("counterexample.yml", {"kind": "I found a benchmark that already reports the stack (a row the census should have as PRESENT)"}))}">A benchmark already reports this<span>the census would count it PRESENT</span></a>
      <a href="{esc(issue_url("counterexample.yml", {"kind": "I can provide item-level or joint outcomes for an evaluation"}))}">I can provide joint outcomes<span>ids and bits are enough; no prompt text</span></a>
      <a href="https://github.com/Cubits11/cubits11.github.io/compare">I want to contribute a patch<span>the pull-request template is three lines</span></a>
    </div>
  </section>

  <section class="zone" id="counterexample" aria-labelledby="cx-h">
    <h2 id="cx-h">Bring a counterexample</h2>
    <p class="zone-intro">This is an open research problem with a correction path, not a request for help. The census examined {fs("MC-001.N", n)} public evaluations: {fs("MC-001.K", k)} preserve a joint-evidence artifact, {fs("MC-001.ABSENT", absent)} report none, and {fs("MC-001.M3", m3)} document matched operating thresholds with full exposure. Each of the following would update the programme and be recorded with the prominence of the claim it changes:</p>
    <ul class="ladder">
      <li>an evaluation that meets the frozen criteria, was public on or before 2026-08-27, and is missing — the count changes (it has changed once already);</li>
      <li>a row whose source contradicts its recorded fields — the row is corrected, dated, in the public file;</li>
      <li>joint evidence for any examined evaluation — union, all-miss, leave-one-out, or aligned per-item outcomes — the row moves to PRESENT;</li>
      <li>a narrower identified region for a registered bound, or a joint law that escapes one — the claim is narrowed or rejected under its registered falsifier;</li>
      <li>a supposed missing column that is already present — the strongest kind of correction.</li>
    </ul>
    <div class="row" style="display:flex;flex-wrap:wrap;gap:.7rem;margin-top:1.1rem">
      {a(issue_url("counterexample.yml", {}), "Bring it", True)}
      {a("/missing-column/", "Read the census")}
      {a("/corrections/", "How corrections are handled")}
    </div>
  </section>

  <section class="zone" id="deeper" aria-labelledby="deeper-h">
    <h2 id="deeper-h">Depth on demand</h2>
    <ol class="ladder">
      <li>2 seconds — the poster above: same scores, different worlds.</li>
      <li>30 seconds — the film, sound off.</li>
      <li>60 seconds — experiment A, the same construction as a script.</li>
      <li>3 minutes — experiment B, a released file recomputed under a hash.</li>
      <li>15 minutes — experiment C, the disclosure test on an evaluation you know.</li>
      <li>the explanation — <a class="u" href="/answers/why-guardrail-miss-rates-do-not-multiply/">why miss rates do not multiply</a> · <a class="u" href="/answers/what-does-the-second-guardrail-add/">what the second guard adds</a>.</li>
      <li>the essay — <a class="u" href="/essays/when-marginals-are-not-enough/">when marginals are not enough</a>.</li>
      <li>the record — <a class="u" href="/missing-column/">the census</a> · <a class="u" href="/ledger/">every claim with its falsifier</a> · <a class="u" href="https://github.com/Cubits11/cubits11.github.io">the repository</a>.</li>
    </ol>
  </section>
</main>''' + PAGE_FOOT


def main() -> int:
    data = yaml.safe_load((ROOT / "distribution" / "experiments.yaml").read_text())
    ledger = outcomes_ledger.load()
    facts = json.loads((ROOT / "films" / "data" / "facts.json").read_text())["facts"]
    counts = verify_census.compute_counts(verify_census.load())
    html = render(data, ledger, facts, counts)
    if "--check" in sys.argv:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != html:
            print("DRIFT: try/index.html does not match its generator. Run: python3 scripts/generate_try.py")
            return 1
        print("ok    /try/ matches experiments.yaml, outcomes.yaml and the bound facts")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote try/index.html ({len(html)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
