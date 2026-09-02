#!/usr/bin/env python3
"""Cheap, deterministic structural gates for the public frontend.

This is deliberately not a substitute for assistive-technology testing. It
protects the invariants that a static build can verify every push: an actual
landmark/skip path, one page title heading, no duplicate IDs, a responsive
viewport, accessible images, and the local-only contract of Stack Study
Preflight. Browser and keyboard review remain release work.
"""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Audit(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.h1_count = 0
        self.main_ids: list[str | None] = []
        self.images_without_alt = 0
        self.has_skip = False
        self.has_viewport = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(str(values["id"]))
        if tag == "h1":
            self.h1_count += 1
        if tag == "main":
            self.main_ids.append(values.get("id"))
        if tag == "img" and "alt" not in values:
            self.images_without_alt += 1
        if tag == "meta" and values.get("name") == "viewport":
            content = values.get("content") or ""
            self.has_viewport = "width=device-width" in content and "user-scalable=no" not in content
        if tag == "a" and values.get("class") and "skip" in values["class"].split():
            self.has_skip = values.get("href") == "#main"


def page_files() -> list[Path]:
    return sorted(
        p for p in ROOT.rglob("*.html")
        if ".git" not in p.parts and "docs" not in p.parts
        and "scripts" not in p.parts and ".venv" not in p.parts
        and "films" not in p.parts  # canvas films are not site pages; scripts/films/verify_films.py audits them
    )


def audit_page(page: Path) -> list[str]:
    html = page.read_text(encoding="utf-8")
    parser = Audit()
    parser.feed(html)
    errors: list[str] = []
    rel = page.relative_to(ROOT).as_posix()
    if not re.search(r'<html\s+[^>]*\blang=["\']en["\']', html, re.I):
        errors.append(f"{rel}: missing lang=en")
    if not parser.has_viewport:
        errors.append(f"{rel}: missing safe responsive viewport")
    if not parser.has_skip:
        errors.append(f"{rel}: missing Skip to content link to #main")
    if parser.h1_count != 1:
        errors.append(f"{rel}: expected exactly one h1, found {parser.h1_count}")
    if parser.main_ids != ["main"]:
        errors.append(f"{rel}: expected exactly one <main id=main>, found {parser.main_ids}")
    repeated = sorted({item for item in parser.ids if parser.ids.count(item) > 1})
    if repeated:
        errors.append(f"{rel}: duplicate id(s): {', '.join(repeated)}")
    if parser.images_without_alt:
        errors.append(f"{rel}: {parser.images_without_alt} image(s) without alt")
    if 'class="site-head"' in html and '/assets/site.js' not in html:
        errors.append(f"{rel}: site header lacks shared responsive-navigation behavior")
    return errors



# A container that scrolls horizontally is unreachable to a keyboard unless it
# is focusable, and unnamed to a screen reader unless it carries an accessible
# name. Both are cheap to assert and easy to forget when a new figure lands.
SCROLLERS = ("fig-scroll", "guard-wrap")


def audit_scroll_regions(page: Path) -> list[str]:
    html = page.read_text(encoding="utf-8")
    rel = page.relative_to(ROOT).as_posix()
    errors: list[str] = []
    for cls in SCROLLERS:
        for match in re.finditer(rf'<div class="{cls}[^"]*"([^>]*)>', html):
            attrs = match.group(1)
            if 'tabindex="0"' not in attrs:
                errors.append(f"{rel}: .{cls} scroll region is not keyboard-focusable (needs tabindex=\"0\")")
            if 'aria-label' not in attrs and 'aria-labelledby' not in attrs:
                errors.append(f"{rel}: .{cls} scroll region has no accessible name")
    for match in re.finditer(r"<pre([^>]*)>", html):
        attrs = match.group(1)
        if "tabindex" in attrs and 'aria-label' not in attrs:
            errors.append(f"{rel}: focusable <pre> has no accessible name")
    return errors


def audit_preflight() -> list[str]:
    errors: list[str] = []
    page = (ROOT / "stack-study" / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "assets" / "stack-study.js").read_text(encoding="utf-8")
    required_page = (
        'id="study-form"',
        'value="shadow_full_exposure"',
        'value="deployed_route"',
        'value="adaptive_holdout"',
        'id="same-items"',
        'id="full-exposure"',
        'id="union-catches"',
        'id="packet"',
    )
    for needle in required_page:
        if needle not in page:
            errors.append(f"stack-study/index.html: required preflight field missing: {needle}")
    required_logic = (
        'Math.max(0, n - sum)',
        'var upper = n - max',
        'buildNonStaticPacket',
        'This mode intentionally emits no static stack result',
        'navigator.clipboard.writeText',
        # Counts past 2^53-1 silently lose precision, so the bounds this tool
        # prints would stop being the bounds it claims to compute.
        'Number.isSafeInteger',
        "/^[+-]?[0-9]+$/",
        # An error announced politely can be missed entirely.
        "isError ? 'alert' : 'status'",
        "isError ? 'assertive' : 'polite'",
    )
    for needle in required_logic:
        if needle not in script:
            errors.append(f"assets/stack-study.js: required safety behavior missing: {needle}")
    blocked_transport = ("fetch(", "XMLHttpRequest", "sendBeacon(")
    for needle in blocked_transport:
        if needle in script:
            errors.append(f"assets/stack-study.js: local-only tool must not contain {needle}")
    return errors


def main() -> int:
    errors: list[str] = []
    for page in page_files():
        errors.extend(audit_page(page))
        errors.extend(audit_scroll_regions(page))
    errors.extend(audit_preflight())
    if errors:
        for error in errors:
            print(f"FAIL  {error}")
        return 1
    print(f"ok    frontend structural gates passed ({len(page_files())} pages; local preflight checked; scroll regions keyboard-reachable)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
