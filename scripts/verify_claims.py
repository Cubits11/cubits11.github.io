#!/usr/bin/env python3
"""Verify the claim registry (claims.yaml) against the rendered site.

Checks, in order:
  1. Registry shape — required fields present, status vocabulary respected.
  2. Dates — parseable, not in the future.
  3. Freshness — any claim whose last_reviewed is older than FRESHNESS_DAYS
     fails the run: its warrant is due for re-examination, and the failure is
     the review trigger (the weekly scheduled run turns this into a standing
     freshness gate).
  4. Ledger coverage — every claim id is rendered in ledger/index.html.
  5. Support liveness — every http(s) support URL resolves (< 400).

Exit code 0 = registry verified; 1 = at least one check failed.
"""

import datetime as dt
import pathlib
import re
import sys
import urllib.request

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
FRESHNESS_DAYS = 120
STATUSES = {
    "untested", "partially_supported", "supported_within_scope",
    "inconclusive", "contradicted", "attested",
}
REQUIRED = {
    "id", "proposition", "scope", "support", "provenance",
    "status", "last_reviewed", "review_trigger", "non_claims",
}

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL  {msg}")


def ok(msg: str) -> None:
    print(f"ok    {msg}")


def check_url(url: str, cid: str) -> None:
    req = urllib.request.Request(url, method="GET", headers={
        "User-Agent": "cubits11.github.io claim-registry verifier"
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status < 400:
                ok(f"{cid}: support URL resolves ({resp.status}) {url}")
            else:
                fail(f"{cid}: support URL returned {resp.status}: {url}")
    except Exception as exc:  # noqa: BLE001 - report every failure mode
        fail(f"{cid}: support URL unreachable ({exc}): {url}")


def main() -> int:
    registry = yaml.safe_load((ROOT / "claims.yaml").read_text())
    claims = registry.get("claims", [])
    if not claims:
        fail("registry contains no claims")
        return 1
    ok(f"registry v{registry.get('version')} loaded with {len(claims)} claims")

    today = dt.date.today()
    ledger_html = (ROOT / "ledger" / "index.html").read_text()

    for claim in claims:
        cid = claim.get("id", "<missing id>")

        missing = REQUIRED - set(claim)
        if missing:
            fail(f"{cid}: missing fields {sorted(missing)}")
        if claim.get("status") not in STATUSES:
            fail(f"{cid}: unknown status {claim.get('status')!r}")

        raw = str(claim.get("last_reviewed", ""))
        try:
            reviewed = dt.date.fromisoformat(raw)
            if reviewed > today:
                fail(f"{cid}: last_reviewed {reviewed} is in the future")
            elif (today - reviewed).days > FRESHNESS_DAYS:
                fail(f"{cid}: review due — last reviewed {reviewed}, "
                     f"older than {FRESHNESS_DAYS} days")
            else:
                ok(f"{cid}: reviewed {reviewed} (fresh)")
        except ValueError:
            fail(f"{cid}: unparseable last_reviewed {raw!r}")

        if not re.search(rf'id="{re.escape(cid)}"', ledger_html):
            fail(f"{cid}: not rendered in ledger/index.html")
        else:
            ok(f"{cid}: rendered in ledger")

        url = (claim.get("support") or {}).get("url")
        if url:
            check_url(url, cid)
        elif claim.get("status") == "attested":
            ok(f"{cid}: attested — no public support URL, by declaration")
        else:
            fail(f"{cid}: non-attested claim has no support URL")

    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        return 1
    print("Registry verified: every claim shaped, fresh, rendered, and "
          "its public support reachable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
