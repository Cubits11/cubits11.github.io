#!/usr/bin/env python3
"""Generate /observatory/ from claims.yaml.

The observatory is a second view of the same registry the ledger renders —
the Claim Observatory vocabulary of CC-Framework's visual identity
translated into accessible 2D web primitives:

  claim capsule   — one article per claim, proposition as the object
  evidence slab   — the binding (repo @ sha) attached as a cyan chip
  support binding — the capsule's rail links straight into /ledger/#ID
  decay clock     — a ring per capsule, drawn by JS from last_reviewed and
                    review_window_days (amber past 75% of the window, red
                    past expiry); the dates are always present as text, so
                    no-JS and screen-reader users lose nothing
  non-claims wall — every non-claim in the registry, one explicit boundary
  falsifier wall — every defeat condition, fixed consequence, and forbidden
                    post-falsification rescue in the registry
  replay manifest — the exact commands that re-verify this record
  human review    — what stays manual, said plainly

No aggregate health score is computed anywhere: counts are per-status
labels, and a quiet trigger is "quiet", never "healthy".

CI runs `generate_observatory.py --check` and fails on drift.
"""

import pathlib
import re
import sys

import yaml

import generate_ledger as ledger

ROOT = pathlib.Path(__file__).resolve().parent.parent

esc = ledger.esc
label = ledger.label


def status_pill_class(status: str) -> str:
    if status in ("inconclusive", "contradicted"):
        return "status-hot"
    if status == "untested":
        return "status-dim"
    return "status"


# The research object's own state, printed apart from the claim's evidential
# status. A claim can be fully supported about a document whose study has
# produced nothing; these two facts must not share a pill.
STUDY_STATE_LABELS = {
    "not_started": "NOT STARTED",
    "untested": "UNTESTED",
    "not_activated": "NOT ACTIVATED",
    "dry_run_only": "DRY RUN ONLY",
    "in_collection": "IN COLLECTION",
    "complete": "COMPLETE",
}


def study_state_html(c: dict) -> str:
    block = c.get("study_state")
    if not block:
        return ""
    state = str(block.get("state", ""))
    return (
        f'<div class="study-state" data-study-state-for="{esc(c["id"])}" '
        f'data-study-state="{esc(state)}">'
        f'<span class="mono study-state-label">Study · {esc(block.get("object", ""))}'
        f'</span> <span class="mono study-state-pill">'
        f'{esc(STUDY_STATE_LABELS.get(state, state.upper()))}</span>'
        f'<p class="study-state-note">{esc(" ".join(str(block.get("note", "")).split()))}</p>'
        f'</div>')


def render_capsule(c: dict) -> str:
    d = c["dimensions"]
    sup = c.get("support") or {}
    falsifier = c["falsifier"]
    url, commit = sup.get("url"), sup.get("commit")
    if url and commit:
        slab = (f'<a class="chip" href="{esc(url)}">'
                f'{esc(url.split("github.com/")[-1].split("/")[1])} @ '
                f'{esc(str(commit)[:8])} ↗</a>')
    elif url:
        slab = f'<a class="chip" href="{esc(url)}">bound document ↗</a>'
    else:
        slab = ('<span class="chip chip-attested">attested — no public artifact'
                '<span class="sr-only"> — stated on the owner\'s responsibility'
                '</span></span>')
    trig_tags = "".join(
        f'<span class="mono tag {"tag-exec" if t.get("enforcement") == "executable" else "tag-manual"}">'
        f'{esc(t.get("enforcement", "manual"))}</span>'
        for t in c.get("review_triggers", []))
    nc_n = len(c.get("non_claims", []))
    rescue_n = len(c["forbidden_rescues"])
    prop = re.sub(r"\s+", " ", str(c["proposition"]).strip())
    attested = "" if url else " capsule-attested"
    return f'''
  <article class="capsule{attested}" data-reviewed="{esc(c["last_reviewed"])}" data-window="{esc(c["review_window_days"])}">
    <div class="cap-head">
      <h2 class="mono cap-id">{esc(c["id"])}</h2>
      <span class="mono {status_pill_class(d["evidential_status"])}">{esc(label(d["evidential_status"]))}</span>
      <span class="clock" aria-hidden="true"><svg viewBox="0 0 36 36"><circle class="clock-track" cx="18" cy="18" r="15.5"/><circle class="clock-arc" cx="18" cy="18" r="15.5"/></svg></span>
    </div>
    <p class="cap-prop">{esc(prop)}</p>
    {study_state_html(c)}
    <div class="cap-slabs">{slab}</div>
    <div class="cap-meta mono">
      <span>{esc(label(d["provenance"]))} · {esc(label(d["maturity"]))}</span>
      <span>reviewed {esc(c["last_reviewed"])} · window {esc(c["review_window_days"])}d<span class="clock-days"></span></span>
      <span>falsifier consequence: {esc(falsifier["consequence"])} · {rescue_n} forbidden rescue{"s" if rescue_n != 1 else ""}</span>
      <span class="cap-tags">{trig_tags}</span>
    </div>
    <div class="cap-foot mono">
      <a class="u" href="/ledger/#{esc(c["id"])}">open the envelope →</a>
      <a class="u" href="#challenge-{esc(c["id"])}">falsifier → {esc(falsifier["consequence"])}</a>
      <a class="u" href="#wall-{esc(c["id"])}">{nc_n} non-claim{"s" if nc_n != 1 else ""}</a>
    </div>
  </article>'''


def render_wall(claims: list[dict]) -> str:
    rows = []
    for c in claims:
        items = "".join(f"<li>{esc(n)}</li>" for n in c.get("non_claims", []))
        rows.append(f'<div class="wall-row" id="wall-{esc(c["id"])}">'
                    f'<span class="mono wall-id">{esc(c["id"])}</span>'
                    f'<ul>{items}</ul></div>')
    return "".join(rows)


def render_challenge_wall(claims: list[dict]) -> str:
    rows = []
    for c in claims:
        falsifier = c["falsifier"]
        rescues = c["forbidden_rescues"]
        if rescues:
            rescues_html = "".join(f"<li>{esc(rescue)}</li>" for rescue in rescues)
            rescues_html = f'<ul>{rescues_html}</ul>'
        else:
            rescues_html = ('<p class="empty-rescues"><code>[]</code> — no meaningful '
                            'post-falsification rescue is declared.</p>')
        rows.append(
            f'<div class="wall-row challenge-row" id="challenge-{esc(c["id"])}">'
            f'<span class="mono wall-id">{esc(c["id"])}</span>'
            f'<div class="challenge-content">'
            f'<p><span class="mono challenge-label">Falsifier</span>{esc(falsifier["condition"])}</p>'
            f'<p><span class="mono challenge-label">Consequence</span>'
            f'<span class="challenge-consequence mono">{esc(falsifier["consequence"])}</span></p>'
            f'<p class="mono challenge-label rescue-label">Forbidden rescues</p>{rescues_html}'
            f'</div></div>'
        )
    return "".join(rows)


def render(registry: dict) -> str:
    claims = registry["claims"]
    n = len(claims)
    version = esc(registry["version"])
    reviewed = esc(registry["last_owner_review"])
    by_status: dict = {}
    for c in claims:
        s = c["dimensions"]["evidential_status"]
        by_status[s] = by_status.get(s, 0) + 1
    status_line = " · ".join(f"{v} {esc(label(k)).lower()}"
                             for k, v in sorted(by_status.items()))
    capsules = "".join(render_capsule(c) for c in claims)
    wall = render_wall(claims)
    challenge_wall = render_challenge_wall(claims)
    manual_events = []
    for c in claims:
        for t in c.get("review_triggers", []):
            if t.get("enforcement") == "manual":
                manual_events.append(f'<li><span class="mono">{esc(c["id"])}</span> — '
                                     f'{esc(t.get("event") or t.get("type"))}</li>')
    title = "Claim Observatory — Pranav Bhave"
    desc = ("The claim registry as one field: capsules, evidence bindings, decay "
            "clocks, non-claims, falsifiers, and forbidden rescues — every boundary visible, no "
            "aggregate score anywhere.")
    return f'''<!doctype html>
<!-- GENERATED FILE — do not edit by hand.
     Source: claims.yaml · renderer: scripts/generate_observatory.py
     CI regenerates this page and fails on drift. -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="https://cubits11.github.io/observatory/">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="https://cubits11.github.io/observatory/">
<meta property="og:image" content="https://cubits11.github.io/assets/img/og.jpg">
<meta property="og:image:alt" content="Pranav Bhave, AI Assurance · Security Engineering · Evidence Systems — measuring what guardrail stacks miss together">
<meta name="twitter:image:alt" content="Pranav Bhave, AI Assurance · Security Engineering · Evidence Systems — measuring what guardrail stacks miss together">
<meta property="og:site_name" content="Cubits11">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://cubits11.github.io/assets/img/og.jpg">
<meta name="robots" content="max-image-preview:large">
<meta name="theme-color" media="(prefers-color-scheme: light)" content="#F1EDE2">
<meta name="theme-color" media="(prefers-color-scheme: dark)" content="#0B0F0A">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%230B0F0A'/%3E%3Crect x='12' y='11' width='17' height='17' rx='4' fill='%23EDE8DA'/%3E%3Crect x='35' y='11' width='17' height='17' rx='4' fill='%23EDE8DA'/%3E%3Crect x='12' y='32' width='17' height='17' rx='4' fill='%23EDE8DA'/%3E%3Crect x='35' y='32' width='17' height='17' rx='4' fill='%23EDE8DA'/%3E%3Crect x='13.5' y='53' width='37' height='0.1' rx='2' fill='none' stroke='%23C9A15E' stroke-width='3'/%3E%3C/svg%3E">
<script>try{{var t=localStorage.getItem('theme');if(t==='dark'||t==='light'){{document.documentElement.dataset.theme=t;var m=document.querySelectorAll('meta[name="theme-color"]');for(var i=0;i<m.length;i++)m[i].content=t==='dark'?'#0B0F0A':'#F1EDE2'}}}}catch(e){{}}</script>
<link rel="stylesheet" href="/assets/site.css">
<style>
body{{font-size:1rem;line-height:1.65}}
.container{{width:min(1060px,100% - 2*clamp(1.25rem,5vw,3rem))}}
.mono{{font-size:.68rem}}
header.page{{padding:7.9rem 0 2.4rem}}
h1{{font-weight:520;font-size:clamp(2.4rem,6vw,3.8rem);line-height:1.04;margin:0 0 1rem;letter-spacing:-.018em}}
.intro{{color:var(--muted);max-width:48em}}
.field{{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(19rem,100%),1fr));gap:1.1rem;margin-top:2.2rem}}
.capsule{{border:1px solid var(--line-strong);min-width:0;border-left:2px solid var(--evidence);background:var(--surface);padding:1.1rem 1.2rem;display:flex;flex-direction:column;gap:.75rem}}
.capsule-attested{{border-left-style:dashed;border-left-color:var(--line-strong)}}
.cap-head{{display:flex;align-items:center;gap:.7rem;flex-wrap:wrap}}
.cap-id{{color:var(--gold);font-size:.68rem;font-weight:400;margin:0;letter-spacing:.09em;margin-right:auto}}
.study-state{{border:1px solid var(--gold);border-left:3px solid var(--gold);background:transparent;padding:.7rem .85rem;margin:0 0 1rem;max-width:46em}}
.study-state-label{{font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}}
.study-state-pill{{font-size:.72rem;letter-spacing:.08em;color:var(--gold);border:1px solid var(--gold);padding:.08rem .4rem;margin-left:.35rem}}
.study-state-note{{font-size:.86rem;line-height:1.5;color:var(--muted);margin:.5rem 0 0}}
.cap-prop{{font-family:var(--serif);font-size:.98rem;line-height:1.5;margin:0;color:var(--ink)}}
.cap-slabs{{display:flex;flex-wrap:wrap;gap:.5rem}}
.cap-meta{{display:flex;flex-direction:column;gap:.3rem;color:var(--muted)}}
.cap-tags{{display:flex;flex-wrap:wrap;gap:.4rem}}
.cap-foot{{display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap;border-top:1px solid var(--line);padding-top:.7rem;margin-top:auto;color:var(--muted)}}
.clock{{width:1.5rem;height:1.5rem;flex:none}}
.clock svg{{width:100%;height:100%;transform:rotate(-90deg)}}
.clock-track{{fill:none;stroke:var(--line);stroke-width:3}}
.clock-arc{{fill:none;stroke:var(--ink);stroke-width:3;stroke-dasharray:97.39;stroke-dashoffset:97.39}}
.capsule.review-due .clock-arc{{stroke:var(--review)}}
.capsule.expired .clock-arc{{stroke:var(--invalid)}}
.capsule.expired{{border-left-color:var(--invalid)}}
.clock-days{{color:var(--muted)}}
html:not(.js) .clock{{display:none}}
.zone{{margin-top:4rem;border-top:1px solid var(--line);padding-top:2rem}}
.zone h2{{font-weight:520;font-size:clamp(1.5rem,3vw,2.1rem);margin:0 0 .6rem;letter-spacing:-.01em}}
.zone .zone-intro{{color:var(--muted);max-width:46em}}
.wall{{margin-top:1.6rem;border:1px solid var(--line-strong);background:var(--surface)}}
.wall-row{{display:grid;grid-template-columns:6.5rem 1fr;gap:1rem;padding:1rem 1.2rem;border-bottom:1px solid var(--line)}}
.wall-row:last-child{{border-bottom:none}}
.wall-id{{color:var(--gold)}}
.wall-row ul{{margin:0;padding-left:1.1rem;color:var(--muted);font-size:.92rem}}
.wall-row li{{margin:.25rem 0}}
.challenge-content{{color:var(--muted)}}
.challenge-content p{{margin:0 0 .55rem;font-size:.92rem}}
.challenge-label{{display:block;color:var(--gold);font-size:.61rem;letter-spacing:.08em;text-transform:uppercase;margin-bottom:.2rem}}
.challenge-consequence{{color:var(--ink);letter-spacing:.06em}}
.rescue-label{{margin-top:.8rem!important}}
.empty-rescues{{margin:0!important;font-size:.92rem}}
.replay pre{{background:var(--surface);border:1px solid var(--line-strong);padding:1.1rem 1.2rem;overflow-x:auto;font-family:var(--mono);font-size:.78rem;line-height:1.8;color:var(--ink);margin:1.4rem 0 0}}
.manual-list{{margin:1.2rem 0 0;padding-left:1.1rem;color:var(--muted);font-size:.92rem}}
.manual-list li{{margin:.35rem 0}}
footer{{border-top:1px solid var(--line);margin-top:3.5rem;padding:2rem 0 3rem;color:var(--muted);font-size:.88rem}}
.foot-links{{display:flex;flex-wrap:wrap;gap:1.4rem}}
@media (max-width:600px){{.wall-row{{grid-template-columns:1fr}}}}
@media print{{body{{background:#fff;color:#000}}}}
</style>
<script defer src="/assets/site.js"></script>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-head">
  <div class="container">
    <a class="wordmark" href="/">Pranav Bhave</a>
    <nav class="site-nav mono" aria-label="Site">
      <a href="/missing-column/">The Missing Column</a>
      <a href="/observatory/" aria-current="page">Evidence</a>
      <a href="/writing/">Writing</a>
      <a href="/work/">Work with me</a>
      <a href="/resume/">About</a>
    </nav>
    <button class="theme-toggle" id="themeToggle" aria-label="Toggle color theme" aria-pressed="false">
      <svg class="sun-only" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4.4"/><path d="M12 2.5v2.4M12 19.1v2.4M2.5 12h2.4M19.1 12h2.4M5 5l1.7 1.7M17.3 17.3 19 19M19 5l-1.7 1.7M6.7 17.3 5 19"/></svg>
      <svg class="moon-only" viewBox="0 0 24 24" aria-hidden="true"><path d="M20.2 14.2A8.2 8.2 0 0 1 9.8 3.8a8.2 8.2 0 1 0 10.4 10.4z"/></svg>
    </button>
  </div>
</header>
<div class="class-bar mono">
  <div class="container">
    <span><b>Observatory</b> — the registry as one field · generated from claims.yaml</span>
    <span data-claim-count-state="current">Schema v{version} · {n} claims · {status_line}</span>
  </div>
</div>
<header class="page">
  <div class="container">
    <h1>Claim observatory</h1>
    <p class="intro">Every claim in this record, as a capsule: its proposition, its evidence
      binding, its decay clock, the boundary it will not cross, and the condition that would
      defeat it. A solid cyan rail marks a
      public evidence binding; capsules without one carry a dashed neutral rail and an
      attested chip that says so; the clock turns amber when a review window is
      three-quarters spent and red when it lapses. There is no aggregate score here and
      never will be — a quiet trigger is quiet, not "healthy", and these envelopes do not
      average into one number.</p>
  </div>
</header>
<main class="container" id="main">
  <div class="field">{capsules}
  </div>

  <section class="zone" id="wall" aria-labelledby="wall-h">
    <h2 id="wall-h">The non-claims wall</h2>
    <p class="zone-intro">The outer boundary of the record: everything these claims refuse to
      support, collected in one place. A claim without a stated non-claim is a claim that has
      not found its edge yet.</p>
    <div class="wall">{wall}
    </div>
  </section>

  <section class="zone" id="challenges" aria-labelledby="challenges-h">
    <h2 id="challenges-h">Falsifiers and forbidden rescues</h2>
    <p class="zone-intro">A falsifier can otherwise be evaded by changing the proposition after
      observing the result. Each record fixes its defeat condition and consequence in advance,
      then lists the reinterpretations that cannot keep it standing. An explicit <code>[]</code>
      means no meaningful post-falsification rescue applies.</p>
    <div class="wall">{challenge_wall}
    </div>
  </section>

  <section class="zone replay" aria-labelledby="replay-h">
    <h2 id="replay-h">Replay manifest</h2>
    <p class="zone-intro">The exact commands that re-verify this record from a clean checkout.
      CI runs them on every push and weekly; nothing here requires trusting this page.</p>
    <pre>python scripts/verify_claims.py            # shape, bindings, triggers, freshness, coverage
python scripts/verify_census.py            # census rows, N/M/K recomputed, MC-001 coherence
python scripts/generate_ledger.py --check  # the ledger is generated, not hand-edited
python scripts/generate_modules.py --check # module pages match their registry
python scripts/generate_observatory.py --check  # this page matches the registry
python scripts/generate_missing_column.py --check  # campaign pages match the census
python scripts/generate_sitemap.py --check # sitemap lastmod matches git history
python scripts/verify_figures.py           # figure geometry, asserted to 1e-9
python scripts/mjgd_reference.py --test    # disclosure arithmetic identities
python scripts/reanalyze_bells_subset.py   # MC-002 recomputed from the hash-bound release
python scripts/reproduce_cc001.py          # clean-clone kernel reproduction + witnesses</pre>
  </section>

  <section class="zone" aria-labelledby="human-h">
    <h2 id="human-h">Human review</h2>
    <p class="zone-intro">Last owner review: <span class="mono">{reviewed}</span>. These review
      events cannot be executed by CI, and the record says so instead of borrowing the
      executable triggers' credibility:</p>
    <ul class="manual-list">{"".join(manual_events)}
    </ul>
    <p class="zone-intro" style="margin-top:1.2rem">Related instrument, its own contract intact:
      <a class="u" href="https://github.com/Cubits11/cc-framework/tree/main/evidence-cards">CC-Framework's
      evidence cards ↗</a> — their manifest forbids aggregate scores and forbids rendering
      "not-run" as passing, pending, or healthy, so this observatory links them rather than
      re-plotting them.</p>
  </section>
</main>
<footer>
  <div class="container">
    <div class="foot-links mono">
      <a class="u" href="/modules/">Modules</a>
      <a class="u" href="/ledger/">Evidence ledger</a>
      <a class="u" href="/">← The record</a>
    </div>
  </div>
</footer>
<script>
(function(){{
  document.documentElement.classList.add('js');
  var root=document.documentElement,meta=document.querySelectorAll('meta[name="theme-color"]'),toggle=document.getElementById('themeToggle');
  if(toggle){{
    var isDark=function(){{if(root.dataset.theme)return root.dataset.theme==='dark';return matchMedia('(prefers-color-scheme: dark)').matches}};
    var sync=function(){{var d=isDark();toggle.setAttribute('aria-pressed',String(d));toggle.setAttribute('aria-label',d?'Switch to light theme':'Switch to dark theme')}};
    var apply=function(n){{root.dataset.theme=n;try{{localStorage.setItem('theme',n)}}catch(e){{}}meta.forEach(function(m){{m.content=n==='dark'?'#0B0F0A':'#F1EDE2'}});sync()}};
    toggle.addEventListener('click',function(){{var n=isDark()?'light':'dark';var r=matchMedia('(prefers-reduced-motion: reduce)').matches;if(document.startViewTransition&&!r){{document.startViewTransition(function(){{apply(n)}})}}else{{apply(n)}}}});
    sync();matchMedia('(prefers-color-scheme: dark)').addEventListener('change',sync);
  }}
  /* decay clocks: drawn from the same registry fields the text already shows */
  var C=2*Math.PI*15.5;
  document.querySelectorAll('.capsule').forEach(function(cap){{
    var reviewed=new Date(cap.dataset.reviewed+'T00:00:00Z');
    var windowDays=Number(cap.dataset.window);
    if(!windowDays||isNaN(reviewed))return;
    var days=Math.floor((Date.now()-reviewed.getTime())/86400000);
    var pct=Math.min(Math.max(days/windowDays,0),1);
    var arc=cap.querySelector('.clock-arc');
    if(arc)arc.style.strokeDashoffset=String(C*(1-pct));
    var out=cap.querySelector('.clock-days');
    if(out)out.textContent=' · '+days+'d elapsed';
    if(days>windowDays)cap.classList.add('expired');
    else if(pct>=0.75)cap.classList.add('review-due');
  }});
}})();
</script>
</body>
</html>
'''


def main() -> int:
    registry = yaml.safe_load((ROOT / "claims.yaml").read_text())
    out = render(registry)
    target = ROOT / "observatory" / "index.html"
    if "--check" in sys.argv:
        current = target.read_text() if target.exists() else ""
        if current != out:
            print("DRIFT: observatory/index.html does not match what claims.yaml generates.")
            print("Run: python scripts/generate_observatory.py")
            return 1
        print("ok    observatory/index.html matches the registry (generated, no drift)")
        return 0
    target.parent.mkdir(exist_ok=True)
    target.write_text(out)
    print(f"wrote {target} ({len(out)} bytes) from claims.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
