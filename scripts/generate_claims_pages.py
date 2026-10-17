#!/usr/bin/env python3
"""Generate addressable claim pages and a documented JSON-LD vocabulary.

Propositions, scope, consequences and non-claims come from claims.yaml.
Editorial titles have a lexical and numeric consistency check; this catches
unsupported tokens but cannot establish that a paraphrase is entailed.
Custom metadata makes qualifications available to consumers, without enforcing
how a consumer quotes or interprets them. --check detects generated drift.
"""

from __future__ import annotations

import datetime
import html
import json
import pathlib
import re
import sys
import unicodedata
import copy

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from generate_ledger import esc, label, squash, support_label  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://cubits11.github.io"
NS = f"{SITE}/ns/falsifiable/v1"

# ---------------------------------------------------------------------------
# the vocabulary
#
# Custom properties used by this site. Each is defined once, here, and
# that definition is what the context file, the specification page, and the
# JSON-LD on every claim page are all rendered from.
# ---------------------------------------------------------------------------

# Every emitted custom property has one definition and one JSON-LD mapping.
TERMS = (
    {"term": "falsifier", "range": "Text", "gloss": "The stated condition that triggers the declared consequence.", "source": "falsifier.condition"},
    {"term": "consequence", "range": "Text", "gloss": "The declared response: NARROW, REJECT or HOLD.", "source": "falsifier.consequence"},
    {"term": "forbiddenRescue", "range": "Text list", "container": "@list", "gloss": "Repairs the author declares unavailable after the falsifier fires.", "note": "An explicit empty RDF list preserves the difference between no forbidden rescues and an omitted field.", "source": "forbidden_rescues"},
    {"term": "nonClaim", "range": "Text list", "container": "@list", "gloss": "Limits the author states on what the claim licenses.", "source": "non_claims"},
    {"term": "scopeStatement", "range": "Text", "gloss": "The claim's stated domain and limitations.", "source": "scope"},
    {"term": "evidentialStatus", "range": "Text", "gloss": "The registry's current evidential-status label.", "source": "dimensions.evidential_status"},
    {"term": "lastReviewed", "range": "Date", "type": "xsd:date", "gloss": "The last review date recorded for this claim.", "source": "last_reviewed"},
    {"term": "reviewWindow", "range": "Duration", "type": "xsd:duration", "gloss": "The declared interval between required reviews.", "source": "review_window_days"},
    {"term": "warrantExpires", "range": "Date", "type": "xsd:date", "gloss": "The recorded review date plus the review window.", "note": "After this date the review is overdue. This is not a probability, a truth verdict, or proof that no unrecorded review occurred.", "source": "last_reviewed + review_window_days"},
    {"term": "supportUrl", "range": "URL", "type": "@id", "gloss": "The declared public support location, which may be mutable.", "source": "support.url"},
    {"term": "supportBinding", "range": "URL", "type": "@id", "gloss": "A support URL containing the declared immutable revision.", "note": "Emitted only with a declared revision embedded in the URL. Reachability and other binding checks belong to verify_claims.py; this metadata alone proves neither.", "source": "support.url, when support.commit is embedded"},
    {"term": "boundRevision", "range": "Text", "gloss": "The immutable support revision declared in the registry.", "source": "support.commit"},
    {"term": "verdict", "range": "Text", "gloss": "An explicit rejection notice recorded at the start of the proposition.", "source": "proposition rejection prefix"},
    {"term": "verdictDate", "range": "Date", "type": "xsd:date", "gloss": "The date of that explicit rejection notice.", "source": "proposition rejection prefix"},
)


def vocabulary_context() -> dict:
    context = {"@version": 1.1, "fw": {"@id": f"{NS}/#", "@prefix": True},
               "xsd": "http://www.w3.org/2001/XMLSchema#"}
    for term in TERMS:
        spec = {"@id": f"{NS}/#{term['term']}"}
        if term.get("type"):
            spec["@type"] = term["type"]
        if term.get("container"):
            spec["@container"] = term["container"]
        context[f"fw:{term['term']}"] = spec
    return context


# The acquisition gate's own budgets, restated here so that a title or a
# description that would fail verify_growth.py fails at the point it is
# written instead of two scripts later.
MAX_TITLE = 72
MAX_DESC = 200
MIN_DESC = 70
# What a result page actually renders, which is the budget that matters.
DISPLAY_DESC = 158

# Words a title may use without appearing in its claim: function words, and
# the registry's own structural nouns.
TITLE_STOPWORDS = frozenset("""
a about after an and are as at be been before between but by can do does for
from had has have how if in into is it its of on or over should than that the
their then there these this through to under up was were what when where which
while who why will with without
claim claims registry record
""".split())

# ---------------------------------------------------------------------------
# titles
#
# The one string on a claim page that the registry does not supply. Held here
# rather than in claims.yaml so that a display decision never touches the
# hash-chained registry, and gated by check_titles_grounded so that it can
# never say more than the claim it names.
# ---------------------------------------------------------------------------

TITLES: dict[str, str] = {
    "CC-001":    "Frechet-Hoeffding endpoint bounds from declared marginals",
    "CC-002":    "The claim-boundary manifest and its validation lanes",
    "CC-003":    "Identical pairwise overlaps, different three-way probability",
    "CC-004":    "The sharp interval for the both-fail query",
    "CC-005":    "A measurement contract frozen before any dataset was inspected",
    "CC-006":    "The E2 pipeline rehearsed on synthetic mechanisms",
    "REL-001":   "Preregistered hypothesis on dependence-aware presentation",
    "MC-001":    "Of 20 guardrail evaluations, 5 with joint-evidence artifacts",
    "MC-002":    "Five supervisors on BELLS against the independence plug-in",
    "MC-003":    "Marginals fix the all-miss rate only up to an interval",
    "MC-004":    "Multimodal Safeguard Bench, recomputed from per-item verdicts",
    "AF-001":    "AI Fluency Index prevalences for 11 of 24 behaviours",
    "GA-001":    "Ghost-Ark, a verifier for the provenance limits of receipts",
    "GV-001":    "Ghost Visualizer, a visual essay that computes safety scores",
    "GCE-001":   "The Guardrail Composability Explorer, a coursework demo",
    "SITE-001":  "The palette token pairs and their computed contrast",
    "SITE-002":  "The claim registry, enforced in CI",
    "E3-001":    "Two ungated classifiers scored on harmful and benign items",
    "E3B-001":   "The same classifiers on the attack family they were built for",
    "E6-001":    "Rejected: the permutation routine moves unequal-mass atoms",
    "E7B-001":   "Rejected: calibration uses the shared pool for every judge",
}

REJECTED_PREFIX = re.compile(r"^\s*REJECTED AS STATED on (\d{4}-\d{2}-\d{2})\.\s*")

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)


# ---------------------------------------------------------------------------
# registry reading
# ---------------------------------------------------------------------------

def load_claims() -> list[dict]:
    return yaml.safe_load((ROOT / "claims.yaml").read_text())["claims"]


def route_of(cid: str) -> str:
    return f"/claims/{cid.lower()}/"


def expiry_of(claim: dict) -> str:
    """lastReviewed + reviewWindow, as a date.

    Deterministic by construction: the page states the date the warrant runs
    out, never a countdown. A countdown would make every generated page drift
    from its own drift gate one day after it was written.
    """
    reviewed = datetime.date.fromisoformat(str(claim["last_reviewed"]))
    return (reviewed + datetime.timedelta(
        days=int(claim["review_window_days"]))).isoformat()


def verdict_of(claim: dict) -> tuple[str, str]:
    """(stamp, date) for a claim whose proposition opens with a verdict."""
    match = REJECTED_PREFIX.match(str(claim["proposition"]))
    return ("REJECTED AS STATED", match.group(1)) if match else ("", "")


def status_of(claim: dict) -> str:
    stamp, _ = verdict_of(claim)
    if stamp:
        return stamp
    return label(claim["dimensions"]["evidential_status"])


def description_of(claim: dict, title: str) -> str:
    """The claim, its consequence, and as much of its falsifier as fits.

    Two budgets apply. The acquisition gate allows 200 characters; Google
    renders about 160 and drops the rest. Writing to the gate's budget would
    pass the gate and put the falsifier in the half nobody sees, so the
    consequence — the single most load-bearing token — comes before the
    condition rather than after it, and the whole string is written to the
    display budget instead of the gate's.
    """
    cid = claim["id"]
    consequence = claim["falsifier"]["consequence"]
    condition = squash(claim["falsifier"]["condition"])
    head = f"{cid}: {title}. {consequence} if "
    body = condition[0].lower() + condition[1:]
    out = f"{head}{body.rstrip('.')}"
    while len(html.escape(out)) > DISPLAY_DESC:
        out = out[: len(out) - 1].rsplit(" ", 1)[0].rstrip(".,;:") + "…"
    if len(html.escape(out)) < MIN_DESC:
        out = f"{head}{body.rstrip('.')}"
    return out


# ---------------------------------------------------------------------------
# the grounding gate
# ---------------------------------------------------------------------------

def words(text: str) -> set[str]:
    text = text.replace("–", "-").replace("—", "-")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z']*", text)}


def stems(vocabulary: set[str]) -> set[str]:
    out = set(vocabulary)
    for word in vocabulary:
        for suffix in ("s", "es", "ed", "ing", "'s"):
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                out.add(word[: -len(suffix)])
        out.add(word + "s")
    return out


def check_titles_grounded(claims: list[dict]) -> None:
    """A title may not use a content word its claim never uses.

    This is a lexical consistency check, not a proof of semantic entailment. A
    title is allowed to be shorter than the claim, and to select from it. It
    is not allowed to introduce a noun the claim does not contain, because
    the title is what a search result shows and a reader who never opens the
    page has read only the title.
    """
    ids = {c["id"] for c in claims}
    for extra in sorted(set(TITLES) - ids):
        fail(f"TITLES has {extra}, which is not in claims.yaml")
    for missing in sorted(ids - set(TITLES)):
        fail(f"{missing}: no title — add one to TITLES in "
             f"scripts/generate_claims_pages.py")
    seen: dict[str, str] = {}
    for claim in claims:
        cid = claim["id"]
        title = TITLES.get(cid)
        if not title:
            continue
        if title in seen:
            fail(f"{cid}: title duplicates {seen[title]}")
        seen[title] = cid
        rendered = html.escape(f"{cid} \u00b7 {title}")
        if len(rendered) > MAX_TITLE:
            fail(f"{cid}: rendered title is {len(rendered)} chars (max "
                 f"{MAX_TITLE}) — it would be truncated in results: {title!r}")
        desc = html.escape(description_of(claim, title))
        if not MIN_DESC <= len(desc) <= MAX_DESC:
            fail(f"{cid}: rendered description is {len(desc)} chars "
                 f"(want {MIN_DESC}-{MAX_DESC})")
        source = " ".join([
            str(claim["proposition"]), str(claim["scope"]),
            str(claim["falsifier"]["condition"]),
            " ".join(str(n) for n in claim.get("non_claims", [])),
        ])
        allowed = stems(words(source)) | TITLE_STOPWORDS | words(cid)
        # Numerals are checked too: a title saying 50 when the proposition
        # says 5 must not pass merely because numbers are not content words.
        numbers = lambda text: set(re.findall(r"(?<![\w])\d+(?:\.\d+)?(?![\w])", text))
        unsupported = numbers(title) - numbers(str(claim["proposition"]))
        if unsupported:
            fail(f"{cid}: title numerals absent from proposition: {sorted(unsupported)}")
        for word in sorted(words(title) - allowed):
            fail(f"{cid}: title says {word!r}, which its claim never says — "
                 f"review the editorial title against the registry")


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------

BANNER = ("<!doctype html>\n"
          "<!-- GENERATED FILE — do not edit by hand.\n"
          "     Source: claims.yaml · renderer: scripts/generate_claims_pages.py\n"
          "     CI regenerates this page and fails on drift. -->\n")

ICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E"
        "%3Crect width='64' height='64' rx='14' fill='%230B0F0A'/%3E"
        "%3Crect x='12' y='11' width='17' height='17' rx='4' fill='%23EDE8DA'/%3E"
        "%3Crect x='35' y='11' width='17' height='17' rx='4' fill='%23EDE8DA'/%3E"
        "%3Crect x='12' y='32' width='17' height='17' rx='4' fill='%23EDE8DA'/%3E"
        "%3Crect x='35' y='32' width='17' height='17' rx='4' fill='%23EDE8DA'/%3E"
        "%3Crect x='13.5' y='53' width='37' height='0.1' rx='2' fill='none' "
        "stroke='%23C9A15E' stroke-width='3'/%3E%3C/svg%3E")

OG_IMAGE = f"{SITE}/assets/img/og.jpg"
OG_ALT = ("Pranav Bhave, AI Assurance · Security Engineering · Evidence "
          "Systems — measuring what guardrail stacks miss together")

THEME_BOOT = ("<script>try{var t=localStorage.getItem('theme');"
              "if(t==='dark'||t==='light'){document.documentElement.dataset.theme=t;"
              "var m=document.querySelectorAll('meta[name=\"theme-color\"]');"
              "for(var i=0;i<m.length;i++)m[i].content=t==='dark'?'#0B0F0A':'#F1EDE2'}}"
              "catch(e){}</script>")

THEME_JS = """<script>
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
</script>"""

SITE_HEAD = """<a class="skip" href="#main">Skip to content</a>
<header class="site-head">
  <div class="container">
    <a class="wordmark" href="/">Pranav Bhave</a>
    <nav class="site-nav mono" aria-label="Site">
      <a href="/missing-column/">The Missing Column</a>
      <a href="/observatory/">Evidence</a>
      <a href="/writing/">Writing</a>
      <a href="/films/">Films</a>
      <a href="/work/">Work with me</a>
      <a href="/resume/">About</a>
    </nav>
    <button class="theme-toggle" id="themeToggle" aria-label="Toggle color theme" aria-pressed="false">
      <svg class="sun-only" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4.4"/><path d="M12 2.5v2.4M12 19.1v2.4M2.5 12h2.4M19.1 12h2.4M5 5l1.7 1.7M17.3 17.3 19 19M19 5l-1.7 1.7M6.7 17.3 5 19"/></svg>
      <svg class="moon-only" viewBox="0 0 24 24" aria-hidden="true"><path d="M20.2 14.2A8.2 8.2 0 0 1 9.8 3.8a8.2 8.2 0 1 0 10.4 10.4z"/></svg>
    </button>
  </div>
</header>"""

CSS = """<style>
body{font-size:1.04rem;line-height:1.72}
.container{width:min(760px,100% - 2*clamp(1.25rem,5vw,3rem))}
.mono{font-size:.7rem}
header.page{padding:7.9rem 0 2.2rem}
.eyebrow{color:var(--gold);margin-bottom:1.1rem;display:flex;flex-wrap:wrap;gap:.5rem 1.4rem;align-items:baseline}
h1.q{font-weight:520;font-size:clamp(1.85rem,4.7vw,2.9rem);line-height:1.12;margin:0 0 1.2rem;letter-spacing:-.018em}
.standfirst{font-family:var(--serif);font-size:1.12rem;color:var(--ink);line-height:1.6;max-width:40em;border-left:2px solid var(--gold);padding-left:1.1rem}
.gsec{border-top:1px solid var(--line);padding:1.7rem 0 .4rem;margin-top:1.4rem}
.gsec .glabel{display:flex;gap:.9rem;align-items:baseline;margin-bottom:.7rem}
.gsec .gno{font-family:var(--mono);font-size:.66rem;letter-spacing:.09em;color:var(--muted)}
.gsec .gname{font-family:var(--mono);font-size:.7rem;letter-spacing:.09em;text-transform:uppercase;color:var(--gold)}
.gsec p{color:var(--ink);max-width:62ch}
.gsec ul{margin:.2rem 0 1em;padding-left:1.15rem;color:var(--ink);max-width:62ch}
.gsec li{margin:.4rem 0}
.kill{border:1px solid var(--review);border-left:3px solid var(--review);background:var(--surface);padding:1.1rem 1.2rem;margin:.2rem 0 1rem}
.kill .cond{font-family:var(--serif);font-size:1.06rem;line-height:1.55;margin:0 0 .8rem;max-width:52ch;color:var(--ink)}
.kill .conseq{display:inline-flex;gap:.6rem;align-items:baseline;font-family:var(--mono);font-size:.66rem;letter-spacing:.09em;text-transform:uppercase}
.kill .conseq b{color:var(--review);font-weight:400;border:1px solid var(--review);padding:.18rem .5rem}
.empty-list{color:var(--muted);font-size:.92rem}
.meta-grid{display:grid;grid-template-columns:10rem 1fr;gap:.5rem 1.2rem;margin:0;font-size:.93rem}
.meta-grid dt{font-family:var(--mono);font-size:.62rem;letter-spacing:.08em;text-transform:uppercase;color:var(--gold);padding-top:.2rem}
.meta-grid dd{margin:0;color:var(--muted);overflow-wrap:anywhere}
.dims{display:flex;flex-wrap:wrap;gap:.4rem .9rem}
.dim{display:inline-flex;gap:.45rem;align-items:baseline}
.dim-k{font-family:var(--mono);font-size:.6rem;letter-spacing:.07em;text-transform:uppercase;color:var(--muted)}
.tag{border:1px solid var(--line-strong);padding:.1rem .42rem;margin-right:.4rem}
.tag-exec{color:var(--evidence);border-color:var(--evidence)}
.tag-manual{color:var(--muted)}
.trg{list-style:none;padding-left:0}
.verdict{border:1px solid var(--invalid);color:var(--invalid);padding:.18rem .5rem;font-family:var(--mono);font-size:.62rem;letter-spacing:.09em}
.claim-nav{display:flex;flex-wrap:wrap;gap:1.4rem;justify-content:space-between;border-top:1px solid var(--line);margin-top:2.6rem;padding-top:1.3rem}
.claim-nav a{color:var(--muted);text-decoration:none;border-bottom:1px solid var(--line-strong);padding-bottom:1px}
.claim-nav a:hover{color:var(--ink)}
.idx{list-style:none;margin:0;padding:0;border-top:1px solid var(--line)}
.idx li{border-bottom:1px solid var(--line)}
.idx a{display:grid;grid-template-columns:6.5rem 1fr auto;gap:.6rem 1.2rem;align-items:baseline;padding:1rem .2rem;text-decoration:none;transition:background-color .18s}
.idx a:hover,.idx a:focus-visible{background:var(--surface)}
.idx .cid{font-family:var(--mono);font-size:.68rem;letter-spacing:.09em;color:var(--gold)}
.idx .ctitle{color:var(--ink);line-height:1.45}
.idx .cexp{font-family:var(--mono);font-size:.62rem;letter-spacing:.06em;color:var(--muted);white-space:nowrap}
.terms{list-style:none;margin:0;padding:0}
.terms li{border-top:1px solid var(--line);padding:1.3rem 0}
.terms .tname{font-family:var(--mono);font-size:.82rem;color:var(--evidence);letter-spacing:.04em}
.terms .trange{font-family:var(--mono);font-size:.62rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-left:.8rem}
.terms .tgloss{font-family:var(--serif);font-size:1.06rem;color:var(--ink);margin:.55rem 0 .5rem;max-width:52ch}
.terms .tnote{color:var(--muted);font-size:.95rem;max-width:62ch;margin:0 0 .5rem}
.terms .tsrc{font-family:var(--mono);font-size:.62rem;letter-spacing:.06em;color:var(--muted)}
pre.ex{background:var(--surface);border:1px solid var(--line-strong);padding:1rem 1.1rem;overflow-x:auto;font-family:var(--mono);font-size:.74rem;line-height:1.7;color:var(--ink)}
footer{border-top:1px solid var(--line);margin-top:3.5rem;padding:2rem 0 3rem;color:var(--muted);font-size:.85rem}
.foot-links{display:flex;flex-wrap:wrap;gap:1.4rem;margin-bottom:1rem}
@media (max-width:600px){.meta-grid{grid-template-columns:1fr}.meta-grid dt{padding-top:.5rem}.idx a{grid-template-columns:1fr}}
@media print{body{background:#fff;color:#000}}
</style>"""

HEAD = """<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="{ogtype}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{ogimg}">
<meta property="og:image:alt" content="{ogalt}">
<meta property="og:site_name" content="Cubits11">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{ogimg}">
<meta name="twitter:image:alt" content="{ogalt}">
<meta name="robots" content="max-image-preview:large">
<meta name="theme-color" media="(prefers-color-scheme: light)" content="#F1EDE2">
<meta name="theme-color" media="(prefers-color-scheme: dark)" content="#0B0F0A">
<link rel="icon" href="{icon}">
{boot}
<link rel="stylesheet" href="/assets/site.css">
{ld}
{css}
<script defer src="/assets/site.js"></script>
</head>
<body>
"""


def head(title: str, desc: str, route: str, ogtype: str, ld_blocks: list[dict]) -> str:
    ld = "\n".join(
        '<script type="application/ld+json">\n'
        + json.dumps(block, indent=2, ensure_ascii=False).replace("<", "\\u003c")
        + "\n</script>"
        for block in ld_blocks)
    return HEAD.format(title=html.escape(title), desc=html.escape(desc),
                       canonical=f"{SITE}{route}", ogtype=ogtype,
                       ogimg=OG_IMAGE, ogalt=html.escape(OG_ALT), icon=ICON,
                       boot=THEME_BOOT, ld=ld, css=CSS)


def footer(links: list[tuple[str, str]], note: str = "") -> str:
    items = "".join(f'<a class="u" href="{href}">{html.escape(text)}</a>'
                    for href, text in links)
    tail = f'<span class="mono">{html.escape(note)}</span>' if note else ""
    return (f'<footer>\n  <div class="container">\n'
            f'    <div class="foot-links mono">{items}</div>\n'
            f'    {tail}\n  </div>\n</footer>\n{THEME_JS}\n</body>\n</html>\n')


def breadcrumbs(trail: list[tuple[str, str | None]]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {k: v for k, v in (("@type", "ListItem"), ("position", i),
                               ("name", name), ("item", url)) if v is not None}
            for i, (name, url) in enumerate(trail, start=1)
        ],
    }


PERSON = {
    "@type": "Person",
    "@id": f"{SITE}/#person",
    "name": "Pranav Bhave",
    "url": f"{SITE}/",
    "sameAs": [
        "https://github.com/Cubits11",
        "https://www.linkedin.com/in/pranav-bhave-2a328721a/",
        "https://x.com/PranavBhave_",
    ],
}


def claim_ld(claim: dict, title: str, desc: str) -> dict:
    """One schema.org Claim, carrying its kill condition in the same object.

    The context is an array: schema.org first, then the falsifiable-web
    prefix. Custom properties have explicit mappings from the published vocabulary.
    Whether an application interprets or quotes those fields is outside this
    renderer's control.
    """
    cid = claim["id"]
    support = claim.get("support") or {}
    stamp, stamp_date = verdict_of(claim)
    node: dict = {
        "@context": ["https://schema.org", vocabulary_context()],
        "@type": "Claim",
        "@id": f"{SITE}{route_of(cid)}#claim",
        "identifier": cid,
        "name": title,
        "description": desc,
        "text": squash(claim["proposition"]),
        "url": f"{SITE}{route_of(cid)}",
        "author": PERSON,
        "isPartOf": {
            "@type": "Dataset",
            "@id": f"{SITE}/ledger/#dataset",
            "name": "Cubits11 claim registry",
            "url": f"{SITE}/ledger/",
        },
        "dateModified": str(claim["last_reviewed"]),
        "fw:scopeStatement": squash(claim["scope"]),
        "fw:falsifier": squash(claim["falsifier"]["condition"]),
        "fw:consequence": claim["falsifier"]["consequence"],
        "fw:forbiddenRescue": [squash(r) for r in claim.get("forbidden_rescues", [])],
        "fw:nonClaim": [squash(n) for n in claim.get("non_claims", [])],
        "fw:lastReviewed": str(claim["last_reviewed"]),
        "fw:reviewWindow": f"P{int(claim['review_window_days'])}D",
        "fw:warrantExpires": expiry_of(claim),
        "fw:evidentialStatus": claim["dimensions"]["evidential_status"],
    }
    if support.get("url"):
        node["fw:supportUrl"] = {"@id": support["url"]}
        if support.get("commit") and support["commit"] in support["url"]:
            node["fw:supportBinding"] = {"@id": support["url"]}
    if support.get("commit"):
        node["fw:boundRevision"] = support["commit"]
    if stamp:
        node["fw:verdict"] = stamp
        node["fw:verdictDate"] = stamp_date
    return node


def render_claim_page(claim: dict, prev: dict | None, nxt: dict | None,
                      position: int, total: int) -> str:
    cid = claim["id"]
    title_short = TITLES[cid]
    title = f"{cid} · {title_short}"
    desc = description_of(claim, title_short)
    route = route_of(cid)
    dims = claim["dimensions"]
    stamp, stamp_date = verdict_of(claim)
    expiry = expiry_of(claim)

    rescues = claim.get("forbidden_rescues", [])
    rescue_html = (
        "<ul>" + "".join(f"<li>{esc(r)}</li>" for r in rescues) + "</ul>"
        if rescues else
        '<p class="empty-list"><code>[]</code> — the registry declares that no '
        'meaningful post-falsification rescue is available for this claim.</p>')
    non_claims = claim.get("non_claims", [])
    non_claim_html = (
        "<ul>" + "".join(f"<li>{esc(n)}</li>" for n in non_claims) + "</ul>"
        if non_claims else
        '<p class="empty-list">None declared.</p>')

    trigger_groups: dict[tuple[str, str], int] = {}
    for trigger in claim.get("review_triggers", []):
        key = (str(trigger.get("enforcement", "manual")),
               str(trigger.get("note") or trigger.get("event") or trigger.get("type")))
        trigger_groups[key] = trigger_groups.get(key, 0) + 1
    triggers = "".join(
        '<li><span class="mono tag {cls}">{enf}</span> {desc}</li>'.format(
            cls="tag-exec" if enf == "executable" else "tag-manual",
            enf=esc(enf),
            desc=esc(d if n == 1 else f"{d} ({n} bound sources)"))
        for (enf, d), n in trigger_groups.items())

    support = claim.get("support") or {}
    sup = support_label(support) or "<span class=\"empty-list\">None public.</span>"
    sup_note = f'<br><span class="empty-list">{esc(support["note"])}</span>' \
        if support.get("note") else ""
    dim_html = "".join(
        f'<span class="dim"><span class="dim-k">{esc(k)}</span>{esc(label(v))}</span>'
        for k, v in (("visibility", dims["visibility"]),
                     ("provenance", dims["provenance"]),
                     ("support role", dims["support_role"]),
                     ("maturity", dims["maturity"])))

    verdict_html = (f'<span class="verdict">{esc(stamp)} {esc(stamp_date)}</span>'
                    if stamp else "")

    ld = [claim_ld(claim, title_short, desc),
          breadcrumbs([("The record", f"{SITE}/"),
                       ("Claims", f"{SITE}/claims/"),
                       (cid, None)])]

    nav = []
    if prev:
        nav.append(f'<a href="{route_of(prev["id"])}">← {esc(prev["id"])} '
                   f'{esc(TITLES[prev["id"]])}</a>')
    else:
        nav.append("<span></span>")
    if nxt:
        nav.append(f'<a href="{route_of(nxt["id"])}">{esc(nxt["id"])} '
                   f'{esc(TITLES[nxt["id"]])} →</a>')

    return (BANNER + head(title, desc, route, "article", ld) + SITE_HEAD + f"""
<div class="class-bar mono">
  <div class="container">
    <span>Claim <b>{esc(cid)}</b> — {position} of {total} in the <a class="u" href="/claims/">registry</a></span>
    <span class="status">{esc(status_of(claim))}</span>
  </div>
</div>
<header class="page">
  <div class="container">
    <p class="eyebrow mono"><span>{esc(cid)}</span>{verdict_html}<span>Warrant reviewed {esc(claim["last_reviewed"])} · expires {esc(expiry)}</span></p>
    <h1 class="q">{esc(title_short)}</h1>
    <p class="standfirst">{esc(claim["proposition"])}</p>
  </div>
</header>
<main class="container" id="main">
  <section class="gsec">
    <div class="glabel"><span class="gno">01</span><span class="gname">Falsifier — what changes this claim</span></div>
    <div class="kill">
      <p class="cond">{esc(claim["falsifier"]["condition"])}</p>
      <span class="conseq">Consequence <b>{esc(claim["falsifier"]["consequence"])}</b></span>
    </div>
    <p>This is the condition and consequence recorded in the registry. <a class="u" href="/ns/falsifiable/v1/">The vocabulary this is published in</a> defines what each consequence commits the author to.</p>
  </section>
  <section class="gsec">
    <div class="glabel"><span class="gno">02</span><span class="gname">Scope</span></div>
    <p>{esc(claim["scope"])}</p>
  </section>
  <section class="gsec">
    <div class="glabel"><span class="gno">03</span><span class="gname">Forbidden rescues</span></div>
    <p>Repairs declared unavailable in advance; using one after a failure would breach the recorded commitment.</p>
    {rescue_html}
  </section>
  <section class="gsec">
    <div class="glabel"><span class="gno">04</span><span class="gname">Non-claims — what this does not license</span></div>
    {non_claim_html}
  </section>
  <section class="gsec">
    <div class="glabel"><span class="gno">05</span><span class="gname">Binding and freshness</span></div>
    <dl class="meta-grid">
      <dt>Binding</dt><dd>{sup}{sup_note}</dd>
      <dt>Reviewed</dt><dd>{esc(claim["last_reviewed"])} · window {esc(claim["review_window_days"])} days</dd>
      <dt>Expires</dt><dd>{esc(expiry)} — after this date the recorded review is overdue; this does not make the claim false</dd>
      <dt>Triggers</dt><dd><ul class="trg">{triggers}</ul></dd>
      <dt>Dimensions</dt><dd><span class="dims">{dim_html}</span></dd>
    </dl>
  </section>
  <nav class="claim-nav mono" aria-label="Adjacent claims">{"".join(nav)}</nav>
</main>
""" + footer([("/claims/", "All claims"), ("/ledger/", "Evidence ledger"),
              ("/observatory/", "Observatory"),
              ("/ns/falsifiable/v1/", "Falsifiable-web vocabulary"),
              ("/", "The record")],
             "Claim text and qualifications come from claims.yaml; titles and navigation are editorial."))


def render_index(claims: list[dict]) -> str:
    title = "Claims — registered propositions and their falsifiers"
    desc = (f"The {len(claims)} registered claims, each with an address, a falsifier, "
            "a fixed consequence, the rescues declared unavailable, and the "
            "date its warrant expires.")
    rows = "".join(
        f'<li><a href="{route_of(c["id"])}">'
        f'<span class="cid">{esc(c["id"])}</span>'
        f'<span class="ctitle">{esc(TITLES[c["id"]])}</span>'
        f'<span class="cexp">expires {esc(expiry_of(c))}</span></a></li>'
        for c in claims)
    ld = [
        {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "@id": f"{SITE}/claims/#page",
            "name": title,
            "description": desc,
            "url": f"{SITE}/claims/",
            "author": PERSON,
            "isPartOf": {"@type": "WebSite", "@id": f"{SITE}/#website"},
            "mainEntity": {
                "@type": "ItemList",
                "numberOfItems": len(claims),
                "itemListOrder": "https://schema.org/ItemListUnordered",
                "itemListElement": [
                    {"@type": "ListItem", "position": i,
                     "url": f"{SITE}{route_of(c['id'])}",
                     "name": f"{c['id']} · {TITLES[c['id']]}"}
                    for i, c in enumerate(claims, start=1)
                ],
            },
        },
        breadcrumbs([("The record", f"{SITE}/"), ("Claims", None)]),
    ]
    return (BANNER + head(title, desc, "/claims/", "website", ld) + SITE_HEAD + f"""
<header class="page">
  <div class="container">
    <p class="eyebrow mono"><span>The registry, one claim per address</span></p>
    <h1 class="q">Registered claims and their falsifiers</h1>
    <p class="standfirst">{len(claims)} claims. Each one carries its declared falsifier, the consequence fixed in advance, the repairs declared unavailable, and the date after which its warrant is stale. None of that is a summary of the claim — it is the claim's own record, rendered.</p>
  </div>
</header>
<main class="container" id="main">
  <section class="gsec">
    <div class="glabel"><span class="gno">01</span><span class="gname">The registry</span></div>
    <ul class="idx">{rows}</ul>
  </section>
  <section class="gsec">
    <div class="glabel"><span class="gno">02</span><span class="gname">How to read a date here</span></div>
    <p>The expiry date is not a prediction that a claim will go wrong. It is the end of the review window recorded in the registry. A claim past its window is due, not false — and this site's CI fails the build rather than let a lapsed window pass quietly.</p>
    <p>The same registry renders three ways: as <a class="u" href="/ledger/">one ledger</a>, as <a class="u" href="/observatory/">decay clocks</a>, and here as one page per claim. One source, three bandwidths.</p>
  </section>
  <section class="gsec">
    <div class="glabel"><span class="gno">03</span><span class="gname">Machine-readable</span></div>
    <p>Every claim page carries a schema.org <code>Claim</code> node whose falsifier, consequence, forbidden rescues and non-claims travel in the same object, under <a class="u" href="/ns/falsifiable/v1/">a published vocabulary</a>. An agent that quotes a claim from this site has already been handed the condition under which the claim is withdrawn.</p>
    <p>The whole registry as one JSON document: <a class="u" href="/claims/index.json"><code>/claims/index.json</code></a>.</p>
  </section>
</main>
""" + footer([("/ledger/", "Evidence ledger"), ("/observatory/", "Observatory"),
              ("/ns/falsifiable/v1/", "Falsifiable-web vocabulary"),
              ("/corrections/", "Corrections"), ("/", "The record")],
             "Generated from claims.yaml — CI fails on drift."))


def render_namespace() -> str:
    title = "The falsifiable-web vocabulary — fw: v1"
    desc = (f"A local vocabulary of {len(TERMS)} JSON-LD properties for claim scope, "
            "falsifiers, consequences, review dates and support bindings. "
            "Definitions and examples from the registry.")
    terms = "".join(
        f'<li id="{esc(t["term"])}"><p><span class="tname">fw:{esc(t["term"])}</span>'
        f'<span class="trange">{esc(t["range"])}</span></p>'
        f'<p class="tgloss">{esc(t["gloss"])}</p>'
        f'<p class="tnote">{esc(t.get("note", ""))}</p>'
        f'<p class="tsrc">SOURCE · {esc(t["source"])}</p></li>'
        for t in TERMS)
    example_claim = next(c for c in load_claims() if c["id"] == "CC-004")
    example_node = claim_ld(example_claim, TITLES["CC-004"],
                            description_of(example_claim, TITLES["CC-004"]))
    example_node = {k: v for k, v in example_node.items()
                    if k in {"@type", "identifier", "text", "fw:falsifier", "fw:consequence", "fw:forbiddenRescue", "fw:nonClaim", "fw:warrantExpires"}}
    example_node = {"@context": ["https://schema.org", f"{NS}/context.json"], **example_node}
    example = json.dumps(example_node, indent=2, ensure_ascii=False)
    ld = [
        {
            "@context": "https://schema.org",
            "@type": "DefinedTermSet",
            "@id": f"{NS}/#vocabulary",
            "name": "Falsifiable-web vocabulary, version 1",
            "description": desc,
            "url": f"{NS}/",
            "author": PERSON,
            "hasDefinedTerm": [
                {"@type": "DefinedTerm", "@id": f"{NS}/#{t['term']}",
                 "termCode": f"fw:{t['term']}", "name": t["term"],
                 "description": t["gloss"]}
                for t in TERMS
            ],
        },
        breadcrumbs([("The record", f"{SITE}/"), ("Vocabulary", None)]),
    ]
    return (BANNER + head(title, desc, "/ns/falsifiable/v1/", "article", ld)
            + SITE_HEAD + f"""
<div class="class-bar mono">
  <div class="container">
    <span>Namespace <b>fw:</b> — <code>{NS}/#</code></span>
    <span class="status">Version 1</span>
  </div>
</div>
<header class="page">
  <div class="container">
    <p class="eyebrow mono"><span>A JSON-LD vocabulary</span></p>
    <h1 class="q">{len(TERMS)} properties for a claim and its qualifications</h1>
    <p class="standfirst">Schema.org can express that a document contains a claim. It cannot express the observation that would withdraw the claim, what the author has undertaken to do when that observation arrives, or which repairs the author has declared unavailable in advance. Those are the properties this site needs, so this site defines them.</p>
  </div>
</header>
<main class="container" id="main">
  <section class="gsec">
    <div class="glabel"><span class="gno">01</span><span class="gname">What this is not</span></div>
    <p>This is not a standard. It is one publisher's vocabulary, versioned, with exactly one implementation — the <a class="u" href="/claims/">{len(load_claims())} claim pages</a> on this site. It is published because a JSON-LD prefix that does not resolve is a prefix nobody can check, not because anyone else has adopted it.</p>
    <p>Custom properties do not promise a search enhancement or enforce quotation. They make the qualifications available beside the proposition. A consumer can still ignore or omit them; this vocabulary does not prevent that.</p>
  </section>
  <section class="gsec">
    <div class="glabel"><span class="gno">02</span><span class="gname">The terms</span></div>
    <ul class="terms">{terms}</ul>
  </section>
  <section class="gsec">
    <div class="glabel"><span class="gno">03</span><span class="gname">Use</span></div>
    <p>Use the published context alongside schema.org. JSON-LD consumers can preserve the custom properties; applications decide whether to interpret them:</p>
    <pre class="ex">{esc(example)}</pre>
    <p>The context document: <a class="u" href="/ns/falsifiable/v1/context.json"><code>/ns/falsifiable/v1/context.json</code></a>. Both it and this page are generated from the same constants that render the claim pages, so a term cannot be defined here and emitted differently there.</p>
  </section>
  <section class="gsec">
    <div class="glabel"><span class="gno">04</span><span class="gname">Stability</span></div>
    <p>Version 1 terms will not change meaning under this URL. A term whose meaning has to change gets a new version path. A term that turns out to be unused gets deleted from version 2 and stays resolvable at version 1, because a namespace that breaks its own old documents teaches publishers not to use namespaces.</p>
  </section>
</main>
""" + footer([("/claims/", "All claims"), ("/ledger/", "Evidence ledger"),
              ("/ns/falsifiable/v1/context.json", "context.json"),
              ("/", "The record")],
             "Generated from scripts/generate_claims_pages.py — CI fails on drift."))


def render_context() -> str:
    return json.dumps({"@context": vocabulary_context()}, indent=2,
                      ensure_ascii=False) + "\n"


def render_json(claims: list[dict]) -> str:
    """The whole registry as one document, for a reader that is not a browser."""
    return json.dumps({
        "@context": ["https://schema.org", vocabulary_context()],
        "@type": "DataFeed",
        "@id": f"{SITE}/claims/index.json",
        "name": "Cubits11 claim registry",
        "description": ("Every registered claim, each with its falsifier, "
                        "the consequence fixed in advance, the rescues "
                        "declared unavailable, and the date its warrant "
                        "expires."),
        "url": f"{SITE}/claims/",
        "author": PERSON,
        "dateModified": max(str(c["last_reviewed"]) for c in claims),
        "dataFeedElement": [claim_ld(c, TITLES[c["id"]],
                                     description_of(c, TITLES[c["id"]]))
                            for c in claims],
    }, indent=2, ensure_ascii=False) + "\n"


# ---------------------------------------------------------------------------
# drive
# ---------------------------------------------------------------------------

def check_vocabulary(nodes: list[dict]) -> None:
    declared = {f"fw:{term['term']}" for term in TERMS}
    context = vocabulary_context()
    for node in nodes:
        for key in node:
            if key.startswith("fw:") and key not in declared:
                fail(f"undocumented custom property: {key}")
        if node.get("@context") != ["https://schema.org", context]:
            fail("claim context differs from the published vocabulary")


def self_test() -> int:
    claims = load_claims()
    check_titles_grounded(claims)
    assert not failures, failures
    nodes = [claim_ld(c, TITLES[c["id"]], description_of(c, TITLES[c["id"]])) for c in claims]
    check_vocabulary(nodes)
    assert not failures, failures
    # Mutation: the old lexical gate accepted arbitrary replacement numerals.
    original = TITLES["MC-001"]
    try:
        TITLES["MC-001"] = original.replace("20", "999")
        check_titles_grounded(claims)
        assert any("numerals" in f for f in failures), failures
    finally:
        TITLES["MC-001"] = original
        failures.clear()
    # Mutation: sharing a word prefix is not a license to invent terminology.
    original = TITLES["CC-001"]
    try:
        TITLES["CC-001"] = "Marginalsuperiority bounds"
        check_titles_grounded(claims)
        assert any("marginalsuperiority" in f for f in failures), failures
    finally:
        TITLES["CC-001"] = original
        failures.clear()
    mutated = copy.deepcopy(nodes[0])
    mutated["fw:undocumented"] = "must fail"
    check_vocabulary([mutated])
    assert any("undocumented" in f for f in failures), failures
    failures.clear()
    mutable = next(c for c in claims if c.get("support", {}).get("url") and not c["support"].get("commit"))
    node = claim_ld(mutable, "test", "test")
    assert "fw:supportUrl" in node and "fw:supportBinding" not in node
    assert vocabulary_context()["fw:forbiddenRescue"]["@container"] == "@list"
    assert vocabulary_context()["fw:lastReviewed"]["@type"] == "xsd:date"
    assert json.loads(render_context())["@context"] == vocabulary_context()
    for node in nodes:
        assert node["fw:scopeStatement"]
        assert isinstance(node["fw:nonClaim"], list)
        if "fw:supportBinding" in node:
            assert node["fw:boundRevision"] in node["fw:supportBinding"]["@id"]
    dangerous = head("test", "test", "/claims/", "article", [{"text": "</script><script>alert(1)</script>"}])
    assert "<script>alert(1)" not in dangerous
    print("ok    claim metadata: title mutations, vocabulary coverage, typed dates, explicit lists, mutable support and script escaping")
    return 0


def build() -> dict[pathlib.Path, str]:
    failures.clear()
    claims = load_claims()
    check_titles_grounded(claims)
    if failures:
        return {}
    out: dict[pathlib.Path, str] = {
        ROOT / "claims" / "index.html": render_index(claims),
        ROOT / "claims" / "index.json": render_json(claims),
        ROOT / "ns" / "falsifiable" / "v1" / "index.html": render_namespace(),
        ROOT / "ns" / "falsifiable" / "v1" / "context.json": render_context(),
    }
    check_vocabulary([claim_ld(c, TITLES[c["id"]], description_of(c, TITLES[c["id"]])) for c in claims])
    total = len(claims)
    for i, claim in enumerate(claims):
        out[ROOT / "claims" / claim["id"].lower() / "index.html"] = render_claim_page(
            claim,
            claims[i - 1] if i else None,
            claims[i + 1] if i + 1 < total else None,
            i + 1, total)
    return out


def main() -> int:
    artifacts = build()
    if failures:
        for message in failures:
            print(f"FAIL  {message}")
        print(f"\n{len(failures)} check(s) failed.")
        return 1
    check = "--check" in sys.argv
    drifted: list[str] = []
    for path, content in artifacts.items():
        rel = path.relative_to(ROOT).as_posix()
        if check:
            current = path.read_text(encoding="utf-8") if path.exists() else ""
            if current != content:
                drifted.append(rel)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    if check:
        if drifted:
            print("DRIFT: generated claim surfaces do not match claims.yaml:")
            for rel in drifted:
                print(f"  {rel}")
            print("Run: python scripts/generate_claims_pages.py")
            return 1
        print(f"ok    {len(artifacts)} claim surfaces match the registry")
        return 0
    print(f"wrote {len(artifacts)} files "
          f"({len(artifacts) - 4} claim pages, an index, a JSON feed, "
          f"and the fw: vocabulary)")
    return 0


if __name__ == "__main__":
    sys.exit(self_test() if "--test" in sys.argv else main())
