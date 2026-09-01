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

# The status of a claim and the status of the research object it describes are
# different facts, and collapsing them is the most available way for an honest
# registry to mislead a skimmer. "CC-005: supported within scope" is true — its
# scope is a contract document. The study that document governs has collected
# nothing. A reader who sees only the first pill concludes the opposite of the
# truth, so a claim that speaks about a research object must declare that
# object's own state, and the generated surfaces must render it separately from
# the evidential-status pill.
STUDY_STATES = {"not_started", "untested", "not_activated", "dry_run_only",
                "in_collection", "complete"}

failures: list[str] = []
holds: list[str] = []

# Liveness is three-valued, not two. A support URL that answers 404 or 410 has
# been withdrawn: that is an observation about the evidence, and it fails. A
# support URL this runner could not reach — an egress policy answering 403 to
# CONNECT, a proxy 407, a 429, a 5xx, a DNS or timeout error — has told the
# runner nothing about the resource at all. Printing "unreachable" for that
# second case reports a fact the run did not establish, and it is the same
# error this registry forbids everywhere else: filling an unmeasured cell with
# the convenient reading. The unmeasured cell here is "does this URL still
# resolve for a reader," and a blocked runner does not get to answer it in
# either direction.
#
# Indeterminate is not a free pass, because a blanket "network trouble does not
# count" is precisely a forbidden rescue. It is discharged only by an
# independent witness on a different host: the claim's own
# remote_content_change trigger fetches the bound file at the bound ref from
# raw.githubusercontent.com, and a success there proves that exact
# (repository, commit) pair is still served publicly — which a deleted,
# privatised, or history-rewritten repository could not do. With that witness
# the run reports HOLD and continues; without it the run fails, and says the
# state is indeterminate rather than asserting a withdrawal nobody observed.
# On an unrestricted runner nothing is indeterminate and this path never
# executes, so the gate is not loosened in the environment that enforces it.
WITHDRAWN_CODES = frozenset({404, 410})
GITHUB_OBJECT = re.compile(
    r"^https://github\.com/(?P<repo>[^/]+/[^/]+)/"
    r"(?:blob|tree|commit|raw)/(?P<ref>[0-9a-f]{7,40})(?:[/?#]|$)")

# (repo, bound_ref) -> path of a file this run actually fetched from the raw
# host at that ref. Written by the executable triggers, read by liveness.
bound_ref_witnesses: dict[tuple[str, str], str] = {}

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


def ok(msg: str) -> None:
    print(f"ok    {msg}")


def hold(msg: str) -> None:
    """Record a check the run could not perform, without scoring it either way."""
    holds.append(msg)
    print(f"hold  {msg}")


def classify_probe(exc: Exception) -> tuple[str, str]:
    """Name what a failed fetch established about the resource itself.

    Only 404 and 410 are statements about the resource. Everything else —
    authorisation, proxy policy, rate limits, server faults, transport errors
    — is a statement about the path between this runner and the resource.
    """
    code = getattr(exc, "code", None)
    if code in WITHDRAWN_CODES:
        return "withdrawn", f"HTTP {code}"
    if code is not None:
        return "indeterminate", f"HTTP {code}"
    return "indeterminate", str(exc)


def witness_for(url: str) -> tuple[str, str, str] | None:
    """Find a bound-ref fetch from this run that covers the URL's own object."""
    match = GITHUB_OBJECT.match(str(url))
    if not match:
        return None
    repo, ref = match.group("repo"), match.group("ref")
    for (witness_repo, witness_ref), path in bound_ref_witnesses.items():
        if witness_repo != repo:
            continue
        if witness_ref.startswith(ref) or ref.startswith(witness_ref):
            return witness_repo, witness_ref, path
    return None


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


def check_study_state(cid: str, claim: dict) -> bool:
    """Validate an optional study_state block. Returns True when one is declared."""
    block = claim.get("study_state")
    if block is None:
        return False
    if not isinstance(block, dict):
        fail(f"{cid}: study_state must be a mapping, got {type(block).__name__}")
        return False
    state = block.get("state")
    if state not in STUDY_STATES:
        fail(f"{cid}: study_state.state={state!r} not in {sorted(STUDY_STATES)}")
    for field in ("object", "note"):
        if not str(block.get(field) or "").strip():
            fail(f"{cid}: study_state.{field} is required and must be non-empty")
    if state in {"untested", "not_started", "not_activated", "dry_run_only"} \
            and claim.get("dimensions", {}).get("evidential_status") == "supported_within_scope":
        # Permitted, and exactly the case the separate rendering exists for:
        # the claim is supported about a document while its study has no result.
        ok(f"{cid}: claim supported within scope while its study is {state} — "
           f"rendered as separate states, never as one")
    else:
        ok(f"{cid}: study state declared — {state}")
    return True


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
            bound_bytes = fetch(
                f"https://raw.githubusercontent.com/{repo}/{ref}/{path}")
        except Exception as exc:  # noqa: BLE001
            state, detail = classify_probe(exc)
            fail(f"{cid}: bound-evidence fetch {state} for {repo}/{path} "
                 f"({detail}) — the trigger did not run")
            return
        # A second host answered for exactly the (repository, commit) pair a
        # support URL can name. This is the only thing allowed to discharge an
        # indeterminate liveness probe, so it is recorded where liveness reads
        # it — and only ever on a fetch that actually succeeded.
        bound_ref_witnesses.setdefault((str(repo), str(ref)), str(path))
        try:
            head_bytes = fetch(
                f"https://raw.githubusercontent.com/{repo}/HEAD/{path}")
        except Exception as exc:  # noqa: BLE001
            state, detail = classify_probe(exc)
            fail(f"{cid}: default-branch fetch {state} for {repo}/{path} "
                 f"({detail}) — the trigger did not run")
            return
        bound = hashlib.sha256(bound_bytes).hexdigest()
        head = hashlib.sha256(head_bytes).hexdigest()
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
    except Exception as exc:  # noqa: BLE001
        state, detail = classify_probe(exc)
        if state == "withdrawn":
            fail(f"{cid}: support URL withdrawn ({detail}): {url}")
            return
        witness = witness_for(url)
        if witness is None:
            fail(f"{cid}: support URL liveness indeterminate from this runner "
                 f"({detail}) and no bound-ref witness covers it: {url}")
            return
        witness_repo, witness_ref, witness_path = witness
        hold(f"{cid}: liveness indeterminate from this runner ({detail}); the "
             f"bound object is still served — raw {witness_repo}@"
             f"{witness_ref[:8]}/{witness_path}: {url}")
        return
    ok(f"{cid}: support URL resolves — {url}")


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


def main() -> int:
    registry = yaml.safe_load((ROOT / "claims.yaml").read_text())
    claims = registry.get("claims", [])
    if not claims:
        fail("registry contains no claims")
        return 1
    ok(f"registry schema v{registry.get('version')} loaded with {len(claims)} claims")

    today = dt.date.today()
    ledger_html = (ROOT / "ledger" / "index.html").read_text()
    observatory_html = (ROOT / "observatory" / "index.html").read_text()
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
        declares_study_state = check_study_state(cid, claim)
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

        # A declared study state that no public surface prints is a private
        # caveat, which is the failure mode this field exists to prevent.
        if declares_study_state:
            marker = f'data-study-state-for="{cid}"'
            missing_from = [name for name, html in
                            (("ledger", ledger_html), ("observatory", observatory_html))
                            if marker not in html]
            if missing_from:
                fail(f"{cid}: study_state declared but not rendered in "
                     f"{', '.join(missing_from)}")
            else:
                ok(f"{cid}: study state rendered separately in ledger and observatory")

    print()
    if holds:
        print(f"{len(holds)} liveness probe(s) indeterminate from this runner "
              f"and corroborated by a bound-ref witness on the raw host. A "
              f"HOLD is not a liveness verification: it records that this "
              f"runner could not test the reader-facing URL, and that the "
              f"object it names had not been withdrawn.")
    if failures:
        print(f"{len(failures)} check(s) failed.")
        return 1
    print("Registry verified: shaped, falsifiers and forbidden rescues "
          "declared, bound, fresh, triggers quiet, support resolved or "
          "witness-held, ledger covered.")
    return 0


def _self_test() -> int:
    """Offline assertions for the three-valued liveness rule.

    The rule decides whether a red build is evidence about someone else's
    repository or evidence about this runner's network. That distinction is
    not observable on a green CI box — the only place it fires is a restricted
    network — so it is asserted here against synthetic responses instead of
    being trusted because a normal run passed. Nothing in this test touches
    the network.
    """
    import contextlib
    import io
    import urllib.error

    def http(code: int) -> urllib.error.HTTPError:
        return urllib.error.HTTPError("https://example.invalid/x", code,
                                      "synthetic", {}, None)

    transport = urllib.error.URLError("Tunnel connection failed: 403 Forbidden")

    cases = [
        (http(404), "withdrawn"), (http(410), "withdrawn"),
        (http(403), "indeterminate"), (http(407), "indeterminate"),
        (http(429), "indeterminate"), (http(503), "indeterminate"),
        (transport, "indeterminate"), (TimeoutError("timed out"), "indeterminate"),
    ]
    problems: list[str] = []
    for exc, expected in cases:
        state, _ = classify_probe(exc)
        if state != expected:
            problems.append(f"classify_probe({exc!r}) = {state}, expected {expected}")

    saved_witnesses = dict(bound_ref_witnesses)
    saved_failures, saved_holds = list(failures), list(holds)
    saved_fetch = globals()["fetch"]
    try:
        bound_ref_witnesses.clear()
        bound_ref_witnesses[("Owner/Repo", "a" * 40)] = "docs/x.md"

        witness_cases = [
            (f"https://github.com/Owner/Repo/commit/{'a' * 40}", True),
            (f"https://github.com/Owner/Repo/blob/{'a' * 40}/docs/y.md", True),
            ("https://github.com/Owner/Repo/commit/aaaaaaa", True),
            (f"https://github.com/Other/Repo/commit/{'a' * 40}", False),
            (f"https://github.com/Owner/Repo/commit/{'b' * 40}", False),
            ("https://github.com/Owner/Repo", False),
            ("https://academy.claude.com/tutorials/x", False),
        ]
        for url, expected_hit in witness_cases:
            if (witness_for(url) is not None) != expected_hit:
                problems.append(f"witness_for({url}) hit != {expected_hit}")

        # End-to-end: the same 403, with and without a covering witness, must
        # land on opposite sides of the build.
        def raising(exc):
            def _fetch(url: str) -> bytes:
                raise exc
            return _fetch

        scenarios = [
            (http(403), f"https://github.com/Owner/Repo/commit/{'a' * 40}", "hold"),
            (http(403), f"https://github.com/Owner/Repo/commit/{'b' * 40}", "fail"),
            (http(404), f"https://github.com/Owner/Repo/commit/{'a' * 40}", "fail"),
            (transport, "https://academy.claude.com/tutorials/x", "fail"),
        ]
        for exc, url, expected in scenarios:
            failures.clear()
            holds.clear()
            globals()["fetch"] = raising(exc)
            with contextlib.redirect_stdout(io.StringIO()):
                check_url_liveness("TEST", url)
            got = "fail" if failures else ("hold" if holds else "ok")
            if got != expected:
                problems.append(f"liveness({exc!r}, {url}) = {got}, expected {expected}")

        # A witness may only be recorded by a fetch that succeeded.
        failures.clear()
        holds.clear()
        bound_ref_witnesses.clear()
        globals()["fetch"] = raising(http(403))
        with contextlib.redirect_stdout(io.StringIO()):
            check_trigger("TEST", {"type": "remote_content_change",
                                   "enforcement": "executable",
                                   "repo": "Owner/Repo", "path": "docs/x.md",
                                   "bound_ref": "c" * 40})
        if bound_ref_witnesses:
            problems.append("a failed bound-evidence fetch recorded a witness")
        if not failures:
            problems.append("a failed bound-evidence fetch did not fail the run")
    finally:
        globals()["fetch"] = saved_fetch
        bound_ref_witnesses.clear()
        bound_ref_witnesses.update(saved_witnesses)
        failures.clear()
        failures.extend(saved_failures)
        holds.clear()
        holds.extend(saved_holds)

    for problem in problems:
        print(f"FAIL  liveness classification: {problem}")
    if problems:
        print(f"{len(problems)} liveness classification assertion(s) failed.")
        return 1
    print(f"ok    liveness classification: {len(cases)} probe classes, "
          f"{len(witness_cases)} witness lookups, {len(scenarios)} end-to-end "
          f"outcomes, and the witness-only-on-success rule all hold")
    return 0


if __name__ == "__main__":
    if "--test" in sys.argv[1:]:
        sys.exit(_self_test())
    sys.exit(main())
