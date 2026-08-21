#!/usr/bin/env python3
"""Generate ledger/index.html from claims.yaml.

The registry is the single source of truth; this renderer is deterministic
(no timestamps beyond registry fields, stable ordering). CI runs
`generate_ledger.py --check` and fails when the committed ledger drifts from
what the registry generates.
"""

import html
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent

LABELS = {
    "untested": "Publicly untested",
    "partially_supported": "Partially supported",
    "supported_within_scope": "Supported within scope",
    "inconclusive": "Inconclusive",
    "contradicted": "Contradicted",
    "machine_generated_owner_executed": "Machine-generated, owner-executed",
    "owner_authored": "Owner-authored, public",
    "lab_repository": "Lab repository, public",
    "owner_attested": "Owner-attested",
    "owner_verified": "Owner-verified",
    "executed_output": "Executed output",
    "document": "Document",
    "repository_readme": "Repository README",
    "site_document": "Site document",
    "none": "None public",
    "public": "Public",
    "private": "Private",
    "experimental": "Experimental",
    "in_development": "In development",
    "released": "Released",
    "stable": "Stable",
}


def esc(value) -> str:
    return html.escape(str(value).strip())


def label(key) -> str:
    return LABELS.get(key, str(key))


def support_label(support: dict) -> str:
    url, commit = support.get("url"), support.get("commit")
    if not url:
        return ""
    if commit:
        tail = commit[:8]
        repo = url.split("github.com/")[-1].split("/blob/")[0].split("/commit/")[0]
        name = url.rsplit("/", 1)[-1] if "/blob/" in url else repo
        return f'<a class="u" href="{esc(url)}"><code>{esc(name)} @ {esc(tail)}</code></a>'
    name = url.rsplit("/", 1)[-1] or url
    return f'<a class="u" href="{esc(url)}"><code>{esc(name)}</code></a>'


def render_claim(c: dict) -> str:
    d = c["dimensions"]
    status_cls = "status-hot" if d["evidential_status"] in ("inconclusive", "contradicted") \
        else ("status-dim" if d["evidential_status"] == "untested" else "status")
    dims = "".join(
        f'<span class="dim"><span class="dim-k">{esc(k)}</span>{esc(label(v))}</span>'
        for k, v in (("visibility", d["visibility"]), ("provenance", d["provenance"]),
                     ("support role", d["support_role"]), ("maturity", d["maturity"]))
    )
    sup = support_label(c.get("support") or {})
    sup_note = (c.get("support") or {}).get("note")
    triggers = "".join(
        '<li><span class="mono tag {cls}">{enf}</span> {desc}</li>'.format(
            cls="tag-exec" if t.get("enforcement") == "executable" else "tag-manual",
            enf=esc(t.get("enforcement", "manual")),
            desc=esc(t.get("note") or t.get("event") or t.get("type")),
        )
        for t in c.get("review_triggers", [])
    )
    non_claims = "".join(f"<li>{esc(n)}</li>" for n in c.get("non_claims", []))
    rows = [
        ("Scope", esc(c["scope"])),
    ]
    if sup:
        rows.append(("Binding", sup + (f'<br><span class="note">{esc(sup_note)}</span>' if sup_note else "")))
    elif sup_note:
        rows.append(("Support", esc(sup_note)))
    rows += [
        ("Dimensions", f'<span class="dims">{dims}</span>'),
        ("Reviewed", f'{esc(c["last_reviewed"])} · window {esc(c["review_window_days"])} days'),
        ("Triggers", f'<ul class="trg">{triggers}</ul>'),
        ("Non-claims", f'<ul class="nc">{non_claims}</ul>'),
    ]
    dl = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows)
    return f'''
  <article class="claim" id="{esc(c["id"])}">
    <div class="claim-head">
      <span class="mono claim-id">{esc(c["id"])}</span>
      <span class="mono {status_cls}">{esc(label(d["evidential_status"]))} · {esc(label(d["provenance"]))}</span>
    </div>
    <p class="prop">{esc(c["proposition"])}</p>
    <dl>{dl}</dl>
  </article>'''


def render(registry: dict) -> str:
    claims_html = "".join(render_claim(c) for c in registry["claims"])
    n = len(registry["claims"])
    version = esc(registry["version"])
    reviewed = esc(registry["last_owner_review"])
    return f'''<!doctype html>
<!-- GENERATED FILE — do not edit by hand.
     Source: claims.yaml · renderer: scripts/generate_ledger.py
     CI regenerates this page and fails on drift. -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Evidence Ledger — Pranav Bhave</title>
<meta name="description" content="The claim registry behind cubits11.github.io, generated from claims.yaml: every technical claim with its dimensions, immutable bindings, review triggers, and non-claims.">
<link rel="canonical" href="https://cubits11.github.io/ledger/">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%230B0F0A'/%3E%3Crect x='12' y='11' width='17' height='17' rx='4' fill='%23EDE8DA'/%3E%3Crect x='35' y='11' width='17' height='17' rx='4' fill='%23EDE8DA'/%3E%3Crect x='12' y='32' width='17' height='17' rx='4' fill='%23EDE8DA'/%3E%3Crect x='35' y='32' width='17' height='17' rx='4' fill='%23EDE8DA'/%3E%3Crect x='13.5' y='53' width='37' height='0.1' rx='2' fill='none' stroke='%23C9A15E' stroke-width='3'/%3E%3C/svg%3E">
<script>try{{var t=localStorage.getItem('theme');if(t==='dark'||t==='light')document.documentElement.dataset.theme=t}}catch(e){{}}</script>
<style>
@font-face{{font-family:'Fraunces';src:url('/assets/fonts/fraunces-roman.woff2') format('woff2');font-weight:100 900;font-style:normal;font-display:swap}}
@font-face{{font-family:'Fraunces';src:url('/assets/fonts/fraunces-italic.woff2') format('woff2');font-weight:100 900;font-style:italic;font-display:swap}}
@font-face{{font-family:'Instrument Sans';src:url('/assets/fonts/instrument-sans-roman.woff2') format('woff2');font-weight:400 700;font-display:swap}}
@font-face{{font-family:'Fragment Mono';src:url('/assets/fonts/fragment-mono.woff2') format('woff2');font-weight:400;font-display:swap}}
:root{{color-scheme:light;--bg:#F1EDE2;--surface:#F8F5EC;--ink:#14170F;--muted:#565E4E;--gold:#755A2C;--sage:#435B33;--line:#DCD5C2;--line-strong:#C2BAA2;
  --serif:'Fraunces',Georgia,serif;--sans:'Instrument Sans',-apple-system,Arial,sans-serif;--mono:'Fragment Mono',ui-monospace,Menlo,monospace}}
:root[data-theme="dark"]{{color-scheme:dark;--bg:#0B0F0A;--surface:#11150F;--ink:#EDE8DA;--muted:#9AA391;--gold:#C9A15E;--sage:#A8C491;--line:#232A20;--line-strong:#39422F}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{color-scheme:dark;--bg:#0B0F0A;--surface:#11150F;--ink:#EDE8DA;--muted:#9AA391;--gold:#C9A15E;--sage:#A8C491;--line:#232A20;--line-strong:#39422F}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:1rem;line-height:1.65;-webkit-font-smoothing:antialiased}}
.container{{width:min(920px,100% - 2*clamp(1.25rem,5vw,3rem));margin-inline:auto}}
.mono{{font-family:var(--mono);font-size:.68rem;letter-spacing:.09em;text-transform:uppercase}}
a{{color:inherit}}
.u{{text-decoration:none;border-bottom:1px solid currentColor;padding-bottom:1px}}
header.page{{padding:4.5rem 0 2.5rem;border-bottom:1px solid var(--line)}}
.crumb{{color:var(--gold);display:block;margin-bottom:1.2rem;text-decoration:none}}
h1{{font-family:var(--serif);font-weight:520;font-size:clamp(2.2rem,5.5vw,3.4rem);line-height:1.05;margin:0 0 1rem;letter-spacing:-.015em}}
.intro{{color:var(--muted);max-width:46em}}
.meta-row{{display:flex;flex-wrap:wrap;gap:1.4rem;margin-top:1.4rem;color:var(--muted)}}
.claim{{border:1px solid var(--line-strong);background:var(--surface);margin:1.4rem 0;padding:clamp(1.2rem,3vw,1.8rem)}}
.claim-head{{display:flex;align-items:baseline;justify-content:space-between;gap:1rem;flex-wrap:wrap;margin-bottom:.9rem}}
.claim-id{{color:var(--gold)}}
.status,.status-dim,.status-hot{{border:1px solid var(--line-strong);border-radius:999px;padding:.28rem .7rem}}
.status{{color:var(--ink)}}
.status-dim{{color:var(--muted);border-style:dashed}}
.status-hot{{color:var(--gold);border-color:var(--gold)}}
.prop{{font-family:var(--serif);font-size:1.12rem;line-height:1.5;margin:0 0 1rem;max-width:42em}}
dl{{display:grid;grid-template-columns:9.5rem 1fr;gap:.45rem 1.2rem;margin:0;font-size:.92rem}}
dt{{font-family:var(--mono);font-size:.64rem;letter-spacing:.08em;text-transform:uppercase;color:var(--gold);padding-top:.15rem}}
dd{{margin:0;color:var(--muted);overflow-wrap:anywhere}}
dd code{{font-family:var(--mono);font-size:.8em}}
.dims{{display:flex;flex-wrap:wrap;gap:.4rem .9rem}}
.dim{{display:inline-flex;gap:.45rem;align-items:baseline}}
.dim-k{{font-family:var(--mono);font-size:.6rem;letter-spacing:.07em;text-transform:uppercase;color:var(--sage)}}
ul.nc,ul.trg{{margin:.1rem 0 0;padding-left:1.1rem}}
ul.nc li,ul.trg li{{margin:.2rem 0}}
ul.trg{{list-style:none;padding-left:0}}
.tag{{border:1px solid var(--line-strong);border-radius:2px;padding:.1rem .4rem;margin-right:.5rem;font-size:.58rem}}
.tag-exec{{color:var(--sage);border-color:var(--sage)}}
.tag-manual{{color:var(--muted);border-style:dashed}}
.note{{font-size:.85rem}}
footer{{border-top:1px solid var(--line);margin-top:3.5rem;padding:2rem 0 3rem;color:var(--muted);font-size:.88rem}}
@media (max-width:600px){{dl{{grid-template-columns:1fr}}dt{{padding-top:.5rem}}}}
@media print{{body{{background:#fff;color:#000}}}}
</style>
</head>
<body>
<header class="page">
  <div class="container">
    <a class="crumb mono" href="/">← Pranav Bhave</a>
    <h1>Evidence ledger</h1>
    <p class="intro">Every technical claim the site renders with an evidence marker, in envelope
      form. This page is <strong>generated</strong> from
      <a class="u" href="https://github.com/Cubits11/cubits11.github.io/blob/main/claims.yaml">claims.yaml</a>
      by <a class="u" href="https://github.com/Cubits11/cubits11.github.io/blob/main/scripts/generate_ledger.py">generate_ledger.py</a>;
      CI regenerates it and fails on drift, verifies commit↔URL bindings, executes the
      executable review triggers against live evidence, and enforces each claim's freshness
      window — on every push and weekly. Triggers marked
      <span class="mono tag tag-manual" style="margin:0">manual</span> are honestly beyond
      CI's reach.</p>
    <div class="meta-row mono">
      <span>Schema v{version}</span>
      <span>Last owner review: {reviewed}</span>
      <span>{n} claims</span>
      <span><a class="u" href="https://github.com/Cubits11/cubits11.github.io/actions/workflows/verify.yml">CI runs ↗</a></span>
    </div>
  </div>
</header>

<main class="container">
{claims_html}
</main>

<footer>
  <div class="container">
    <span class="mono">Evidential statuses: untested · partially supported · supported within
    scope · inconclusive · contradicted. Provenance (incl. owner-attested) is a separate
    dimension — an attested claim with no public artifact is publicly untested, and says so.</span>
    <p style="margin:.9rem 0 0">A fired trigger or an expired window does not make a claim
    false; it makes the claim's warrant due for re-examination. Stale claims are re-reviewed
    or withdrawn, never quietly left standing.
    <a class="u" href="/">← Back to the record</a></p>
  </div>
</footer>
</body>
</html>
'''


def main() -> int:
    registry = yaml.safe_load((ROOT / "claims.yaml").read_text())
    out = render(registry)
    target = ROOT / "ledger" / "index.html"
    if "--check" in sys.argv:
        current = target.read_text() if target.exists() else ""
        if current != out:
            print("DRIFT: ledger/index.html does not match what claims.yaml generates.")
            print("Run: python scripts/generate_ledger.py")
            return 1
        print("ok    ledger/index.html matches the registry (generated, no drift)")
        return 0
    target.parent.mkdir(exist_ok=True)
    target.write_text(out)
    print(f"wrote {target} ({len(out)} bytes) from claims.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
