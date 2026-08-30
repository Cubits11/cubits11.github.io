#!/usr/bin/env python3
"""Wait for and verify a coherent deployed Cubits11 release.

Checkout verification proves only that a revision is internally coherent. A
release gate must additionally prove that readers can reach every canonical
route, that the served census is the revision just checked, and that the
rendered Missing Column page is bound to that exact census. GitHub Pages is
asynchronous, so the script retries until all of those assertions describe
one coherent public deployment.

It formerly asserted N and the M ladder and not K, so the strongest statement
it could support was "the deployed page matches the checked revision" — which
a page contradicting itself about K satisfies. It now re-runs the full fact
audit against the served bytes, so the statement it supports is the one the
record actually promises: every current factual surface the public receives
agrees with the census that produced it.
"""

import argparse
import hashlib
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import facts  # noqa: E402
from verify_census import compute_counts, load  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SITE = "https://cubits11.github.io"
CORRECTION_POLICY_URL = f"{DEFAULT_SITE}/corrections/"
DEFAULT_ATTEMPTS = 24
DEFAULT_INTERVAL_SECONDS = 10
TIMEOUT = 30


def fetch(url: str) -> tuple[bytes | None, str | None]:
    """Fetch one URL without letting a transient deployment state pass."""
    req = urllib.request.Request(url, headers={"User-Agent": "cubits11-smoke"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            if response.status != 200:
                return None, f"{url} returned HTTP {response.status}"
            return response.read(), None
    except urllib.error.HTTPError as exc:
        return None, f"{url} returned HTTP {exc.code}"
    except Exception as exc:  # network, TLS, timeout
        return None, f"{url} unreachable: {exc}"


def routes(site: str) -> list[str]:
    """Map canonical sitemap paths onto a requested deployment target."""
    xml = (ROOT / "sitemap.xml").read_text()
    paths = [urlsplit(url).path or "/"
             for url in re.findall(r"<loc>([^<]+)</loc>", xml)]
    return [urljoin(f"{site}/", path.lstrip("/")) for path in paths]


def check_once(site: str) -> list[str]:
    """Return every failed assertion for one attempt at a coherent release."""
    failures: list[str] = []
    urls = routes(site)
    if not urls:
        return ["sitemap.xml lists no routes"]

    bodies: dict[str, bytes] = {}
    for url in urls:
        body, error = fetch(url)
        if error:
            failures.append(error)
        elif body is not None:
            bodies[url] = body
    if len(bodies) == len(urls):
        print(f"ok    {len(urls)} sitemap routes served 200")

    local_census = (ROOT / "census.yaml").read_bytes()
    local_sha = hashlib.sha256(local_census).hexdigest()
    census_url = urljoin(f"{site}/", "census.yaml")
    deployed_census, error = fetch(census_url)
    if error:
        failures.append(error)
    elif deployed_census is not None:
        deployed_sha = hashlib.sha256(deployed_census).hexdigest()
        if deployed_sha != local_sha:
            failures.append(
                f"{census_url} has sha256 {deployed_sha}, expected {local_sha}")
        else:
            print("ok    deployed census.yaml matches this revision byte-for-byte")

    counts = compute_counts(load())
    strata = counts["M_strata"]
    mc_url = urljoin(f"{site}/", "missing-column/")
    body = bodies.get(mc_url)
    if body is None:
        failures.append(f"{mc_url} did not serve — cannot check deployed counts")
        return failures

    html = body.decode("utf-8", "replace")
    text = facts.visible_text(html)
    modes = counts["K_evidence_modes"]
    wanted = [
        (f"{counts['N']} public guardrail evaluations", "N in the proposition"),
        (f"{strata['shared_basis']} document a shared item set and a common event definition",
         "M ladder rung 1"),
        (f"{strata['threshold_not_contradicted']} have no stated threshold mismatch",
         "M ladder rung 2"),
        (f"{strata['threshold_documented_full_exposure']} document matched",
         "M ladder rung 3 — the strongest reading"),
        # K was the one headline quantity this gate never asserted, which is
        # how a deployed page that stated it as both 5 and 4 passed here.
        (f"{counts['K']} provide one of the declared joint-evidence artifacts",
         "K in the proposition"),
        (f"The {counts['K']} is a heterogeneous discovery count",
         "K where the page glosses it"),
        (f"Its {counts['K']} is an inclusive discovery count",
         "K in the non-claims — the surface that drifted"),
        (f"{modes['prints_composition_result']} artifacts print at least one "
         f"composition result", "the printed-evidence mode count"),
    ]
    for needle, label in wanted:
        if needle in text:
            print(f"ok    deployed page states {label}")
        else:
            failures.append(
                f"deployed page is missing {label} (expected {needle!r})")

    # The same fact audit CI runs on the checkout, re-run against the bytes
    # the public actually receives. A checkout gate proves what was built; it
    # cannot prove what is being served.
    registry = facts.registry(counts)
    fact_failures = facts.audit_html(
        html, registry, mc_url,
        facts.REQUIRED_BINDINGS.get("missing-column/index.html"),
        facts.accepted_triples())
    if fact_failures:
        failures.extend(fact_failures)
    else:
        print("ok    deployed page carries no stale current census value")

    stale_k = re.compile(
        r"\b(?:the|its)\s+(?!%d\b)\d+\s+is\s+(?:an inclusive|a heterogeneous)"
        r"\s+discovery count" % counts["K"], re.I)
    hit = stale_k.search(facts.visible_text(facts.strip_historical(html)))
    if hit:
        failures.append(
            f"deployed page states a discovery count other than the current "
            f"{counts['K']}: {hit.group(0)!r}")
    else:
        print(f"ok    no current discovery count on the deployed page "
              f"disagrees with K={counts['K']}")
    marker = f'<meta name="census-sha256" content="{local_sha}">'
    if marker in html:
        print("ok    deployed page binds itself to the deployed census checksum")
    else:
        failures.append(
            "deployed page does not carry this revision's census-sha256 marker")

    correction_marker = (
        f'<meta name="correction-policy-url" content="{CORRECTION_POLICY_URL}">')
    if correction_marker in html:
        print("ok    deployed page binds the canonical correction-policy route")
    else:
        failures.append(
            "deployed page does not name the canonical correction-policy route")
    corrections_url = urljoin(f"{site}/", "corrections/")
    corrections = bodies.get(corrections_url)
    if corrections is None:
        failures.append(f"{corrections_url} did not serve — cannot check correction policy")
    else:
        correction_html = corrections.decode("utf-8", "replace")
        if ('id="correction-policy"' in correction_html
                and "same calendar day" in correction_html):
            print("ok    correction policy is served with the same-day logging rule")
        else:
            failures.append(
                "deployed correction page is missing its policy or same-day logging rule")
    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Wait for and verify a coherent deployed Cubits11 release.")
    parser.add_argument(
        "--site", default=os.environ.get("CUBITS_SITE_URL", DEFAULT_SITE),
        help="release target (default: %(default)s)")
    parser.add_argument(
        "--attempts", type=int, default=DEFAULT_ATTEMPTS,
        help="coherent deployment views to try (default: %(default)s)")
    parser.add_argument(
        "--interval-seconds", type=float, default=DEFAULT_INTERVAL_SECONDS,
        help="seconds between attempts (default: %(default)s)")
    args = parser.parse_args()
    parsed = urlsplit(args.site)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        parser.error("--site must be an absolute http(s) URL")
    if args.attempts < 1:
        parser.error("--attempts must be at least 1")
    if args.interval_seconds < 0:
        parser.error("--interval-seconds cannot be negative")
    args.site = args.site.rstrip("/")
    return args


def main() -> int:
    args = parse_args()
    last_failures: list[str] = []
    for attempt in range(1, args.attempts + 1):
        print(f"check {attempt}/{args.attempts}: {args.site}")
        last_failures = check_once(args.site)
        if not last_failures:
            print("Deployed site verified: every route serves, the served census "
                  "matches this revision, and the rendered M ladder is current.")
            return 0
        if attempt < args.attempts:
            print(f"wait  deployment has not settled ({len(last_failures)} assertion(s)); "
                  f"retrying in {args.interval_seconds:g}s")
            time.sleep(args.interval_seconds)

    for failure in last_failures:
        print(f"FAIL  {failure}")
    print(f"{len(last_failures)} check(s) failed after {args.attempts} attempt(s).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
