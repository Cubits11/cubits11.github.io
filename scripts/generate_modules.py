#!/usr/bin/env python3
"""Generate /modules/ from modules.yaml (+ claim envelopes from claims.yaml).

One epistemic grammar for every module page:

  QUESTION · EVIDENCE/PREMISES · VISUAL EXPERIMENT · FEASIBLE WORLDS ·
  IDENTIFICATION STATUS · RESULT OR BOUND · WITNESS/COUNTEREXAMPLE ·
  CLAIM ENVELOPE · EVIDENCE · FALSIFIER · NON-CLAIMS · REPRODUCIBILITY ·
  NEXT UNKNOWN

Sections that have no honest content are omitted, never fabricated; a
PLANNED module renders its frozen question with explicit
NOT-YET-POPULATED stamps, which is a feature.

Claim data is never duplicated here: modules cite claim_ids and the
generator embeds the ledger's own claim rendering, so status, bindings,
triggers, falsifiers, forbidden rescues, and non-claims stay single-sourced
in claims.yaml.

Validation (also under --check):
  * unique ids/slugs; every claim_id exists
  * looked-up binding commits are well-formed 40-hex revisions
  * a CURRENT module with a result section cites at least one
    supported_within_scope claim
  * a PLANNED module carries no result/witness section and only publicly
    untested claims
  * a module citing a `superseded`-maturity claim is itself
    historical/superseded

CI runs `generate_modules.py --check` and fails when the committed pages
drift from what the registries generate.
"""

import hashlib
import json
import pathlib
import re
import sys

import yaml

import generate_ledger as ledger

ROOT = pathlib.Path(__file__).resolve().parent.parent

GRAMMAR = [
    ("observed", "01", "Evidence / premises"),
    ("_visual", "02", "Visual experiment"),
    ("worlds", "03", "Feasible worlds"),
    ("identification", "04", "Identification status"),
    ("result", "05", "Result or bound"),
    ("witness", "06", "Witness / counterexample"),
    ("_envelope", "07", "Claim envelope"),
    ("_evidence", "08", "Evidence"),
    ("falsifier", "09", "Falsifier"),
    ("_nonclaims", "10", "Non-claims"),
    ("reproducibility", "11", "Reproducibility"),
    ("next", "12", "Next unknown"),
]

STATUS_LABEL = {
    "current": "Current",
    "planned": "Planned",
    "historical": "Historical",
    "superseded": "Superseded",
}

esc = ledger.esc

errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)
    print(f"FAIL  {msg}")


def module_digest(module: dict) -> str:
    return hashlib.sha256(
        json.dumps(module, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def validate(modules: list[dict], claims_by_id: dict) -> None:
    seen_ids: set = set()
    seen_slugs: set = set()
    for m in modules:
        mid, slug = m.get("id"), m.get("slug")
        if mid in seen_ids:
            err(f"duplicate module id {mid}")
        if slug in seen_slugs:
            err(f"duplicate module slug {slug}")
        seen_ids.add(mid)
        seen_slugs.add(slug)
        status = m.get("status")
        if status not in STATUS_LABEL:
            err(f"{mid}: status {status!r} not in {sorted(STATUS_LABEL)}")
        cited = []
        for cid in m.get("claim_ids", []):
            claim = claims_by_id.get(cid)
            if claim is None:
                err(f"{mid}: claim_id {cid} not in claims.yaml")
                continue
            cited.append(claim)
            commit = (claim.get("support") or {}).get("commit")
            if commit is not None and not re.fullmatch(r"[0-9a-f]{40}", str(commit)):
                err(f"{mid}: {cid} binding commit {commit!r} is not a 40-hex revision")
            if claim["dimensions"].get("maturity") == "superseded" and \
                    status not in ("historical", "superseded"):
                err(f"{mid}: cites superseded claim {cid} but status is {status}")
        sections = m.get("sections") or {}
        if status == "current" and sections.get("result"):
            if not any(c["dimensions"].get("evidential_status")
                       == "supported_within_scope" for c in cited):
                err(f"{mid}: current module with a result section must cite a "
                    f"supported_within_scope claim")
        if status == "planned":
            for banned in ("result", "witness"):
                if sections.get(banned):
                    err(f"{mid}: planned module may not carry a {banned} section")
            for c in cited:
                if c["dimensions"].get("evidential_status") != "untested":
                    err(f"{mid}: planned module cites {c['id']} whose status is "
                        f"{c['dimensions'].get('evidential_status')!r}, not untested")


def breadcrumb_jsonld(*trail: tuple) -> str:
    items = []
    for i, (name, url) in enumerate(trail, start=1):
        item = {"@type": "ListItem", "position": i, "name": name}
        if url:
            item["item"] = f"https://cubits11.github.io{url}"
        items.append(item)
    payload = json.dumps({"@context": "https://schema.org",
                          "@type": "BreadcrumbList",
                          "itemListElement": items}, indent=2,
                         ensure_ascii=False)
    return f'\n<script type="application/ld+json">\n{payload}\n</script>'


def head(title: str, description: str, canonical: str,
         jsonld: str = "") -> str:
    return f'''<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="article">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:image" content="https://cubits11.github.io/assets/img/og.jpg">
<meta property="og:site_name" content="Cubits11">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://cubits11.github.io/assets/img/og.jpg">
<meta name="robots" content="max-image-preview:large">
<meta name="theme-color" media="(prefers-color-scheme: light)" content="#F1EDE2">
<meta name="theme-color" media="(prefers-color-scheme: dark)" content="#0B0F0A">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%230B0F0A'/%3E%3Crect x='12' y='11' width='17' height='17' rx='4' fill='%23EDE8DA'/%3E%3Crect x='35' y='11' width='17' height='17' rx='4' fill='%23EDE8DA'/%3E%3Crect x='12' y='32' width='17' height='17' rx='4' fill='%23EDE8DA'/%3E%3Crect x='35' y='32' width='17' height='17' rx='4' fill='%23EDE8DA'/%3E%3Crect x='13.5' y='53' width='37' height='0.1' rx='2' fill='none' stroke='%23C9A15E' stroke-width='3'/%3E%3C/svg%3E">
<script>try{{var t=localStorage.getItem('theme');if(t==='dark'||t==='light'){{document.documentElement.dataset.theme=t;var m=document.querySelectorAll('meta[name="theme-color"]');for(var i=0;i<m.length;i++)m[i].content=t==='dark'?'#0B0F0A':'#F1EDE2'}}}}catch(e){{}}</script>
<link rel="stylesheet" href="/assets/site.css">{jsonld}'''


SITE_HEAD = '''<a class="skip" href="#main">Skip to content</a>
<header class="site-head">
  <div class="container">
    <a class="wordmark" href="/">Pranav Bhave</a>
    <nav class="site-nav mono" aria-label="Site">
      <a href="/modules/" aria-current="page">Modules</a>
      <a href="/observatory/">Observatory</a>
      <a href="/ledger/">Ledger</a>
      <a href="/writing/">Writing</a>
      <a href="/archive/">Archive</a>
      <a href="/resume/">R&eacute;sum&eacute;</a>
    </nav>
    <button class="theme-toggle" id="themeToggle" aria-label="Toggle color theme" aria-pressed="false">
      <svg class="sun-only" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4.4"/><path d="M12 2.5v2.4M12 19.1v2.4M2.5 12h2.4M19.1 12h2.4M5 5l1.7 1.7M17.3 17.3 19 19M19 5l-1.7 1.7M6.7 17.3 5 19"/></svg>
      <svg class="moon-only" viewBox="0 0 24 24" aria-hidden="true"><path d="M20.2 14.2A8.2 8.2 0 0 1 9.8 3.8a8.2 8.2 0 1 0 10.4 10.4z"/></svg>
    </button>
  </div>
</header>'''

TOGGLE_JS = '''<script>
(function(){
  document.documentElement.classList.add('js');
  var root=document.documentElement,meta=document.querySelectorAll('meta[name="theme-color"]'),toggle=document.getElementById('themeToggle');
  if(!toggle)return;
  function isDark(){if(root.dataset.theme)return root.dataset.theme==='dark';return matchMedia('(prefers-color-scheme: dark)').matches}
  function sync(){var d=isDark();toggle.setAttribute('aria-pressed',String(d));toggle.setAttribute('aria-label',d?'Switch to light theme':'Switch to dark theme')}
  function apply(n){root.dataset.theme=n;try{localStorage.setItem('theme',n)}catch(e){}meta.forEach(function(m){m.content=n==='dark'?'#0B0F0A':'#F1EDE2'});sync()}
  toggle.addEventListener('click',function(){var n=isDark()?'light':'dark';var r=matchMedia('(prefers-reduced-motion: reduce)').matches;if(document.startViewTransition&&!r){document.startViewTransition(function(){apply(n)})}else{apply(n)}});
  sync();matchMedia('(prefers-color-scheme: dark)').addEventListener('change',sync);
})();
</script>'''

MODULE_CSS = '''<style>
body{font-size:1.04rem;line-height:1.72}
.container{width:min(760px,100% - 2*clamp(1.25rem,5vw,3rem))}
.mono{font-size:.7rem}
header.page{padding:7.9rem 0 2.6rem}
.eyebrow{color:var(--gold);margin-bottom:1.1rem;display:flex;flex-wrap:wrap;gap:.5rem 1.4rem;align-items:baseline}
h1.q{font-weight:520;font-size:clamp(2rem,5.4vw,3.4rem);line-height:1.1;margin:0 0 1.2rem;letter-spacing:-.018em}
.standfirst{font-family:var(--serif);font-style:italic;font-size:1.22rem;color:var(--muted);line-height:1.55;max-width:36em}
.gsec{border-top:1px solid var(--line);padding:1.7rem 0 .4rem;margin-top:1.4rem}
.gsec .glabel{display:flex;gap:.9rem;align-items:baseline;margin-bottom:.7rem}
.gsec .gno{font-family:var(--mono);font-size:.66rem;letter-spacing:.09em;color:var(--muted)}
.gsec .gname{font-family:var(--mono);font-size:.7rem;letter-spacing:.09em;text-transform:uppercase;color:var(--gold)}
.gsec p{color:var(--ink);max-width:62ch}
.gsec ul{margin:.2rem 0 1em;padding-left:1.15rem;color:var(--ink);max-width:62ch}
.gsec li{margin:.35rem 0}
.gsec pre{background:var(--surface);border:1px solid var(--line-strong);padding:1rem 1.1rem;overflow-x:auto;font-family:var(--mono);font-size:.78rem;line-height:1.7;color:var(--ink)}
.vis-door{display:flex;flex-direction:column;gap:.4rem;text-decoration:none;border:1px solid var(--line-strong);background:var(--surface);padding:1.1rem 1.2rem;max-width:34rem;transition:border-color .2s}
.vis-door:hover,.vis-door:focus-visible{border-color:var(--evidence)}
.vis-door .mono{color:var(--evidence)}
.stamp-row{display:flex;flex-wrap:wrap;gap:.7rem;margin:1.6rem 0 .4rem}
.claim{border:1px solid var(--line-strong);background:var(--surface);margin:1rem 0;padding:clamp(1.1rem,3vw,1.5rem)}
.claim-head{display:flex;align-items:baseline;justify-content:space-between;gap:1rem;flex-wrap:wrap;margin-bottom:.9rem}
.claim-id{color:var(--gold);font-size:.68rem;font-weight:400;margin:0;letter-spacing:.09em}
.prop{font-family:var(--serif);font-size:1.05rem;line-height:1.5;margin:0 0 1rem;max-width:42em}
.claim dl{display:grid;grid-template-columns:9.5rem 1fr;gap:.45rem 1.2rem;margin:0;font-size:.9rem}
.claim dt{font-family:var(--mono);font-size:.62rem;letter-spacing:.08em;text-transform:uppercase;color:var(--gold);padding-top:.15rem}
.claim dd{margin:0;color:var(--muted);overflow-wrap:anywhere}
.claim dd code{font-family:var(--mono);font-size:.8em}
.dims{display:flex;flex-wrap:wrap;gap:.4rem .9rem}
.dim{display:inline-flex;gap:.45rem;align-items:baseline}
.dim-k{font-family:var(--mono);font-size:.6rem;letter-spacing:.07em;text-transform:uppercase;color:var(--muted)}
ul.nc,ul.trg{margin:.1rem 0 0;padding-left:1.1rem}
ul.trg{list-style:none;padding-left:0}
.note{font-size:.85rem}
.evd{display:flex;flex-direction:column;gap:.4rem;font-size:.95rem;color:var(--muted);max-width:62ch}
footer{border-top:1px solid var(--line);margin-top:3.5rem;padding:2rem 0 3rem;color:var(--muted);font-size:.85rem}
.foot-links{display:flex;flex-wrap:wrap;gap:1.4rem;margin-bottom:1rem}
.digest{overflow-wrap:anywhere}
@media (max-width:600px){.claim dl{grid-template-columns:1fr}.claim dt{padding-top:.5rem}}
@media print{body{background:#fff;color:#000}}
</style>'''


def render_visual(m: dict) -> str:
    vis = m.get("visualization")
    if not vis:
        return ""
    return (f'<a class="vis-door" href="{esc(vis["href"])}">'
            f'<span class="mono">Open the experiment</span>'
            f'<span>{esc(vis["label"])}</span></a>')


def render_evidence(cited: list[dict]) -> str:
    rows = []
    for c in cited:
        sup = c.get("support") or {}
        url, commit = sup.get("url"), sup.get("commit")
        prov = ledger.label(c["dimensions"]["provenance"])
        reviewed = c.get("last_reviewed")
        if url and commit:
            rows.append(f'<span><a class="u" href="{esc(url)}"><code>'
                        f'{esc(c["id"])} @ {esc(str(commit)[:8])}</code></a>'
                        f' — {esc(prov)} · reviewed {esc(reviewed)}</span>')
        elif url:
            rows.append(f'<span><a class="u" href="{esc(url)}"><code>{esc(c["id"])}'
                        f'</code></a> — {esc(prov)} · mutable link by design · '
                        f'reviewed {esc(reviewed)}</span>')
        else:
            rows.append(f'<span><code>{esc(c["id"])}</code> — {esc(prov)} · '
                        f'no public binding, by declaration · reviewed '
                        f'{esc(reviewed)}</span>')
    return '<div class="evd">' + "".join(rows) + "</div>"


def render_nonclaims(m: dict, cited: list[dict]) -> str:
    items: list[str] = []
    for c in cited:
        for n in c.get("non_claims", []):
            if n not in items:
                items.append(n)
    for n in m.get("non_claims_extra", []):
        if n not in items:
            items.append(n)
    return "<ul>" + "".join(f"<li>{esc(n)}</li>" for n in items) + "</ul>"


def render_section(no: str, name: str, inner: str) -> str:
    return (f'\n  <section class="gsec">\n    <div class="glabel">'
            f'<span class="gno">{no}</span>'
            f'<span class="gname">{esc(name)}</span></div>\n    {inner}\n  </section>')


def render_module(m: dict, claims_by_id: dict) -> str:
    num = m["id"].split("-")[1]
    status = m["status"]
    cited = [claims_by_id[cid] for cid in m.get("claim_ids", [])
             if cid in claims_by_id]
    sections = m.get("sections") or {}
    digest = module_digest(m)
    canonical = f"https://cubits11.github.io/modules/{m['slug']}/"

    body_sections = []
    for key, no, name in GRAMMAR:
        if key == "_visual":
            inner = render_visual(m)
        elif key == "_envelope":
            inner = "".join(ledger.render_claim(c) for c in cited) + \
                ('<p class="note" style="color:var(--muted)">Rendered from the same '
                 'registry as the <a class="u" href="/ledger/">ledger</a> — one '
                 'source, two views.</p>' if cited else "")
        elif key == "_evidence":
            inner = render_evidence(cited) if cited else ""
        elif key == "_nonclaims":
            inner = render_nonclaims(m, cited)
        else:
            text = sections.get(key.lstrip("_"))
            if key == "reproducibility" and text:
                inner = f"<pre>{esc(text)}</pre>"
            else:
                inner = f"<p>{esc(text)}</p>" if text else ""
        if inner:
            body_sections.append(render_section(no, name, inner))

    planned_stamps = ""
    if status == "planned":
        planned_stamps = ('\n  <div class="stamp-row">'
                          '<span class="stamp stamp-untested">Status — planned</span>'
                          '<span class="stamp stamp-untested">Public evidence — none yet</span>'
                          '<span class="stamp">Question — stated</span>'
                          '<span class="stamp stamp-untested">Result — not yet populated</span>'
                          '</div>')

    status_pill = ("status-plan" if status == "planned"
                   else "status-dim" if status in ("historical", "superseded")
                   else "status")
    title = f"{m['title']} — Modules — Pranav Bhave"
    desc = re.sub(r"\s+", " ", str(m["question"]).strip())
    crumbs = breadcrumb_jsonld(("The record", "/"), ("Modules", "/modules/"),
                               (m["title"], None))

    return f'''<!doctype html>
<!-- GENERATED FILE — do not edit by hand.
     Source: modules.yaml + claims.yaml · renderer: scripts/generate_modules.py
     CI regenerates this page and fails on drift. -->
<html lang="en">
<head>
{head(title, desc, canonical, crumbs)}
{MODULE_CSS}
<script defer src="/assets/site.js"></script>
</head>
<body>
{SITE_HEAD}
<div class="class-bar mono">
  <div class="container">
    <span>Module <b>{esc(num)}</b> of 006 — <a class="u" href="/modules/">all modules</a></span>
    <span class="{status_pill}">{esc(STATUS_LABEL[status])}</span>
  </div>
</div>
<header class="page">
  <div class="container">
    <p class="eyebrow mono"><span>Module {esc(num)} — {esc(m["title"])}</span></p>
    <h1 class="q">{esc(desc)}</h1>
    <p class="standfirst">{esc(re.sub(r"\\s+", " ", str(m["thesis"]).strip()))}</p>{planned_stamps}
  </div>
</header>
<main class="container" id="main">{"".join(body_sections)}
</main>
<footer>
  <div class="container">
    <div class="foot-links mono">
      <a class="u" href="/modules/">← All modules</a>
      <a class="u" href="/ledger/">Evidence ledger</a>
      <a class="u" href="/observatory/">Observatory</a>
      <a class="u" href="/">The record</a>
    </div>
    <span class="mono digest">Module identity sha256:{digest} — the canonical registry entry; regenerate to verify.</span>
  </div>
</footer>
{TOGGLE_JS}
</body>
</html>
'''


def render_index(modules: list[dict], claims_by_id: dict) -> str:
    items = []
    for m in modules:
        num = m["id"].split("-")[1]
        status = m["status"]
        status_pill = ("status-plan" if status == "planned"
                       else "status-dim" if status in ("historical", "superseded")
                       else "status")
        q = re.sub(r"\s+", " ", str(m["question"]).strip())
        claims = " · ".join(m.get("claim_ids", []))
        items.append(f'''
  <a class="mod-item" href="/modules/{esc(m["slug"])}/">
    <span class="mono mod-no">{esc(num)}</span>
    <span class="mod-q">{esc(q)}</span>
    <span class="mod-meta"><span class="mono {status_pill}">{esc(STATUS_LABEL[status])}</span><span class="mono mod-claims">{esc(claims)}</span></span>
  </a>''')
    title = "Modules — Pranav Bhave"
    desc = ("Six questions, one epistemic grammar: claims, feasible worlds, "
            "witnesses, non-claims, and the next unknown — each module taken to "
            "its current evidence boundary.")
    return f'''<!doctype html>
<!-- GENERATED FILE — do not edit by hand.
     Source: modules.yaml + claims.yaml · renderer: scripts/generate_modules.py
     CI regenerates this page and fails on drift. -->
<html lang="en">
<head>
{head(title, desc, "https://cubits11.github.io/modules/",
      breadcrumb_jsonld(("The record", "/"), ("Modules", None)))}
<style>
body{{font-size:1.04rem;line-height:1.7}}
.container{{width:min(880px,100% - 2*clamp(1.25rem,5vw,3rem))}}
.mono{{font-size:.7rem}}
header.page{{padding:7.9rem 0 2.2rem}}
h1{{font-weight:520;font-size:clamp(2.4rem,6vw,4rem);line-height:1.04;margin:0 0 1rem;letter-spacing:-.018em}}
.intro{{color:var(--muted);max-width:46em}}
.mod-list{{margin-top:2.4rem;border-top:1px solid var(--line)}}
.mod-item{{display:grid;grid-template-columns:auto 1fr auto;gap:1.2rem 1.6rem;align-items:baseline;
  padding:1.6rem .2rem;border-bottom:1px solid var(--line);text-decoration:none;transition:background-color .2s}}
.mod-item:hover,.mod-item:focus-visible{{background:color-mix(in srgb, var(--surface) 70%, transparent)}}
.mod-no{{color:var(--gold);font-size:.9rem}}
.mod-q{{font-family:var(--serif);font-size:clamp(1.25rem,2.6vw,1.7rem);font-weight:500;line-height:1.3;letter-spacing:-.01em}}
.mod-meta{{display:flex;flex-direction:column;gap:.5rem;align-items:flex-end}}
.mod-claims{{color:var(--muted)}}
footer{{border-top:1px solid var(--line);margin-top:3.5rem;padding:2rem 0 3rem;color:var(--muted);font-size:.88rem}}
.foot-links{{display:flex;flex-wrap:wrap;gap:1.4rem}}
@media (max-width:600px){{.mod-item{{grid-template-columns:auto 1fr}}.mod-meta{{grid-column:2;flex-direction:row;align-items:baseline}}}}
@media print{{body{{background:#fff;color:#000}}}}
</style>
<script defer src="/assets/site.js"></script>
</head>
<body>
{SITE_HEAD}
<div class="class-bar mono">
  <div class="container">
    <span><b>Modules</b> — generated from modules.yaml, drift-checked in CI</span>
    <span>{len(modules)} questions</span>
  </div>
</div>
<header class="page">
  <div class="container">
    <h1>Six questions,<br>one grammar</h1>
    <p class="intro">Each module takes one question to its current evidence boundary and stops
      there, visibly: what is observed, which worlds remain feasible, what is identified, what
      would falsify it, and what is not claimed. Status and bindings come from the same registry
      the <a class="u" href="/ledger/">ledger</a> renders. A planned module says so on its face —
      an honest empty slot outranks a confident guess.</p>
  </div>
</header>
<main class="container" id="main">
  <nav class="mod-list" aria-label="Modules">{"".join(items)}
  </nav>
</main>
<footer>
  <div class="container">
    <div class="foot-links mono">
      <a class="u" href="/observatory/">Observatory</a>
      <a class="u" href="/ledger/">Evidence ledger</a>
      <a class="u" href="/">← The record</a>
    </div>
  </div>
</footer>
{TOGGLE_JS}
</body>
</html>
'''


def main() -> int:
    registry = yaml.safe_load((ROOT / "modules.yaml").read_text())
    claims = yaml.safe_load((ROOT / "claims.yaml").read_text())
    claims_by_id = {c["id"]: c for c in claims["claims"]}
    modules = registry["modules"]

    validate(modules, claims_by_id)
    if errors:
        print(f"\n{len(errors)} validation failure(s).")
        return 1

    outputs = {ROOT / "modules" / "index.html": render_index(modules, claims_by_id)}
    for m in modules:
        outputs[ROOT / "modules" / m["slug"] / "index.html"] = \
            render_module(m, claims_by_id)

    if "--check" in sys.argv:
        drifted = [p for p, out in outputs.items()
                   if not p.exists() or p.read_text() != out]
        if drifted:
            for p in drifted:
                print(f"DRIFT: {p.relative_to(ROOT)}")
            print("Run: python scripts/generate_modules.py")
            return 1
        print(f"ok    {len(outputs)} module pages match the registries "
              f"(generated, no drift)")
        return 0

    for path, out in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(out)
        print(f"wrote {path.relative_to(ROOT)} ({len(out)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
