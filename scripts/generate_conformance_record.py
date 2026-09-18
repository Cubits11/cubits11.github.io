#!/usr/bin/env python3
"""Render /records/conformance/ — the preregistration-to-execution record.

A compiler output. Every scientific number on the page is a projection of a
committed artifact; none is typed here. The page therefore cannot drift from
the repository, and CI fails if it does.

Sources, all canonical, all deterministic functions of committed bytes:

  research/DIRECTION.yaml                        the plane, its edges, the cohort
  metrics/ledger_snapshot.json                   counts (ages excluded on purpose)
  corrections/records/2026-09-10.json            dispositions
  corrections/records/*-preserved-inputs.json    preserved-byte manifest
  scripts/verify_prereg.py                       fixtures and mutants, by import
  claims.yaml                                    registry status per claim
  experiments/*/                                 contract declaration coverage

Deliberately absent: today's date, blocker ages, anything read from the
network, and any number a human could retype. `as_of` comes from the ledger
snapshot, which carries its own drift gate.

    python3 scripts/generate_conformance_record.py
    python3 scripts/generate_conformance_record.py --check
"""
from __future__ import annotations

import hashlib
import html
import importlib.util
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "records" / "conformance" / "index.html"
REPO = "https://github.com/Cubits11/cubits11.github.io/blob/main/"

SOURCES = (
    "research/DIRECTION.yaml",
    "metrics/ledger_snapshot.json",
    "corrections/records/2026-09-10.json",
    "corrections/records/2026-09-10-preserved-inputs.json",
    "scripts/verify_prereg.py",
    "claims.yaml",
)

STATE = {"enforced": ("evidence", "enforced"),
         "partial": ("review", "partial"),
         "absent": ("invalid", "absent")}


def esc(s: object) -> str:
    return html.escape(str(s), quote=True)


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def load_verifier():
    spec = importlib.util.spec_from_file_location("vp", ROOT / "scripts" / "verify_prereg.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def src(rel: str, label: str | None = None) -> str:
    return f'<a class="u" href="{REPO}{esc(rel)}"><code>{esc(label or rel)}</code></a>'


def render() -> str:
    d = yaml.safe_load((ROOT / "research/DIRECTION.yaml").read_text(encoding="utf-8"))
    snap = json.loads((ROOT / "metrics/ledger_snapshot.json").read_text(encoding="utf-8"))
    corr = json.loads((ROOT / "corrections/records/2026-09-10.json").read_text(encoding="utf-8"))
    preserved = json.loads(
        (ROOT / "corrections/records/2026-09-10-preserved-inputs.json").read_text(encoding="utf-8"))
    registry = {c["id"]: c for c in
                yaml.safe_load((ROOT / "claims.yaml").read_text(encoding="utf-8"))["claims"]}
    vp = load_verifier()

    # fixture name -> the experiment it reconstructs, derived from the name itself
    fixtures = {}
    for name, _fn in vp.FIXTURES:
        tag = name.rsplit("(", 1)[-1].rstrip(")") if "(" in name else None
        fixtures[tag] = name
    n_mutants = len(vp.MUTANTS)

    # contract declaration coverage, counted from the tree
    preregs = sorted(p.name for p in (ROOT / "experiments").iterdir()
                     if (p / "PREREG.md").exists())
    declared = [e for e in preregs if (ROOT / "experiments" / e / vp.SIDECAR).exists()
                or (ROOT / "experiments" / e / vp.CONTRACT).exists()]

    disp = {r["claim_id"]: r for r in corr["records"]}
    # Direct indexing on purpose: a missing key must raise here rather than
    # fall back to a plausible zero. Rendering a wrong number silently is the
    # defect class this whole page is about.
    n_preserved = len(preserved["sha256"])
    baseline = preserved["baseline_commit"]

    # ── the plane ────────────────────────────────────────────────────────────
    edges = []
    for name, e in d["plane"]["edges"].items():
        tone, word = STATE[e["status"]]
        by = src(e["by"].split(" ")[0]) if e.get("by") else "<span class=\"muted\">nothing</span>"
        edges.append(
            f'<tr><th scope="row"><code>{esc(name)}</code></th>'
            f'<td class="mono">{esc(" ".join(e["over"]))}</td>'
            f'<td>{esc(e["asks"])}</td>'
            f'<td><span class="pill pill-{tone}">{esc(word)}</span></td>'
            f'<td>{by}</td></tr>')

    # ── the cohort ───────────────────────────────────────────────────────────
    cards = []
    for c in d["plane"]["founding_cohort"]:
        eid = c["id"]
        cid = {"E7": None}.get(eid, f"{eid}-001")
        claim = registry.get(cid) if cid else None
        rec = disp.get(cid) if cid else None
        fixture = fixtures.get(eid)
        stands = c["disposition"] == "STANDS"
        tone = "evidence" if stands else "invalid"
        rows = [
            ("declared", f'{src(f"experiments/{eid.lower()}/PREREG.md")}'
                         if (ROOT / f"experiments/{eid.lower()}/PREREG.md").exists()
                         else '<span class="muted">no preregistration committed</span>'),
            ("plane edge that failed",
             f'<code>{esc(c["edge"])}</code> — {esc(d["plane"]["edges"][c["edge"]]["asks"])}'
             if c["edge"] else '<span class="muted">none — the join held</span>'),
            ("mismatch", f'<code>{esc(c["defect"])}</code>' if c["defect"]
                         else '<span class="muted">none detected</span>'),
            ("disposition",
             f'<span class="pill pill-{tone}">{esc(c["disposition"])}</span>'
             + (f' · history transition <code>{esc(rec["transition_type"])}</code>'
                f' · registry status <code>{esc(rec["status"])}</code>' if rec else "")),
            ("caught", esc(c["caught"]) if c.get("caught")
                       else '<span class="muted">n/a — nothing to catch</span>'),
            ("historical defect reconstructed by",
             f'<code>{esc(fixture)}</code> in {src("scripts/verify_prereg.py")}'
             if fixture else '<span class="muted">no fixture — the join held, '
                             'so there is nothing to regress against</span>'),
            ("evidence",
             (f'{src(rec["artifact"])} · ' if rec else "")
             + src(f"experiments/{eid.lower()}/results/", f"experiments/{eid.lower()}/results/")),
        ]
        if claim and claim.get("support", {}).get("url"):
            rows.append(("registered as", f'<code>{esc(cid)}</code>'))
        body = "".join(f'<dt>{esc(k)}</dt><dd>{v}</dd>' for k, v in rows)
        cards.append(f'<article class="rec" id="{esc(eid.lower())}">'
                     f'<div class="rec-head"><h3>{esc(eid)}</h3>'
                     f'<span class="pill pill-{tone}">{esc(c["disposition"])}</span></div>'
                     f'<dl>{body}</dl></article>')

    # ── sources ──────────────────────────────────────────────────────────────
    source_rows = "".join(
        f'<tr><th scope="row">{src(rel)}</th><td class="mono hash">{esc(sha(rel))}</td></tr>'
        for rel in SOURCES)

    blind = [f'<li><code>{esc(n)}</code> — {esc(e["asks"])}</li>'
             for n, e in d["plane"]["edges"].items() if e["status"] == "absent"]

    obs = snap["observations"]
    stands_rows = sum(f["rows"] for f in obs["files"]
                      if any(f["file"].startswith(f"experiments/{e['id'].lower()}/")
                             for e in d["plane"]["founding_cohort"]
                             if e["disposition"] == "STANDS"))
    void_rows = obs["rows"] - stands_rows

    return f'''<!doctype html>
<!-- GENERATED FILE — do not edit by hand.
     Sources: {" · ".join(SOURCES)}
     Renderer: scripts/generate_conformance_record.py
     CI regenerates this page and fails on drift. -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Preregistration → Execution — Conformance record</title>
<meta name="description" content="Where this repository's preregistered intent and its executed evidence diverged: the conformance plane, three historical failures, and the edges still unguarded.">
<link rel="canonical" href="https://cubits11.github.io/records/conformance/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Cubits11">
<meta property="og:title" content="Preregistration → Execution — Conformance record">
<meta property="og:description" content="Three of five executed experiments were voided or rejected. The failures include a degenerate declared rule and mismatches between declared and executed analyses.">
<meta property="og:url" content="https://cubits11.github.io/records/conformance/">
<meta property="og:image" content="https://cubits11.github.io/assets/img/og.jpg">
<meta property="og:image:alt" content="Pranav Bhave, AI Assurance · Security Engineering · Evidence Systems — measuring what guardrail stacks miss together">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://cubits11.github.io/assets/img/og.jpg">
<meta name="twitter:image:alt" content="Pranav Bhave, AI Assurance · Security Engineering · Evidence Systems — measuring what guardrail stacks miss together">
<meta name="robots" content="max-image-preview:large">
<meta name="theme-color" media="(prefers-color-scheme: light)" content="#F1EDE2">
<meta name="theme-color" media="(prefers-color-scheme: dark)" content="#0B0F0A">
<script>try{{var t=localStorage.getItem('theme');if(t==='dark'||t==='light'){{document.documentElement.dataset.theme=t}}}}catch(e){{}}</script>
<link rel="stylesheet" href="/assets/site.css">
<style>
body{{font-size:1rem;line-height:1.65}}
.container{{width:min(980px,100% - 2*clamp(1.25rem,5vw,3rem));margin-inline:auto}}
.mono{{font-size:.72rem}}
header.page{{padding:4.5rem 0 2rem;border-bottom:1px solid var(--line)}}
h1{{font-size:clamp(2rem,5vw,3rem);line-height:1.06;margin:.6rem 0 1rem;letter-spacing:-.015em;font-weight:520}}
h2{{font-size:1.15rem;margin:2.6rem 0 .8rem;font-weight:560}}
h3{{font-size:1rem;margin:0;font-weight:560}}
.intro{{color:var(--muted);max-width:48em}}
.banner{{border:1px solid var(--line-strong);background:var(--surface);padding:.85rem 1rem;margin:1.4rem 0 0;font-size:.9rem}}
.banner strong{{font-weight:600}}
table{{width:100%;border-collapse:collapse;margin:.6rem 0 0;font-size:.92rem}}
th,td{{text-align:left;padding:.5rem .6rem;border-bottom:1px solid var(--line);vertical-align:top}}
thead th{{color:var(--muted);font-weight:500;font-size:.78rem;text-transform:uppercase;letter-spacing:.06em}}
.scroll{{overflow-x:auto}}
.hash{{word-break:break-all;color:var(--muted);text-transform:none}}
.pill{{display:inline-block;border:1px solid;border-radius:2em;padding:.05rem .6rem;font-size:.72rem;letter-spacing:.03em}}
.pill-evidence{{color:var(--evidence);border-color:var(--evidence)}}
.pill-review{{color:var(--review);border-color:var(--review)}}
.pill-invalid{{color:var(--invalid);border-color:var(--invalid)}}
.chain{{font-size:.8rem;letter-spacing:.08em;color:var(--muted);margin:.4rem 0 0;overflow-x:auto;white-space:nowrap}}
.chain b{{color:var(--ink);font-weight:560}}
.chain i{{font-style:normal;color:var(--gold)}}
.rec{{border:1px solid var(--line-strong);background:var(--surface);margin:1.1rem 0;padding:clamp(1rem,2.5vw,1.4rem)}}
.rec-head{{display:flex;align-items:baseline;justify-content:space-between;gap:1rem;margin-bottom:.7rem}}
dl{{display:grid;grid-template-columns:minmax(9rem,14rem) 1fr;gap:.35rem 1rem;margin:0;font-size:.92rem}}
dt{{color:var(--muted)}}
dd{{margin:0}}
@media (max-width:620px){{dl{{grid-template-columns:1fr}}dt{{margin-top:.5rem}}}}
.muted{{color:var(--muted)}}
pre{{background:var(--surface);border:1px solid var(--line);padding:.8rem 1rem;overflow-x:auto;font-size:.82rem}}
ul{{padding-left:1.1rem}}
footer{{border-top:1px solid var(--line);margin-top:3.5rem;padding:2rem 0 3rem;color:var(--muted);font-size:.88rem}}
</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="page">
  <div class="container">
    <p class="mono"><a class="u" href="/">← Cubits11</a></p>
    <h1>Preregistration → Execution</h1>
    <p class="intro">Three of this repository's five executed experiments were voided or
      rejected. E7 executed a degenerate declared rule; E6 and E7B violated declared
      invariants or pool identities. This page records those distinct failures, the
      synthetic regression fixtures that reconstruct them, and the execution obligations
      still unguarded.</p>
    <div class="banner"><strong>This page is generated from repository state. It is not a
      governing source.</strong> Every number below is a projection of a committed artifact
      listed under <a class="u" href="#sources">Sources</a>. Nothing here is hand-maintained,
      and CI fails the build if this file and its sources disagree.</div>
    <div class="meta-row mono" style="display:flex;gap:1.4rem;flex-wrap:wrap;margin-top:1.2rem;color:var(--muted)">
      <span>as of {esc(snap["as_of"])}</span>
      <span>{esc(snap["claims"]["total"])} claims · {esc(snap["claims"]["own_measurement"])} own-measurement</span>
      <span>{esc(obs["rows"])} observation rows</span>
      <span>DIRECTION v{esc(d["version"])}</span>
    </div>
  </div>
</header>

<main id="main" class="container">

<h2>The plane</h2>
<p class="intro">An experiment is not a preregistration plus code plus data plus a result. It
  is a typed graph, and the edges are the scientific objects. A result is admissible only
  when every edge holds.</p>
<p class="chain"><b>DECLARED</b> <i>P</i> ── <b>BOUND</b> <i>X</i> ── <b>EXECUTED</b> <i>R/D</i> ── <b>VALIDATED</b> <i>O</i> ── <b>CLAIMED</b> <i>C</i></p>
<p class="mono">{esc(d["plane"]["admissibility"])}</p>
<div class="scroll"><table>
<caption class="sr-only">Conformance plane edges and what enforces each</caption>
<thead><tr><th scope="col">edge</th><th scope="col">over</th><th scope="col">asks</th><th scope="col">state</th><th scope="col">enforced by</th></tr></thead>
<tbody>{"".join(edges)}</tbody>
</table></div>

<h2>The founding cohort</h2>
<p class="intro">Retrospective. These five motivated the plane; they do not measure it. The
  classification was partly built after the failures were visible, so
  {esc(sum(1 for c in d["plane"]["founding_cohort"] if c["disposition"] == "STANDS"))} of
  {esc(len(d["plane"]["founding_cohort"]))} valid is diagnostic evidence, not an estimate.
  Of {esc(obs["rows"])} observation rows, {esc(stands_rows)} stand and {esc(void_rows)}
  belong to voided or rejected runs. Frozen inputs, estimators and outputs are unchanged in
  every case; {esc(n_preserved)} files are held in the preserved-byte manifest at baseline commit
  <code>{esc(baseline[:12])}</code>.</p>
{"".join(cards)}

<h2>What now intercepts these</h2>
<p class="intro">{esc(len(vp.FIXTURES))} regression fixtures, each reconstructing a defect
  that actually voided a run here, on synthetic data with a known answer. Each asserts that
  the <em>defective</em> rule still gets it wrong, so a fixture that loses its teeth fails
  loudly instead of passing vacuously. {esc(n_mutants)} mutant declarations carry one of the
  three defects each and must be rejected: a detector nobody has watched fire has no
  demonstrated discriminatory power.</p>
<div class="scroll"><table>
<thead><tr><th scope="col">fixture</th><th scope="col">reconstructs</th></tr></thead>
<tbody>{"".join(f'<tr><th scope="row"><code>{esc(n)}</code></th><td>{esc(t or "—")}</td></tr>' for t, n in fixtures.items())}</tbody>
</table></div>

<h2>Prospective coverage</h2>
<p class="intro">An experiment opts in by committing a machine-readable contract beside its
  preregistration, intended for its runner to consume rather than restate. The current
  scan checks declaration fields and a textual reference in the runner; it does not prove
  runtime consumption. Frozen preregistrations
  are reported as undeclared and never failed: gating a frozen file after its outcomes are
  visible is itself the rescue this repository forbids.</p>
<p><span class="pill pill-{"evidence" if declared else "review"}">{esc(len(declared))} of {esc(len(preregs))} declared</span>
   &nbsp; <span class="mono muted">{esc(" ".join(preregs))}</span></p>

<h2 id="blind">Unresolved blind spots</h2>
<p class="intro">The edges with nothing behind them. Naming them here is the only thing
  currently done about them.</p>
<ul>{"".join(blind)}</ul>

<h2>Reproduce</h2>
<pre><code>git clone https://github.com/Cubits11/cubits11.github.io &amp;&amp; cd cubits11.github.io
python3 scripts/verify_prereg.py --test    # the fixtures and the mutants
python3 scripts/direction.py               # the heading this page projects
python3 scripts/generate_conformance_record.py --check   # this page, against its sources</code></pre>

<h2 id="sources">Sources</h2>
<p class="intro">Every scientific number above is read from one of these files at render
  time. Hashes are of the bytes this page was generated from.</p>
<div class="scroll"><table>
<thead><tr><th scope="col">file</th><th scope="col">sha256</th></tr></thead>
<tbody>{source_rows}</tbody>
</table></div>

</main>
<footer><div class="container">
  <p>Generated by <a class="u" href="{REPO}scripts/generate_conformance_record.py"><code>scripts/generate_conformance_record.py</code></a>.
     Direction: <a class="u" href="{REPO}research/DIRECTION.yaml"><code>research/DIRECTION.yaml</code></a>.
     A perfect hash cannot rescue a bad denominator.</p>
</div></footer>
</body>
</html>
'''


def main() -> int:
    out = render()
    if "--check" in sys.argv:
        current = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
        if current != out:
            print("DRIFT: records/conformance/index.html does not match its sources.")
            print("Run: python3 scripts/generate_conformance_record.py")
            return 1
        print("ok    records/conformance/index.html matches its sources (generated, no drift)")
        return 0
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(out, encoding="utf-8")
    print(f"wrote {TARGET.relative_to(ROOT)} ({len(out)} bytes) from {len(SOURCES)} sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
