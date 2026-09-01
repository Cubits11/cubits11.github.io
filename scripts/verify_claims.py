#!/usr/bin/env python3
"""Verify the public claim registry (claims.yaml) — schema v0.4.

Checks, in order:
  1. Shape — required fields, public-only visibility, dimension enums, trigger typing, and the
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
  7. Public claim-count coherence — the homepage and generated registry
     surfaces must mark their live count and agree with claims.yaml; a
     historical count must be explicitly dated so it cannot impersonate the
     live record.

Exit codes: 0 = registry verified; 1 = at least one check was evaluated and
failed; 2 = nothing failed, but at least one check could not be evaluated
because its source was never reached. 2 is not a pass — a gate must not
proceed on an unknown — but it is not a refutation either, and neither the
run log nor the ledger may record it as one. This mirrors verify_wayback.py;
the states are pinned by verify_claims_states.py.
"""

import datetime as dt
import hashlib
import pathlib
import re
import subprocess
import sys
import socket
import tempfile
import urllib.error
import urllib.request

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent

ENUMS = {
    "visibility": {"public"},
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
# Rights travel with evidence. A claim bound to someone else's artifact must
# record what may be done with it, because "we cited it" and "we may build a
# commercial derivative of it" are different permissions and the difference is
# invisible six months later. UNKNOWN and QUARANTINED are terminal states: they
# are allowed to exist, and they are not allowed to flow anywhere.
COMMERCIAL_REUSE = {"permitted", "noncommercial_only", "permission_required",
                    "facts_only", "unknown", "quarantined"}
FIRST_PARTY = ("github.com/Cubits11/", "cubits11.github.io")

REQUIRED = {"id", "proposition", "scope", "dimensions", "support",
            "last_reviewed", "review_window_days", "review_triggers",
            "falsifier", "forbidden_rescues", "non_claims"}
FALSIFIER_CONSEQUENCES = {"NARROW", "REJECT", "HOLD"}

failures: list[str] = []
unknowns: list[str] = []

# A number of claims is an unusually easy datum to leave behind in a hand-written
# surface. The marker makes the state explicit: the public record is either
# current and mechanically checked, or historical and dated. Bare ``N claims``
# strings are forbidden on the designated public count surfaces because a
# reader cannot know which role they play.
CLAIM_COUNT_MARKER = re.compile(
    r'<(?P<tag>[A-Za-z][\w:-]*)(?P<attrs>[^>]*\bdata-claim-count-state="'
    r'(?P<state>current|historical)"[^>]*)>(?P<body>.*?)</(?P=tag)>',
    re.DOTALL,
)
CLAIM_COUNT_TEXT = re.compile(r"\b(?P<count>\d+)\s+claims?\b", re.IGNORECASE)
TAG_TEXT = re.compile(r"<[^>]+>")
AS_OF = re.compile(r'\bdata-as-of="(?P<date>\d{4}-\d{2}-\d{2})"')
CLAIM_COUNT_SURFACES = {
    "index.html": "current",
    "ledger/index.html": "current",
    "observatory/index.html": "current",
    "now/index.html": "historical",
}


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL  {msg}")


def unknown(msg: str) -> None:
    """Record a check whose source was never reached.

    A source we could not reach is not a source that failed. Merging the two
    lets an outage be recorded as a dead binding or a fired trigger — which is
    the exact inference (absence of evidence read as evidence of absence) this
    registry exists to refuse. Kept separate here for the same reason
    verify_wayback.py keeps them separate.
    """
    unknowns.append(msg)
    print(f"UNKNOWN  {msg}")


def transport_failure(exc: BaseException) -> bool:
    """True when the exception means the server was never reached.

    HTTPError is tested first and deliberately excluded: it subclasses
    URLError, and the server did answer — a 404 or 410 on a bound support URL
    is a real finding about the binding, not a network condition.
    """
    if isinstance(exc, urllib.error.HTTPError):
        return False
    return isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError,
                            socket.timeout, socket.gaierror, OSError))


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
    if dims.get("visibility") != "public":
        fail(f"{cid}: claims.yaml is public-only; private records must not be tracked here")


def check_support_rights(cid: str, support: dict) -> None:
    """Third-party evidence must declare its licence and reuse state.

    First-party artifacts (this site, this owner's repositories) inherit the
    owner's rights and are exempt. Everything else is somebody else's work,
    and a registry that binds to it without recording the terms is one
    refactor away from a licence violation it cannot detect.
    """
    url = str((support or {}).get("url") or "")
    if not url or any(fp in url for fp in FIRST_PARTY):
        return
    licence = support.get("license")
    reuse = support.get("commercial_reuse")
    if not isinstance(licence, str) or not licence.strip():
        fail(f"{cid}: third-party support must record support.license "
             f"(use 'none declared' when the source states none) — {url}")
    if reuse not in COMMERCIAL_REUSE:
        fail(f"{cid}: support.commercial_reuse={reuse!r} not in "
             f"{sorted(COMMERCIAL_REUSE)}")
    elif reuse in ("unknown", "quarantined"):
        ok(f"{cid}: rights {reuse} — evidence usable for analysis, barred "
           f"from any derivative until resolved")
    else:
        ok(f"{cid}: third-party rights recorded ({licence}, {reuse})")


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
            # "TRIGGER FIRED" asserts that bound evidence changed upstream.
            # A fetch that never completed asserts nothing of the kind, and
            # must not be able to produce that same red on a flaky network.
            report = unknown if transport_failure(exc) else fail
            report(f"{cid}: trigger fetch did not complete for {repo}/{path} "
                   f"({exc}) — evidence drift is unevaluated, not observed")
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
                unknown(f"reachability probe clone did not complete for {repo} "
                        f"({exc}) — ancestry of its bound commit(s) is "
                        f"unevaluated, not refuted")
                continue
            for cid, commit in entries:
                result = subprocess.run(
                    ["git", "-C", clone, "merge-base", "--is-ancestor",
                     commit, "HEAD"], capture_output=True)
                if result.returncode == 0:
                    ok(f"{cid}: bound commit {commit[:8]} reachable from "
                       f"{repo}'s default branch")
                elif result.returncode == 1:
                    # git answered: the commit is not an ancestor. A verdict.
                    fail(f"{cid}: bound commit {commit[:8]} is NOT reachable "
                         f"from {repo}'s default branch — a dangling binding "
                         f"survives only as long as GitHub retains the object")
                else:
                    # git could not answer (unknown revision, broken probe).
                    # That is not the same sentence as "not an ancestor".
                    detail = result.stderr.decode("utf-8", "replace").strip()
                    unknown(f"{cid}: ancestry probe for {commit[:8]} in {repo} "
                            f"could not be evaluated (git exit "
                            f"{result.returncode}: {detail or 'no detail'})")


SELF_BLOB = "https://github.com/Cubits11/cubits11.github.io/blob/main/"


def check_url_liveness(cid: str, url: str) -> None:
    # Branch CI cannot require a self-link to main to resolve before merge.
    # Here we verify only that its referenced source exists in this checkout;
    # this is not a remote-liveness or deployment assertion. The post-deploy
    # smoke gate handles the latter once an exact revision is on main.
    if str(url).startswith(SELF_BLOB):
        rel = str(url)[len(SELF_BLOB):]
        if (ROOT / rel).is_file():
            ok(f"{cid}: self-support path exists in this checkout — {rel} "
               "(deployment liveness is a separate gate)")
        else:
            fail(f"{cid}: support URL names {rel}, which does not exist "
                 f"in this repository")
        return
    try:
        fetch(url)
        ok(f"{cid}: support URL resolves — {url}")
    except Exception as exc:  # noqa: BLE001
        if transport_failure(exc):
            unknown(f"{cid}: support URL was not reached ({exc}): {url} — "
                    f"liveness unevaluated, not disproved")
        else:
            fail(f"{cid}: support URL returned an error ({exc}): {url}")


def check_public_claim_counts(expected: int, today: dt.date) -> None:
    """Require every public claim count to declare whether it is live or dated.

    Generated pages already derive their values from ``claims.yaml``. The
    homepage and ``/now/`` are hand-written, however, and a historical
    sentence there previously looked like a competing live count. This check
    makes that distinction executable rather than relying on a reader to
    infer it from surrounding prose.
    """
    for rel, expected_state in sorted(CLAIM_COUNT_SURFACES.items()):
        page = ROOT / rel
        if not page.is_file():
            fail(f"{rel}: public claim-count surface is missing")
            continue
        raw = page.read_text(encoding="utf-8")
        markers = 0

        def inspect_marker(match: re.Match[str]) -> str:
            nonlocal markers
            attrs = match.group("attrs")
            state = match.group("state")
            markers += 1
            if state != expected_state:
                fail(f"{rel}: claim-count marker is {state}, expected "
                     f"{expected_state}")
            visible = TAG_TEXT.sub(" ", match.group("body"))
            values = [int(found.group("count"))
                      for found in CLAIM_COUNT_TEXT.finditer(visible)]
            if len(values) != 1:
                fail(f"{rel}: {state} claim-count marker must contain exactly "
                     f"one 'N claims' value, found {values or 'none'}")
                return " "
            value = values[0]
            if state == "current":
                if value != expected:
                    fail(f"{rel}: current claim count {value} disagrees with "
                         f"claims.yaml ({expected})")
            else:
                date_match = AS_OF.search(attrs)
                if not date_match:
                    fail(f"{rel}: historical claim count {value} has no "
                         "data-as-of date")
                else:
                    try:
                        as_of = dt.date.fromisoformat(date_match.group("date"))
                    except ValueError:
                        fail(f"{rel}: historical claim count {value} has an "
                             f"invalid data-as-of date {date_match.group('date')!r}")
                    else:
                        if as_of > today:
                            fail(f"{rel}: historical claim count {value} is "
                                 f"dated in the future ({as_of})")
            return " "

        unmarked = CLAIM_COUNT_MARKER.sub(inspect_marker, raw)
        # Keep adjacent elements adjacent. Replacing every tag with a space
        # would turn a module's visual label ``07`` + ``Claim envelope`` into
        # the false phrase "07 claims".
        for found in CLAIM_COUNT_TEXT.finditer(TAG_TEXT.sub("", unmarked)):
            fail(f"{rel}: unmarked claim count {found.group('count')} — mark "
                 "it current or historical with data-as-of")
        if markers != 1:
            fail(f"{rel}: expected exactly one {expected_state} claim-count "
                 f"marker, found {markers}")
        else:
            if expected_state == "current":
                ok(f"{rel}: current claim count is explicitly bound to "
                   f"claims.yaml ({expected})")
            else:
                ok(f"{rel}: historical claim count is explicitly dated")


def exit_code() -> int:
    """Collapse the two buckets into this module's three-state exit contract.

    Kept as its own function so verify_claims_states.py can execute the real
    branch. A test that re-implements this logic would pass while the contract
    silently regressed, which is the failure mode the contract exists to stop.
    """
    if failures:
        print(f"{len(failures)} check(s) failed; {len(unknowns)} could not be "
              f"evaluated.")
        return 1
    if unknowns:
        print(f"0 check(s) failed; {len(unknowns)} could not be evaluated "
              f"because the source was never reached. The registry is NOT "
              f"verified — an unevaluated check is not a passing one — and "
              f"this run is not a finding about any binding. Re-run from a "
              f"network that can reach the listed sources.")
        return 2
    print("Registry verified: shaped, falsifiers and forbidden rescues "
          "declared, bound, fresh, triggers quiet, support reachable, "
          "ledger covered.")
    return 0


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

    owner_review = str(registry.get("last_owner_review", ""))
    newest_claim_review = max(str(c.get("last_reviewed", "")) for c in claims)
    if owner_review < newest_claim_review:
        fail(f"last_owner_review {owner_review} lags newest claim review "
             f"{newest_claim_review}")
    else:
        ok(f"last_owner_review {owner_review} covers all claim reviews")

    if owner_review in index_html:
        ok(f"index.html states the registry's last owner review date "
           f"({owner_review})")
    else:
        fail(f"index.html does not state the registry's last owner review "
             f"date ({owner_review!r})")
    check_public_claim_counts(len(claims), today)

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

    for claim in claims:
        cid = claim.get("id", "<missing id>")

        missing = REQUIRED - set(claim)
        if missing:
            fail(f"{cid}: missing fields {sorted(missing)}")
            continue

        check_dimensions(cid, claim["dimensions"])
        check_support_rights(cid, claim.get("support") or {})
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
    return exit_code()


if __name__ == "__main__":
    sys.exit(main())
