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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", help="path to a Chromium-family binary")
    parser.add_argument("--shots", help="directory to write screenshots into")
    args = parser.parse_args()

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
        try:
            for route in PAGES:
                for width in WIDTHS:
                    url = f"http://127.0.0.1:{port}{route}"
                    name = (route.strip("/") or "home").replace("/", "-")
                    shot = shots / f"{name}-{width}.png" if shots else None
                    reading = measure(browser, url, width, shot)
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
