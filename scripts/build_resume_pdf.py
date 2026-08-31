#!/usr/bin/env python3
"""Print the résumé page to resume/pranav-bhave-resume.pdf.

The PDF is a print of the page, not a separately maintained document. That is
the point: a résumé that says something the page does not is a second source
of truth about a person's history, and this record does not keep those.

Requiring an email to obtain a PDF also costs exactly the visitor who has
already decided to look harder. The page omits a phone number, so the print
does too, and the file can simply be downloaded.

Committed artifact — CI verifies its source-binding receipt. Rebuild it
whenever a declared print input changes:

    python scripts/build_resume_pdf.py
    python scripts/build_resume_pdf.py --browser /path/to/chrome
"""

from __future__ import annotations

import argparse
import http.server
import socketserver
import subprocess
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_layout import find_browser  # noqa: E402
from resume_artifact import PDF as OUT, write_manifest  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TMP_DIR = ROOT / "tmp" / "pdfs"
TMP = TMP_DIR / "pranav-bhave-resume.next.pdf"


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


def renderer_identity(browser: str) -> str:
    """Record the actual renderer without making it a cross-host equality gate."""
    try:
        result = subprocess.run([browser, "--version"], capture_output=True,
                                text=True, timeout=15, check=False)
    except OSError:
        return browser
    version = (result.stdout or result.stderr).strip()
    return version or browser


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", help="path to a Chromium-family binary")
    args = parser.parse_args()

    browser = find_browser(args.browser)
    if not browser:
        print("FAIL  no Chromium-family browser found; pass --browser PATH")
        return 1

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    TMP.unlink(missing_ok=True)
    server, port = serve(ROOT)
    try:
        try:
            result = subprocess.run(
                [browser, "--headless", "--disable-gpu", "--no-sandbox",
                 "--no-pdf-header-footer", "--force-prefers-reduced-motion",
                 "--virtual-time-budget=10000", f"--print-to-pdf={TMP}",
                 f"http://127.0.0.1:{port}/resume/"],
                capture_output=True, text=True, timeout=180)
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"FAIL  the browser could not render the résumé PDF ({exc})")
            return 1
    finally:
        server.shutdown()
        server.server_close()

    if result.returncode:
        print("FAIL  the browser could not render the résumé PDF")
        print(result.stderr[-800:])
        return 1
    if not TMP.exists() or TMP.stat().st_size < 10_000:
        print("FAIL  the PDF was not written, or is implausibly small")
        print(result.stderr[-800:])
        return 1
    header = TMP.read_bytes()[:5]
    if header != b"%PDF-":
        print(f"FAIL  {TMP.name} is not a PDF")
        return 1
    TMP.replace(OUT)
    write_manifest(renderer_identity(browser))
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
