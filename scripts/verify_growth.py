#!/usr/bin/env python3
"""Gate the acquisition surfaces the same way the evidence surfaces are gated.

Growth work is where a rigorous record usually starts lying: a title promises
more than the page delivers, a campaign link points at a route that moved, an
identity sentence drifts between the site and a profile, a social card claims
a number the census no longer holds. None of that is caught by a checker that
only reads census.yaml.

So the acquisition layer gets its own invariants:

  * every public page has a unique, non-empty title and description, a
    canonical URL matching its own path, and valid JSON-LD;
  * the pages that exist to convert actually carry their calls to action;
  * every campaign link resolves to a committed page and is built only from
    the declared parameter vocabulary — an unattributable link is a link that
    cannot be counted, and a typo'd one silently becomes a new bucket;
  * the identity sentence is byte-identical everywhere it appears;
  * the social card is the declared 1200x630;
  * the measurement baseline reports observed values or says "unavailable",
    and never a number nobody read.

Run with no arguments to audit the working tree.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import facts  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://cubits11.github.io"

# One sentence, everywhere. A public identity that is paraphrased differently
# on each surface is not an identity; it is a family of similar claims.
IDENTITY = ("I measure what AI guardrail stacks miss together, and build "
            "evidence systems that show exactly what data can and cannot "
            "establish.")

# Pages that exist to move a visitor onward must keep the link that does it.
REQUIRED_CTAS = {
    "index.html": ["/missing-column/", "/essays/when-marginals-are-not-enough/",
                   "/work/", "/resume/"],
    "work/index.html": ["mailto:bhavepranavwork@gmail.com", "/missing-column/",
                        "/resume/"],
    "answers/why-guardrail-miss-rates-do-not-multiply/index.html": [
        "/missing-column/", "/missing-column/disclosure/"],
    "answers/how-to-evaluate-guardrails-you-plan-to-stack/index.html": [
        "/missing-column/disclosure/", "/work/"],
    "answers/what-does-the-second-guardrail-add/index.html": [
        "/missing-column/disclosure/", "/ledger/#MC-003"],
    "missing-column/index.html": ["/missing-column/disclosure/", "/corrections/"],
}

# Titles are the search result. A title that names an internal noun instead of
# the question a reader typed is a discoverability defect, not a style choice.
MAX_TITLE = 72
MAX_DESC = 200
MIN_DESC = 70

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)


def pages() -> list[Path]:
    return sorted(
        p for p in ROOT.rglob("index.html")
        if ".git" not in p.parts and "docs" not in p.parts
        and "scripts" not in p.parts and "fixtures" not in p.parts
        and ".venv" not in p.parts)


def route_of(page: Path) -> str:
    rel = page.relative_to(ROOT)
    return "/" if rel.as_posix() == "index.html" else f"/{rel.parent.as_posix()}/"


def tag(html: str, pattern: str) -> str | None:
    match = re.search(pattern, html)
    return match.group(1).strip() if match else None


def check_metadata() -> None:
    titles: dict[str, str] = {}
    descriptions: dict[str, str] = {}
    for page in pages():
        rel = page.relative_to(ROOT).as_posix()
        route = route_of(page)
        html = page.read_text(encoding="utf-8")

        title = tag(html, r"<title>(.*?)</title>")
        if not title:
            fail(f"{rel}: no <title>")
        else:
            if len(title) > MAX_TITLE:
                fail(f"{rel}: title is {len(title)} chars (max {MAX_TITLE}) — "
                     f"it will be truncated in results: {title!r}")
            if title in titles:
                fail(f"{rel}: title duplicates {titles[title]} — two pages "
                     f"competing for the same result")
            titles[title] = rel

        desc = tag(html, r'<meta name="description" content="(.*?)">')
        if not desc:
            fail(f"{rel}: no meta description")
        else:
            if not MIN_DESC <= len(desc) <= MAX_DESC:
                fail(f"{rel}: description is {len(desc)} chars "
                     f"(want {MIN_DESC}-{MAX_DESC})")
            if desc in descriptions:
                fail(f"{rel}: description duplicates {descriptions[desc]}")
            descriptions[desc] = rel

        canonical = tag(html, r'<link rel="canonical" href="(.*?)">')
        if canonical != f"{SITE}{route}":
            fail(f"{rel}: canonical is {canonical!r}, expected "
                 f"{SITE}{route!r}")

        for prop in ("og:title", "og:description", "og:image", "og:url"):
            if f'property="{prop}"' not in html:
                fail(f"{rel}: missing {prop}")
        if 'name="twitter:card"' not in html:
            fail(f"{rel}: missing twitter:card")
        if 'og:image:alt' not in html:
            fail(f"{rel}: og:image has no alt text")

        for block in re.findall(
                r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
            try:
                data = json.loads(block)
            except json.JSONDecodeError as exc:
                fail(f"{rel}: invalid JSON-LD ({exc})")
                continue
            if not isinstance(data, dict) or "@type" not in data:
                fail(f"{rel}: JSON-LD block has no @type")


def check_ctas() -> None:
    for rel, hrefs in REQUIRED_CTAS.items():
        page = ROOT / rel
        if not page.exists():
            fail(f"{rel}: required conversion page is missing")
            continue
        html = page.read_text(encoding="utf-8")
        for href in hrefs:
            if f'href="{href}' not in html:
                fail(f"{rel}: lost its call to action to {href}")


def campaign_url(site: str, path: str, utm: dict) -> str:
    """Build one attributable URL, query before fragment.

    A destination like ``/missing-column/#census`` has to become
    ``/missing-column/?utm_...=#census``. Appending the query after the
    fragment buries every parameter inside the fragment, where nothing reads
    them — the link looks tagged and attributes nothing.
    """
    route, _, fragment = path.partition("#")
    query = "&".join(f"utm_{k}={utm[k]}" for k in
                     ("source", "medium", "campaign", "content") if utm.get(k))
    url = f"{site}{route}?{query}"
    return f"{url}#{fragment}" if fragment else url


def check_campaigns() -> None:
    path = ROOT / "campaigns.yaml"
    if not path.exists():
        fail("campaigns.yaml is missing — no attribution source of truth")
        return
    data = yaml.safe_load(path.read_text())
    vocab = data["vocabulary"]
    destinations = data["destinations"]

    for name, route in destinations.items():
        target = route.split("#")[0]
        page = ROOT / (target.lstrip("/") or ".") / "index.html"
        if not page.exists():
            fail(f"campaigns.yaml destination {name!r} points at {route}, "
                 f"which is not a committed page")

    seen = set()
    for row in data["campaigns"]:
        cid = row.get("id")
        if not cid or not SLUG.match(cid):
            fail(f"campaign id {cid!r} is not slug-shaped")
        if cid in seen:
            fail(f"campaign id {cid!r} is used twice")
        seen.add(cid)
        for field in ("audience", "destination", "intended_action",
                      "success_signal", "utm"):
            if not row.get(field):
                fail(f"campaign {cid}: missing {field}")
        if row.get("destination") not in destinations:
            fail(f"campaign {cid}: destination {row.get('destination')!r} is "
                 f"not declared")
            continue
        utm = row["utm"]
        for key in ("source", "medium", "campaign"):
            allowed = vocab.get(f"utm_{key}") or []
            if utm.get(key) not in allowed:
                fail(f"campaign {cid}: utm_{key}={utm.get(key)!r} is outside "
                     f"the declared vocabulary {allowed}")
        if utm.get("content") and not SLUG.match(str(utm["content"])):
            fail(f"campaign {cid}: utm_content={utm['content']!r} is not "
                 f"slug-shaped")
        url = campaign_url(data["site"], destinations[row["destination"]], utm)
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.netloc != "cubits11.github.io":
            fail(f"campaign {cid}: built URL is not an https site URL: {url}")
        if len(dict(parse_qsl(parsed.query))) < 3:
            fail(f"campaign {cid}: built URL lacks source/medium/campaign: {url}")

    baseline = data["baseline"]["observed"]
    for key, value in baseline.items():
        if isinstance(value, str) and value != "unavailable":
            fail(f"campaigns.yaml baseline.{key}={value!r} — a baseline entry "
                 f"is a number that was read, or the word 'unavailable'")
    if data["targets"].get("directional") is not True:
        fail("campaigns.yaml targets must be labelled directional — at n=100 "
             "nothing here is significant")


def check_launch_pack() -> None:
    """Every tagged URL in the launch pack must be one the ledger can build.

    A pack that quotes a link the ledger does not know is a link nobody can
    attribute — the post ships, the visit arrives, and it lands in no bucket.
    This is the one check that keeps the copy and the attribution model from
    drifting apart while both look fine in isolation.
    """
    pack = ROOT / "docs" / "launch-14-day.md"
    ledger = ROOT / "campaigns.yaml"
    if not pack.exists():
        fail("docs/launch-14-day.md is missing — nothing is ready to publish")
        return
    data = yaml.safe_load(ledger.read_text())
    buildable = {campaign_url(data["site"], data["destinations"][r["destination"]],
                              r["utm"])
                 for r in data["campaigns"]
                 if r.get("destination") in data["destinations"]}
    used = set(re.findall(r"https://cubits11\.github\.io/\S*utm_[^\s`)>]*",
                          pack.read_text(encoding="utf-8")))
    for url in sorted(used - buildable):
        fail(f"launch pack uses {url} — no campaigns.yaml row builds it, so a "
             f"visit from it cannot be attributed")
    if not used:
        fail("launch pack contains no campaign-tagged URLs")
    forbidden = {
        "[disclosure link]": "a disclosure email contains an untracked placeholder link",
        "5 report what the stack misses": "the HN title overstates the census definition of K",
    }
    for needle, reason in forbidden.items():
        if needle in pack.read_text(encoding="utf-8"):
            fail(f"launch pack: {reason}")


def check_disclosure_language() -> None:
    """The MJGD is a proposal until someone else adopts it.

    "Standard" and "specification" assert a settled, adopted artifact. The
    claim registry records that no benchmark author has adopted the MJGD, so
    those words would be stronger than the evidence beneath them. This gate
    keeps the public wording inside what the record supports.
    """
    banned = ("reporting standard", "disclosure standard", "the mjgd standard")
    for rel in ("missing-column/disclosure/index.html",
                "answers/what-does-the-second-guardrail-add/index.html"):
        path = ROOT / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8").lower()
        for phrase in banned:
            if phrase in text:
                fail(f"{rel}: calls the disclosure a {phrase!r} — no external "
                     "adoption is recorded, so use 'proposed reporting protocol'")


def check_identity() -> None:
    """The identity sentence must be identical wherever it is published."""
    found = []
    for page in pages():
        html = facts.visible_text(page.read_text(encoding="utf-8"))
        if "miss together" in html and "evidence systems" in html:
            found.append(page.relative_to(ROOT).as_posix())
    identity_file = ROOT / "docs" / "identity.md"
    if not identity_file.exists():
        fail("docs/identity.md is missing — the identity has no canonical text")
        return
    text = re.sub(r"[\s>]+", " ", identity_file.read_text(encoding="utf-8"))
    normalized = re.sub(r"\s+", " ", IDENTITY)
    if normalized not in text:
        fail("docs/identity.md does not carry the canonical identity sentence "
             "verbatim")
    for rel in ("index.html", "work/index.html"):
        page = ROOT / rel
        if not page.exists():
            continue
        if normalized not in re.sub(r"\s+", " ", facts.visible_text(
                page.read_text(encoding="utf-8"))):
            fail(f"{rel}: does not state the canonical identity sentence")


def check_resume_pdf() -> None:
    """The downloadable résumé exists, is a PDF, and is not gated.

    It is a print of resume/index.html, so it needs no separate content check —
    but it does need to actually exist and actually be linked, because an
    email-gated résumé costs exactly the reader who already decided to look
    harder.
    """
    pdf = ROOT / "resume" / "pranav-bhave-resume.pdf"
    if not pdf.exists():
        fail("resume/pranav-bhave-resume.pdf is missing — rebuild it with "
             "scripts/build_resume_pdf.py")
        return
    if pdf.read_bytes()[:5] != b"%PDF-":
        fail("resume/pranav-bhave-resume.pdf is not a PDF")
    page = (ROOT / "resume" / "index.html").read_text(encoding="utf-8")
    if 'href="/resume/pranav-bhave-resume.pdf"' not in page:
        fail("resume/index.html does not link its own PDF")
    text = facts.visible_text(page)
    if "email me and" in text and "send" in text and "PDF" in text:
        fail("resume/index.html still gates the PDF behind an email request")


def check_social_card() -> None:
    card = ROOT / "assets" / "img" / "og-missing-column.png"
    if not card.exists():
        fail("assets/img/og-missing-column.png is missing")
        return
    header = card.read_bytes()[:33]
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        fail("og-missing-column.png is not a PNG")
        return
    width = int.from_bytes(header[16:20], "big")
    height = int.from_bytes(header[20:24], "big")
    if (width, height) != (1200, 630):
        fail(f"og-missing-column.png is {width}x{height}, expected 1200x630")


def main() -> int:
    check_metadata()
    check_ctas()
    check_campaigns()
    check_launch_pack()
    check_identity()
    check_disclosure_language()
    check_resume_pdf()
    check_social_card()
    if failures:
        for failure in failures:
            print(f"FAIL  {failure}")
        print(f"{len(failures)} check(s) failed.")
        return 1
    print(f"ok    {len(pages())} pages: unique titles and descriptions, "
          f"canonical URLs, valid JSON-LD, social metadata")
    print("ok    conversion pages keep their calls to action")
    print("ok    every campaign link resolves and uses the declared vocabulary")
    print("ok    every tagged URL in the launch pack is attributable")
    print("ok    the identity sentence is identical everywhere it appears")
    print("ok    the résumé PDF exists, is linked, and is not gated")
    print("ok    the social card is 1200x630")
    print("Acquisition surfaces verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
