#!/usr/bin/env python3
"""Measure horizontal overflow and the reduced-motion path in a real browser.

The structural gates in verify_frontend.py read HTML. They cannot see that a
grid item inherited a 38rem min-content floor from a scrollable table and made
the whole page scroll sideways on a phone — which is exactly what happened when
the campaign object moved into the hero, and exactly what a visitor arriving
from a phone would have met first.

So this measures instead of inferring: it lays each page out at real viewport
widths and asks the document for its own scrollWidth.

It also renders with prefers-reduced-motion forced, which is the path where the
reveal animation is disabled entirely. That is both an accessibility check and
the only reliable way to screenshot this site headlessly — the reveal's
rAF-and-timeout choreography does not complete under --virtual-time-budget, so
a motion-enabled capture shows a blank hero that is not what a real visitor
sees.

NOT a CI gate. It needs a browser binary, and adding one to the release
pipeline is a supply-chain decision for the repository owner rather than a
side effect of a layout fix. Run it before a release that touches layout:

    python scripts/check_layout.py                    # find a browser, check
    python scripts/check_layout.py --browser /path    # name one
    python scripts/check_layout.py --shots out/       # also write screenshots
    python scripts/check_layout.py --all              # every route in sitemap.xml

When the Python `playwright` package is importable, pages are laid out in a
device-emulated viewport instead of a --window-size window. That removes the
~485px clamp described at WIDTHS, so 360 and 390 are measured at 360 and 390.
Run against the tree before the overflow-wrap fix, this mode fails
/claims/e7b-001/ and /ns/falsifiable/v1/ at 360px by 16px each (an unbroken
file path; a namespace URL) — pages the clamped run passed. A separate
element-level scan also found /claims/e3b-001/ 5px wide at 360px; the probe's
document-level reading does not show that one.
"""

from __future__ import annotations

import argparse
import http.server
import re
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The widths that matter: a small phone, a large phone, a tablet, a laptop.
#
# Headless Chromium clamps its client width to roughly 485px, so the two phone
# widths below both measure at that floor rather than at 360/390. The check is
# therefore a real guard against page-level horizontal overflow and NOT
# evidence about layout at genuinely narrow widths — each result prints the
# client width it actually measured so the reading cannot be overclaimed.
WIDTHS = (360, 390, 768, 1280)

# Pages a first-time visitor is most likely to land on from a campaign link.
PAGES = ("/", "/missing-column/", "/work/",
         "/answers/why-guardrail-miss-rates-do-not-multiply/",
         "/answers/how-to-evaluate-guardrails-you-plan-to-stack/",
         "/answers/what-does-the-second-guardrail-add/",
         "/resume/", "/essays/when-marginals-are-not-enough/")

CANDIDATES = (
    "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
    "chromium", "chromium-browser", "google-chrome", "google-chrome-stable",
)

# Measured synchronously at end of body: the stylesheets are in <head>, so
# layout is final, and nothing here depends on script that runs later.
PROBE = """<script>
(function(){
  var de = document.documentElement, worst = null, worstW = 0;
  var all = document.querySelectorAll('body *');
  for (var i = 0; i < all.length; i++) {
    var r = all[i].getBoundingClientRect();
    if (r.right > de.clientWidth + 1 && r.width > worstW) {
      worstW = r.width; worst = all[i];
    }
  }
  document.title = 'PROBE|' + de.clientWidth + '|' + de.scrollWidth + '|'
    + (worst ? worst.tagName.toLowerCase() + '.'
        + String(worst.className || '').split(' ')[0] : '-');
})();
</script></body>"""


def find_browser(explicit: str | None) -> str | None:
    for candidate in ([explicit] if explicit else []) + list(CANDIDATES):
        if not candidate:
            continue
        if Path(candidate).is_file():
            return candidate
        found = shutil.which(candidate)
        if found:
            return found
    return None


def build_probe_tree(dest: Path) -> None:
    """Copy the site, injecting the measurement into each checked page."""
    for item in ROOT.iterdir():
        if item.name in {".git", "scripts", "docs"} or item.name.startswith("."):
            continue
        target = dest / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
    for route in PAGES:
        page = dest / (route.strip("/") or ".") / "index.html"
        if page.exists():
            page.write_text(
                page.read_text(encoding="utf-8").replace("</body>", PROBE, 1),
                encoding="utf-8")


def serve(directory: Path) -> tuple[socketserver.TCPServer, int]:
    handler = type("Quiet", (http.server.SimpleHTTPRequestHandler,), {
        "log_message": lambda *a, **k: None,
        "directory_": str(directory),
    })

    class Server(socketserver.TCPServer):
        allow_reuse_address = True

        def finish_request(self, request, client_address):
            handler(request, client_address, self, directory=str(directory))

    server = Server(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def measure(browser: str, url: str, width: int,
            shot: Path | None) -> tuple[int, int, str] | None:
    args = [browser, "--headless", "--disable-gpu", "--no-sandbox",
            "--force-prefers-reduced-motion",
            f"--window-size={width},900", "--virtual-time-budget=8000"]
    if shot:
        subprocess.run(args + [f"--screenshot={shot}", url],
                       capture_output=True, timeout=90)
    result = subprocess.run(args + ["--dump-dom", url],
                            capture_output=True, text=True, timeout=90)
    match = re.search(r"<title>PROBE\|(\d+)\|(\d+)\|([^<]*)</title>",
                      result.stdout)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), match.group(3)


def sitemap_routes() -> tuple[str, ...]:
    text = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    return tuple(re.sub(r"^https://cubits11\.github\.io", "", u)
                 for u in re.findall(r"<loc>([^<]+)</loc>", text))


def playwright_session(browser: str):
    """A device-emulated Chromium, or None when playwright is not installed."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    pw = sync_playwright().start()
    return pw, pw.chromium.launch(executable_path=browser)


def measure_emulated(chromium, url: str, width: int,
                     shot: Path | None) -> tuple[int, int, str] | None:
    page = chromium.new_page(viewport={"width": width, "height": 900},
                             reduced_motion="reduce")
    try:
        page.goto(url, wait_until="load", timeout=60000)
        title = page.title()
        if shot:
            page.screenshot(path=str(shot), full_page=True)
    finally:
        page.close()
    match = re.match(r"PROBE\|(\d+)\|(\d+)\|(.*)", title)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), match.group(3)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", help="path to a Chromium-family binary")
    parser.add_argument("--shots", help="directory to write screenshots into")
    parser.add_argument("--all", action="store_true",
                        help="check every route in sitemap.xml, not only the landing pages")
    args = parser.parse_args()
    global PAGES
    if args.all:
        PAGES = sitemap_routes()

    browser = find_browser(args.browser)
    if not browser:
        print("SKIP  no Chromium-family browser found; pass --browser PATH")
        print("      (this check is deliberately not a CI gate — see the "
              "module docstring)")
        return 0
    print(f"ok    using {browser}")

    shots = Path(args.shots) if args.shots else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)

    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp) / "site"
        tree.mkdir()
        build_probe_tree(tree)
        server, port = serve(tree)
        session = playwright_session(browser)
        print("ok    viewport: " + ("device-emulated (true widths)" if session
                                    else "window-size (phone widths clamp; see WIDTHS)"))
        try:
            for route in PAGES:
                for width in WIDTHS:
                    url = f"http://127.0.0.1:{port}{route}"
                    name = (route.strip("/") or "home").replace("/", "-")
                    shot = shots / f"{name}-{width}.png" if shots else None
                    reading = (measure_emulated(session[1], url, width, shot) if session
                               else measure(browser, url, width, shot))
                    if reading is None:
                        failures.append(
                            f"{route} @ {width}px: the probe did not report — "
                            f"the page did not lay out")
                        continue
                    client, scroll, worst = reading
                    overflow = scroll - client
                    if overflow > 0:
                        failures.append(
                            f"{route} @ {width}px: page scrolls sideways by "
                            f"{overflow}px (widest offender: {worst})")
                    else:
                        print(f"ok    {route} @ {width}px: no horizontal "
                              f"overflow (client {client}px)")
        finally:
            if session:
                session[1].close()
                session[0].stop()
            server.shutdown()

    if failures:
        for failure in failures:
            print(f"FAIL  {failure}")
        print(f"{len(failures)} check(s) failed.")
        return 1
    print(f"Layout verified: {len(PAGES)} pages x {len(WIDTHS)} widths, "
          f"no page scrolls horizontally, reduced-motion path renders.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
