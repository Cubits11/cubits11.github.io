#!/usr/bin/env python3
"""Post-deploy gate: does the live site actually serve what this repo says?

Verification that only runs on a checkout proves the repo is coherent. It
does not prove a reader can reach the pages, and it does not prove the
deployed HTML is the HTML CI checked. A branch push is not a release.

This script fetches every route in sitemap.xml, requires 200s, and then
asserts that the deployed Missing Column page carries the counts this
repo's census computes right now — including the strongest rung of the M
ladder, which is the number most likely to be quietly dropped in a
redesign. Run it against the live site after a deploy, and weekly.
"""
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_census import compute_counts, load  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://cubits11.github.io"
TIMEOUT = 30

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL  {msg}")


def ok(msg: str) -> None:
    print(f"ok    {msg}")


def fetch(url: str) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": "cubits11-smoke"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            if resp.status != 200:
                fail(f"{url} returned HTTP {resp.status}")
                return None
            return resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        fail(f"{url} returned HTTP {exc.code}")
    except Exception as exc:  # network, TLS, timeout
        fail(f"{url} unreachable: {exc}")
    return None


def routes() -> list[str]:
    xml = (ROOT / "sitemap.xml").read_text()
    return re.findall(r"<loc>([^<]+)</loc>", xml)


def main() -> int:
    urls = routes()
    if not urls:
        fail("sitemap.xml lists no routes")
        return 1
    bodies: dict[str, str] = {}
    for url in urls:
        body = fetch(url)
        if body is not None:
            bodies[url] = body
    if len(bodies) == len(urls):
        ok(f"{len(urls)} sitemap routes served 200")

    counts = compute_counts(load())
    strata = counts["M_strata"]
    mc_url = f"{SITE}/missing-column/"
    body = bodies.get(mc_url)
    if body is None:
        fail(f"{mc_url} did not serve — cannot check deployed counts")
    else:
        text = re.sub(r"<[^>]+>", " ", body)
        text = re.sub(r"\s+", " ", text)
        wanted = [
            (f"{counts['N']} public guardrail evaluations", "N in the proposition"),
            (f"{strata['shared_basis']} share items", "M ladder rung 1"),
            (f"{strata['threshold_not_contradicted']} once the row", "M ladder rung 2"),
            (f"{strata['threshold_documented_full_exposure']} document matched",
             "M ladder rung 3 — the strongest reading"),
        ]
        for needle, label in wanted:
            if needle in text:
                ok(f"deployed page states {label}")
            else:
                fail(f"deployed page is missing {label} (expected {needle!r})")

    if failures:
        print(f"{len(failures)} check(s) failed.")
        return 1
    print("Deployed site verified: every route serves, and the live counts "
          "match what this census computes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
