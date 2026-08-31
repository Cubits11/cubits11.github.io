#!/usr/bin/env python3
"""Print the résumé page to resume/pranav-bhave-resume.pdf.

The PDF is a print of the page, not a separately maintained document. That is
the point: a résumé that says something the page does not is a second source
of truth about a person's history, and this record does not keep those.

Requiring an email to obtain a PDF also costs exactly the visitor who has
already decided to look harder. The page omits a phone number, so the print
does too, and the file can simply be downloaded.

Committed artifact — CI never runs this. Rebuild it whenever resume/index.html
changes:

    python scripts/build_resume_pdf.py
    python scripts/build_resume_pdf.py --browser /path/to/chrome
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import http.server
import json
import socketserver
import subprocess
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_layout import find_browser  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "resume" / "pranav-bhave-resume.pdf"
RECEIPT = ROOT / "resume" / "pranav-bhave-resume.receipt.json"

# The inputs that can change what the printed page says or how it lays out.
# A PDF whose receipt no longer matches these is a second source of truth about
# a person's history, which is exactly what this artifact refuses to be.
SOURCES = ("resume/index.html", "assets/site.css", "assets/site.js")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def renderer_identity(browser: str) -> str:
    try:
        out = subprocess.run([browser, "--version"], capture_output=True,
                             text=True, timeout=30)
        return (out.stdout or out.stderr).strip() or "unknown"
    except Exception:
        return "unknown"


def serve(directory: Path) -> tuple[socketserver.TCPServer, int]:
    """Serve the tree locally — the page uses absolute asset paths."""
    class Server(socketserver.TCPServer):
        allow_reuse_address = True

        def finish_request(self, request, client_address):
            handler(request, client_address, self, directory=str(directory))

    handler = type("Quiet", (http.server.SimpleHTTPRequestHandler,),
                   {"log_message": lambda *a, **k: None})
    server = Server(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", help="path to a Chromium-family binary")
    args = parser.parse_args()

    browser = find_browser(args.browser)
    if not browser:
        print("SKIP  no Chromium-family browser found; pass --browser PATH")
        return 0

    server, port = serve(ROOT)
    try:
        result = subprocess.run(
            [browser, "--headless", "--disable-gpu", "--no-sandbox",
             "--no-pdf-header-footer", "--force-prefers-reduced-motion",
             "--virtual-time-budget=10000", f"--print-to-pdf={OUT}",
             f"http://127.0.0.1:{port}/resume/"],
            capture_output=True, text=True, timeout=180)
    finally:
        server.shutdown()

    if not OUT.exists() or OUT.stat().st_size < 10_000:
        print("FAIL  the PDF was not written, or is implausibly small")
        print(result.stderr[-800:])
        return 1
    header = OUT.read_bytes()[:5]
    if header != b"%PDF-":
        print(f"FAIL  {OUT.name} is not a PDF")
        return 1
    receipt = {
        "artifact": OUT.relative_to(ROOT).as_posix(),
        "artifact_sha256": sha256(OUT),
        "artifact_bytes": OUT.stat().st_size,
        "sources": {rel: sha256(ROOT / rel) for rel in SOURCES},
        "renderer": renderer_identity(browser),
        "print_flags": ["--headless", "--no-pdf-header-footer",
                        "--force-prefers-reduced-motion",
                        "--virtual-time-budget=10000"],
        "built_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "claim": ("This PDF is a print of resume/index.html at the source digests "
                  "above. It asserts nothing the page does not."),
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size} bytes)")
    print(f"wrote {RECEIPT.relative_to(ROOT)} (binds PDF to {len(SOURCES)} sources)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
