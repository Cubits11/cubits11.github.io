#!/usr/bin/env python3
"""Verify the claim registry (claims.yaml) — schema v0.4.

Checks, in order:
  1. Shape — required fields, dimension enums, trigger typing, and the
     public challenge record: every claim has a non-empty falsifier condition,
     a fixed NARROW|REJECT|HOLD consequence, and a typed forbidden_rescues
     list (an explicit [] is valid). "attested" may never appear as an
     evidential status: it is provenance.
  2. Binding consistency — when a claim declares a commit, the support URL
     must embed exactly that commit (a resolving URL is not a binding;
     a matching one is), AND every bound commit must be reachable from its
     repository's default branch. GitHub serves dangling objects for
     years, so a resolving raw URL proves nothing about reachability —
     CC-001 was once bound to a commit stranded by an upstream history
     rewrite, and content-hash triggers were structurally blind to it.
     One filtered bare clone per bound repository; merge-base decides.
  3. Freshness — each claim carries its own review window; a claim past it
     fails the run. The weekly scheduled run turns this into a standing gate.
     last_owner_review may never lag the newest per-claim review.
  4. Executable review triggers —
       remote_content_change: fetch the bound file at its bound ref and at
         the default branch HEAD; if the content differs, the evidence has
         changed and the claim's warrant is due — the run fails.
       local_content_change: hash the named file in this checkout against
         the recorded sha256; drift without a registry re-review fails.
     Triggers marked manual are reported, honestly, as beyond CI's reach.
  5. Support liveness — every public support URL resolves (< 400).
  6. Ledger coverage — every claim id appears in ledger/index.html
     (generation-drift itself is checked by generate_ledger.py --check).
  7. Homepage coherence — index.html must state the registry's actual claim
     count and last owner review; hand-written strips may not silently
     strand when the registry grows.

Exit code 0 = registry verified; 1 = at least one check failed.
"""

import datetime as dt
import hashlib
import pathlib
import re
import subprocess
import sys
import tempfile
import urllib.request

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent

ENUMS = {
    "visibility": {"public", "private"},
    "provenance": {"machine_generated_owner_executed", "owner_authored",
                   "lab_repository", "owner_attested", "owner_verified"},
    "support_role": {"executed_output", "document", "repository_readme",
                     "site_document", "none"},
    "evidential_status": {"untested", "partially_supported",
                          "supported_within_scope", "inconclusive",
                          "contradicted"},
    "maturity": {"experimental", "in_development", "released", "stable",
                 "superseded"},
}
REQUIRED = {"id", "proposition", "scope", "dimensions", "support",
            "last_reviewed", "review_window_days", "review_triggers",
            "falsifier", "forbidden_rescues", "non_claims"}
FALSIFIER_CONSEQUENCES = {"NARROW", "REJECT", "HOLD"}

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL  {msg}")


def ok(msg: str) -> None:
    print(f"ok    {msg}")


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": "cubits11.github.io claim-registry verifier"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status >= 400:
            raise RuntimeError(f"HTTP {resp.status}")
        return resp.read()


def check_dimensions(cid: str, dims: dict) -> None:
    for key, allowed in ENUMS.items():
        val = dims.get(key)
        if val not in allowed:
            fail(f"{cid}: dimensions.{key}={val!r} not in {sorted(allowed)}")
    if dims.get("evidential_status") == "attested":
        fail(f"{cid}: 'attested' used as evidential_status — it is provenance")


def check_falsifier(cid: str, falsifier) -> None:
    if not isinstance(falsifier, dict):
        fail(f"{cid}: falsifier must be a mapping with condition and consequence")
        return
    missing = {"condition", "consequence"} - set(falsifier)
    if missing:
        fail(f"{cid}: falsifier missing fields {sorted(missing)}")
    condition = falsifier.get("condition")
    if not isinstance(condition, str) or not condition.strip():
        fail(f"{cid}: falsifier.condition must be a non-empty string")
    consequence = falsifier.get("consequence")
    if consequence not in FALSIFIER_CONSEQUENCES:
        fail(f"{cid}: falsifier.consequence={consequence!r} not in "
             f"{sorted(FALSIFIER_CONSEQUENCES)}")


def check_forbidden_rescues(cid: str, rescues) -> None:
    if not isinstance(rescues, list):
        fail(f"{cid}: forbidden_rescues must be an array; use [] when none apply")
        return
    for index, rescue in enumerate(rescues):
        if not isinstance(rescue, str) or not rescue.strip():
            fail(f"{cid}: forbidden_rescues[{index}] must be a non-empty string")


def check_binding(cid: str, support: dict) -> None:
    url, commit = support.get("url"), support.get("commit")
    if commit and not url:
        fail(f"{cid}: commit declared but no support URL")
    if commit and url:
        if commit in url:
            ok(f"{cid}: support URL embeds the bound commit {commit[:8]}")
        else:
            fail(f"{cid}: support URL does not embed declared commit {commit[:8]}")


def check_trigger(cid: str, trig: dict) -> None:
    enforcement = trig.get("enforcement")
    ttype = trig.get("type")
    if enforcement == "manual":
        ok(f"{cid}: manual trigger declared — {trig.get('event') or ttype}")
        return
    if enforcement != "executable":
        fail(f"{cid}: trigger enforcement must be executable|manual, got {enforcement!r}")
        return
    if ttype == "remote_content_change":
        repo, path, ref = trig.get("repo"), trig.get("path"), trig.get("bound_ref")
        try:
            bound = hashlib.sha256(fetch(
                f"https://raw.githubusercontent.com/{repo}/{ref}/{path}")).hexdigest()
            head = hashlib.sha256(fetch(
                f"https://raw.githubusercontent.com/{repo}/HEAD/{path}")).hexdigest()
        except Exception as exc:  # noqa: BLE001
            fail(f"{cid}: trigger fetch failed for {repo}/{path} ({exc})")
            return
        if bound == head:
            ok(f"{cid}: evidence unchanged — {repo}/{path} matches bound ref")
        else:
            fail(f"{cid}: TRIGGER FIRED — {repo}/{path} on the default branch "
                 f"diverged from bound ref {str(ref)[:8]}; claim is due for re-review")
    elif ttype == "local_content_change":
        path, recorded = trig.get("path"), trig.get("sha256")
        target = ROOT / str(path)
        if not target.exists():
            fail(f"{cid}: local trigger path missing: {path}")
            return
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual == recorded:
            ok(f"{cid}: {path} matches recorded hash")
        else:
            fail(f"{cid}: TRIGGER FIRED — {path} changed without a registry "
                 f"re-review (recorded {str(recorded)[:12]}, actual {actual[:12]})")
    else:
        fail(f"{cid}: unknown executable trigger type {ttype!r}")


def check_reachability(bindings: dict[str, list[tuple[str, str]]]) -> None:
    """Every bound commit must be an ancestor of its repo's default branch."""
    for repo, entries in sorted(bindings.items()):
        with tempfile.TemporaryDirectory() as tmp:
            clone = str(pathlib.Path(tmp) / "probe")
            try:
                subprocess.run(
                    ["git", "clone", "--quiet", "--bare", "--filter=tree:0",
                     f"https://github.com/{repo}.git", clone],
                    check=True, capture_output=True, timeout=120)
            except Exception as exc:  # noqa: BLE001
                fail(f"reachability probe clone failed for {repo} ({exc})")
                continue
            for cid, commit in entries:
                result = subprocess.run(
                    ["git", "-C", clone, "merge-base", "--is-ancestor",
                     commit, "HEAD"], capture_output=True)
                if result.returncode == 0:
                    ok(f"{cid}: bound commit {commit[:8]} reachable from "
                       f"{repo}'s default branch")
                else:
                    fail(f"{cid}: bound commit {commit[:8]} is NOT reachable "
                         f"from {repo}'s default branch — a dangling binding "
                         f"survives only as long as GitHub retains the object")


def check_url_liveness(cid: str, url: str) -> None:
    try:
        fetch(url)
        ok(f"{cid}: support URL resolves — {url}")
    except Exception as exc:  # noqa: BLE001
        fail(f"{cid}: support URL unreachable ({exc}): {url}")


def main() -> int:
    registry = yaml.safe_load((ROOT / "claims.yaml").read_text())
    claims = registry.get("claims", [])
    if not claims:
        fail("registry contains no claims")
        return 1
    ok(f"registry schema v{registry.get('version')} loaded with {len(claims)} claims")

    today = dt.date.today()
    ledger_html = (ROOT / "ledger" / "index.html").read_text()
    index_html = (ROOT / "index.html").read_text()

    bindings: dict[str, list[tuple[str, str]]] = {}
    for claim in claims:
        support = claim.get("support") or {}
        url, commit = support.get("url"), support.get("commit")
        if url and commit:
            match = re.match(r"https://github\.com/([^/]+/[^/]+)/", str(url))
            if match:
                bindings.setdefault(match.group(1), []).append(
                    (claim.get("id", "<missing id>"), str(commit)))
    check_reachability(bindings)

    owner_review = str(registry.get("last_owner_review", ""))
    newest_claim_review = max(str(c.get("last_reviewed", "")) for c in claims)
    if owner_review < newest_claim_review:
        fail(f"last_owner_review {owner_review} lags newest claim review "
             f"{newest_claim_review}")
    else:
        ok(f"last_owner_review {owner_review} covers all claim reviews")

    for needle, what in ((f"{len(claims)} claims", "claim count"),
                         (owner_review, "last owner review date")):
        if needle in index_html:
            ok(f"index.html states the registry's {what} ({needle})")
        else:
            fail(f"index.html does not state the registry's {what} ({needle!r})")

    for claim in claims:
        cid = claim.get("id", "<missing id>")

        missing = REQUIRED - set(claim)
        if missing:
            fail(f"{cid}: missing fields {sorted(missing)}")
            continue

        check_dimensions(cid, claim["dimensions"])
        check_falsifier(cid, claim["falsifier"])
        check_forbidden_rescues(cid, claim["forbidden_rescues"])

        raw = str(claim["last_reviewed"])
        window = int(claim["review_window_days"])
        try:
            reviewed = dt.date.fromisoformat(raw)
            if reviewed > today:
                fail(f"{cid}: last_reviewed {reviewed} is in the future")
            elif (today - reviewed).days > window:
                fail(f"{cid}: review due — last reviewed {reviewed}, window {window}d")
            else:
                ok(f"{cid}: reviewed {reviewed} (window {window}d, fresh)")
        except ValueError:
            fail(f"{cid}: unparseable last_reviewed {raw!r}")

        support = claim.get("support") or {}
        check_binding(cid, support)
        for trig in claim["review_triggers"]:
            check_trigger(cid, trig)

        url = support.get("url")
        if url:
            check_url_liveness(cid, url)
        elif claim["dimensions"].get("provenance") == "owner_attested":
            ok(f"{cid}: owner-attested — no public support URL, by declaration")
        else:
            fail(f"{cid}: non-attested claim has no support URL")

        if re.search(rf'id="{re.escape(cid)}"', ledger_html):
            ok(f"{cid}: rendered in ledger")
        else:
            fail(f"{cid}: not rendered in ledger/index.html")

    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        return 1
    print("Registry verified: shaped, falsifiers and forbidden rescues "
          "declared, bound, fresh, triggers quiet, support reachable, "
          "ledger covered.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
