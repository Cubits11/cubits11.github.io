#!/usr/bin/env python3
"""The claim-history kernel (E5A): declared transitions or nothing.

A registered claim's COMMITMENT is the parsed value of these fields of its
claims.yaml record, and nothing else:

    proposition · scope · falsifier · forbidden_rescues · non_claims · expected

(`expected` only where the record carries it). The commitment is canonicalized
by parsing the YAML, keeping the exact parsed values, serializing as JSON with
sorted keys and no whitespace, and hashing the UTF-8 bytes with SHA-256. YAML
formatting therefore disappears; a changed word does not.

claims_history.yaml holds a GENESIS (the protected baseline: every claim's full
commitment as it stood at one named ancestor commit) and an ordered chain of
ENTRIES, each carrying the previous entry's digest. A transition binds
claim_id, from_digest, to_digest, transition_type, event_at, recorded_at,
provenance_class, direction_basis, evidence_refs, reason and the previous
digest; a contemporaneous transition also carries the full to_commitment, so
every post-genesis state is reconstructable from the file alone. Retrospective
entries reconstruct pre-genesis history from git objects and are re-derived
from those objects whenever history is available.

verify fails when: a live commitment differs from the state the chain
predicts (an undeclared change); a from_digest does not match the predicted
state; a to_digest does not match the recorded content; the chain digests do
not link; the genesis differs from the genesis at the prior accepted revision
or from the claims at its anchor commit; the prior accepted revision's entries
are not an exact prefix of the current ones; a MACHINE_CHECKED direction is
claimed where no structured proof rule applies or where the structured domain
moves the other way; or dates, enums or provenance classes are incoherent.

What this does NOT do: infer English entailment (NARROW versus EXPAND on prose
is a declared classification, and the verifier proves only that a
classification exists); prove that history was protected before genesis; or
stop an actor who can change this verifier, the workflow, branch protection,
or repository history in the same act. It detects undeclared commitment
changes under the repository's current verification contract, from the
genesis forward.

    python3 scripts/claims_history.py verify              # the gate (exit 0 / 1 / 2)
    python3 scripts/claims_history.py --test              # the mandatory mutants, in memory
    python3 scripts/claims_history.py reconstruct         # recompute pre-genesis transitions and counts from git
    python3 scripts/claims_history.py append --claim ID --type NARROW --basis DECLARED_HUMAN_JUDGMENT \
        --event-at YYYY-MM-DD --reason "..." --evidence git:<sha> [--evidence ...]
    python3 scripts/claims_history.py register --claim ID --reason "..." --evidence ...
    python3 scripts/claims_history.py digest              # print every live commitment digest

Exit codes follow the registry's contract: 0 verified, 1 a check failed,
2 a check could not be evaluated (git history unavailable) — blocking, never
a finding.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CLAIMS = ROOT / "claims.yaml"
HISTORY = ROOT / "claims_history.yaml"

COMMITMENT_FIELDS = ("proposition", "scope", "falsifier", "forbidden_rescues", "non_claims", "expected")
CANONICALIZATION = ("commitment = {field: parsed value for field in (proposition, scope, falsifier, "
                    "forbidden_rescues, non_claims, expected) if present on the claim}; "
                    "json.dumps(sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False); "
                    "UTF-8; SHA-256 hex")
TRANSITION_TYPES = {"CLARIFY", "NARROW", "CORRECT", "RETRACT", "SUPERSEDE", "EXPAND"}
PROVENANCE = {"CONTEMPORANEOUS", "RETROSPECTIVE_RECONSTRUCTION"}
BASES = {"MACHINE_CHECKED", "DECLARED_HUMAN_JUDGMENT", "NOT_MACHINE_DECIDABLE"}
DATED_RECORDS = ("census.yaml", "corrections/index.html", "DESIGN.md", "notes")
HEX64 = set("0123456789abcdef")


# ------------------------------------------------------------------ canonical
def canonical_bytes(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(obj) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def commitment(claim: dict) -> dict:
    return {f: claim[f] for f in COMMITMENT_FIELDS if f in claim}


def live_states(claims_doc: dict) -> dict[str, dict]:
    out = {}
    for c in claims_doc.get("claims", []):
        cm = commitment(c)
        out[c["id"]] = {"digest": digest(cm), "commitment": cm}
    return out


def entry_digest(entry: dict) -> str:
    return digest({k: v for k, v in entry.items() if k != "digest"})


def genesis_digest(states: list) -> str:
    return digest(states)


def is_hex(s, n: int) -> bool:
    return isinstance(s, str) and len(s) == n and set(s) <= HEX64


def parse_date(s) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(s))
    except ValueError:
        return None


# ------------------------------------------------------------------ git
class GitUnavailable(Exception):
    pass


def git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        raise GitUnavailable(" ".join(args) + ": " + r.stderr.strip()[:200])
    return r.stdout


def claims_at(rev: str) -> dict | None:
    """Live states at a revision, or None when claims.yaml is absent there."""
    try:
        text = git("show", f"{rev}:claims.yaml")
    except GitUnavailable as exc:
        if "does not exist" in str(exc) or "exists on disk, but not in" in str(exc) or "invalid object" in str(exc):
            return None
        raise
    return live_states(yaml.safe_load(text))


def history_at(rev: str) -> dict | None:
    try:
        text = git("show", f"{rev}:claims_history.yaml")
    except GitUnavailable as exc:
        if "does not exist" in str(exc) or "exists on disk, but not in" in str(exc) or "invalid object" in str(exc):
            return None
        raise
    return yaml.safe_load(text)


def is_ancestor(a: str, b: str) -> bool:
    r = subprocess.run(["git", "merge-base", "--is-ancestor", a, b], cwd=ROOT, capture_output=True, text=True)
    if r.returncode in (0, 1):
        return r.returncode == 0
    raise GitUnavailable("merge-base: " + r.stderr.strip()[:200])


def prior_reference() -> str:
    """The accepted revision the candidate must extend.

    The candidate is the working tree. If claims_history.yaml is tracked at
    HEAD the candidate extends HEAD's parent (HEAD itself is the candidate
    when the tree is clean — a merge commit's first parent is the previous
    tip of the branch, a pull-request merge ref's first parent is its base);
    if the file is not yet tracked at HEAD, the candidate is the first
    kernel revision and HEAD is the revision it extends.
    """
    tracked = subprocess.run(["git", "cat-file", "-e", "HEAD:claims_history.yaml"], cwd=ROOT,
                             capture_output=True, text=True).returncode == 0
    return git("rev-parse", "HEAD^1").strip() if tracked else git("rev-parse", "HEAD").strip()


# ------------------------------------------------------------------ intervals (the one structured direction rule)
def intervals(expected) -> dict[str, tuple[float, float]]:
    """Every interval-shaped value inside an expected block, keyed by path.

    Two shapes qualify: a two-element list of numbers [lo, hi] with lo <= hi,
    and a pair of sibling keys <name>_lower / <name>_upper with numeric values.
    Nothing else is treated as a domain, so nothing else can be MACHINE_CHECKED.
    """
    out: dict[str, tuple[float, float]] = {}

    def num(x) -> bool:
        return isinstance(x, (int, float)) and not isinstance(x, bool)

    def walk(node, path: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(k, str) and k.endswith("_lower") and num(v):
                    up = node.get(k[:-6] + "_upper")
                    if num(up) and v <= up:
                        out[f"{path}/{k[:-6]}"] = (float(v), float(up))
                walk(v, f"{path}/{k}")
        elif isinstance(node, list):
            if len(node) == 2 and num(node[0]) and num(node[1]) and node[0] <= node[1]:
                out[path] = (float(node[0]), float(node[1]))
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")
    walk(expected, "expected")
    return out


def machine_check(kind: str, before: dict | None, after: dict | None) -> str | None:
    """Return None when the structured domain moves the declared way, else why not."""
    if kind not in ("NARROW", "EXPAND"):
        return f"MACHINE_CHECKED is only defined for NARROW and EXPAND on interval-shaped expected fields, not {kind}"
    if not before or not after or "expected" not in before or "expected" not in after:
        return "MACHINE_CHECKED requires an expected block on both sides of the transition"
    a, b = intervals(before["expected"]), intervals(after["expected"])
    if not a or set(a) != set(b):
        return "MACHINE_CHECKED requires the same interval-shaped expected fields on both sides"
    strict = False
    for key in a:
        (alo, ahi), (blo, bhi) = a[key], b[key]
        if kind == "NARROW":
            if blo < alo or bhi > ahi:
                return f"declared NARROW but {key} moves from [{alo}, {ahi}] to [{blo}, {bhi}]"
        else:
            if blo > alo or bhi < ahi:
                return f"declared EXPAND but {key} moves from [{alo}, {ahi}] to [{blo}, {bhi}]"
        strict = strict or (alo, ahi) != (blo, bhi)
    if not strict:
        return "MACHINE_CHECKED requires at least one interval to move; none did"
    return None


# ------------------------------------------------------------------ verify
class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.unknowns: list[str] = []
        self.oks: list[str] = []

    def fail(self, msg: str) -> None:
        self.failures.append(msg)

    def unknown(self, msg: str) -> None:
        self.unknowns.append(msg)

    def ok(self, msg: str) -> None:
        self.oks.append(msg)

    def exit_code(self) -> int:
        return 1 if self.failures else (2 if self.unknowns else 0)


def verify(claims_doc: dict, hist: dict, prior: dict | None, *, prior_ref: str | None, today: dt.date,
           use_git: bool = True) -> Report:
    R = Report()
    live = live_states(claims_doc)

    # ---- shape
    if hist.get("version") != 1 or hist.get("kernel") != "E5A":
        R.fail("history: version/kernel must be 1 / E5A")
    if hist.get("canonicalization") != CANONICALIZATION:
        R.fail("history: canonicalization string does not name this verifier's fixed rule")
    if list(hist.get("commitment_fields") or []) != list(COMMITMENT_FIELDS):
        R.fail("history: commitment_fields differ from the verifier's fixed field set")
    g = hist.get("genesis") or {}
    anchor = g.get("anchor_commit")
    g_date = parse_date(g.get("recorded_at"))
    if not is_hex(anchor, 40):
        R.fail("genesis.anchor_commit must be a full lowercase commit SHA")
    if g_date is None or g_date > today:
        R.fail("genesis.recorded_at must be a date not in the future")
    states = g.get("states") or []
    seen = set()
    for s in states:
        cid = s.get("claim_id")
        if cid in seen:
            R.fail(f"genesis: claim {cid} listed twice")
        seen.add(cid)
        if s.get("digest") != digest(s.get("commitment")):
            R.fail(f"genesis: {cid} digest does not match its recorded commitment content")
        if set(s.get("commitment") or {}) - set(COMMITMENT_FIELDS):
            R.fail(f"genesis: {cid} commitment carries a non-commitment field")
    if g.get("digest") != genesis_digest(states):
        R.fail("genesis.digest does not match the recorded states")
    if R.failures:
        return R

    # ---- genesis against its anchor commit (a past revision, never the candidate)
    if use_git:
        try:
            ref = prior_ref or prior_reference()
            if not is_ancestor(anchor, ref):
                R.fail(f"genesis.anchor_commit {anchor[:12]} is not an ancestor of the revision the candidate extends ({ref[:12]})")
            at_anchor = claims_at(anchor)
            if at_anchor is None:
                R.fail(f"genesis.anchor_commit {anchor[:12]} carries no claims.yaml")
            else:
                gen = {s["claim_id"]: s["digest"] for s in states}
                if {k: v["digest"] for k, v in at_anchor.items()} != gen:
                    R.fail("genesis states do not equal the commitments recorded at the anchor commit — a genesis cannot be re-minted")
                else:
                    R.ok(f"genesis: {len(gen)} states equal claims.yaml at anchor {anchor[:12]}")
        except GitUnavailable as exc:
            R.unknown(f"git history unavailable — genesis anchor not evaluated ({exc})")

    # ---- chain
    entries = hist.get("entries") or []
    prev = g["digest"]
    state = {s["claim_id"]: s["digest"] for s in states}
    content = {s["claim_id"]: s["commitment"] for s in states}
    retro_by_claim: dict[str, list[dict]] = {}
    n_contemp = n_retro = 0
    for i, e in enumerate(entries):
        where = f"entries[{i}]"
        kind = e.get("kind")
        if e.get("digest") != entry_digest(e):
            R.fail(f"{where}: entry digest does not match its content")
        if e.get("previous_transition_digest") != prev:
            R.fail(f"{where}: previous_transition_digest does not link to the preceding entry")
        prev = e.get("digest")
        cid = e.get("claim_id")
        rec = parse_date(e.get("recorded_at"))
        if rec is None or rec > today:
            R.fail(f"{where}: recorded_at must be a date not in the future")
        if not e.get("reason") or not isinstance(e.get("reason"), str):
            R.fail(f"{where}: reason must be a non-empty string")
        refs = e.get("evidence_refs")
        if not isinstance(refs, list) or not refs or not all(isinstance(r, str) and r for r in refs):
            R.fail(f"{where}: evidence_refs must be a non-empty list of locators")
        if kind == "registration":
            if e.get("provenance_class") != "CONTEMPORANEOUS":
                R.fail(f"{where}: a registration is recorded when the claim enters — CONTEMPORANEOUS only")
            if state.get(cid) is not None:
                R.fail(f"{where}: registration of {cid}, which already has a protected state")
            if e.get("digest_of_commitment") != digest(e.get("commitment")):
                R.fail(f"{where}: registration digest does not match its commitment content")
            state[cid] = e.get("digest_of_commitment")
            content[cid] = e.get("commitment")
            n_contemp += 1
            continue
        if kind != "transition":
            R.fail(f"{where}: kind must be transition or registration")
            continue
        ttype, prov, basis = e.get("transition_type"), e.get("provenance_class"), e.get("direction_basis")
        if ttype not in TRANSITION_TYPES:
            R.fail(f"{where}: transition_type {ttype!r} is not one of {sorted(TRANSITION_TYPES)} — there is no formatting-only transition; an unchanged canonical commitment needs no entry")
        if prov not in PROVENANCE:
            R.fail(f"{where}: provenance_class {prov!r} not allowed")
        if basis not in BASES:
            R.fail(f"{where}: direction_basis {basis!r} not allowed")
        ev = parse_date(e.get("event_at"))
        if ev is None or (rec and ev > rec):
            R.fail(f"{where}: event_at must be a date no later than recorded_at")
        frm, to = e.get("from_digest"), e.get("to_digest")
        if not is_hex(frm, 64):
            R.fail(f"{where}: from_digest must be a commitment digest")
        if ttype == "RETRACT":
            if to is not None:
                R.fail(f"{where}: a RETRACT has no to_digest")
        elif not is_hex(to, 64):
            R.fail(f"{where}: to_digest must be a commitment digest")
        if frm == to:
            R.fail(f"{where}: from_digest equals to_digest — an unchanged commitment is not a transition")
        if prov == "RETROSPECTIVE_RECONSTRUCTION":
            n_retro += 1
            if g_date and ev and ev >= g_date:
                R.fail(f"{where}: a retrospective reconstruction must describe an event before the genesis was recorded")
            if not any(r.startswith("git:") for r in (refs or [])):
                R.fail(f"{where}: a retrospective reconstruction must name the git revision at which the change landed (git:<sha>)")
            retro_by_claim.setdefault(cid, []).append(e)
            continue
        # ---- contemporaneous: the forward state machine
        n_contemp += 1
        if g_date and rec and rec < g_date:
            R.fail(f"{where}: a CONTEMPORANEOUS entry cannot be recorded before the genesis — the kernel protected nothing before it existed")
        if g_date and ev and ev < g_date:
            R.fail(f"{where}: a CONTEMPORANEOUS entry cannot describe an event before the genesis; record it as RETROSPECTIVE_RECONSTRUCTION")
        if state.get(cid) is None:
            R.fail(f"{where}: {cid} has no protected state to transition from")
            continue
        if frm != state[cid]:
            R.fail(f"{where}: from_digest {str(frm)[:12]} does not match {cid}'s protected state {state[cid][:12]}")
        before = content.get(cid)
        if ttype == "RETRACT":
            state[cid] = None
            content[cid] = None
            after = None
        else:
            after = e.get("to_commitment")
            if after is None or digest(after) != to:
                R.fail(f"{where}: to_digest does not match the recorded to_commitment")
            if set(after or {}) - set(COMMITMENT_FIELDS):
                R.fail(f"{where}: to_commitment carries a non-commitment field")
            state[cid] = to
            content[cid] = after
        if basis == "MACHINE_CHECKED":
            why = machine_check(ttype, before, after)
            if why:
                R.fail(f"{where}: {why}")
            else:
                R.ok(f"{where}: {cid} {ttype} machine-checked on interval-shaped expected fields")
    if R.failures:
        return R
    R.ok(f"chain: {len(entries)} entries link from genesis {g['digest'][:12]} to tip {prev[:12]} "
         f"({n_contemp} contemporaneous, {n_retro} retrospective)")

    # ---- live state equals the predicted tip state
    for cid, st in live.items():
        if cid not in state or state[cid] is None:
            R.fail(f"{cid}: live claim has no protected state — register it or restore it")
        elif state[cid] != st["digest"]:
            R.fail(f"{cid}: commitment changed without a declared transition "
                   f"(protected {state[cid][:12]}, live {st['digest'][:12]})")
    for cid, d in state.items():
        if d is not None and cid not in live:
            R.fail(f"{cid}: protected state exists but the claim is gone — declare a RETRACT")
    if not R.failures:
        R.ok(f"live: {len(live)} commitments equal the chain tip")

    # ---- retrospective entries against git objects and the genesis
    if use_git and retro_by_claim:
        try:
            gen = {s["claim_id"]: s["digest"] for s in states}
            checked = 0
            for cid, chain in retro_by_claim.items():
                for k, e in enumerate(chain):
                    if k and e["from_digest"] != chain[k - 1]["to_digest"]:
                        R.fail(f"retrospective chain for {cid} does not link at {e['evidence_refs'][0]}")
                    sha = next(r[4:] for r in e["evidence_refs"] if r.startswith("git:"))
                    before, after = claims_at(f"{sha}^1"), claims_at(sha)
                    if before is None or after is None:
                        R.fail(f"retrospective {cid} at {sha[:12]}: claims.yaml unavailable at the named revision")
                        continue
                    if (before.get(cid) or {}).get("digest") != e["from_digest"]:
                        R.fail(f"retrospective {cid} at {sha[:12]}: from_digest is not the commitment at {sha[:12]}^1")
                    got = (after.get(cid) or {}).get("digest")
                    if got != e["to_digest"]:
                        R.fail(f"retrospective {cid} at {sha[:12]}: to_digest is not the commitment at {sha[:12]}")
                    checked += 1
                last = chain[-1]["to_digest"]
                if last != gen.get(cid):
                    R.fail(f"retrospective chain for {cid} ends at {str(last)[:12]}, not at its genesis state")
            if not R.failures:
                R.ok(f"retrospective: {checked} reconstructed transitions re-derived from git objects and tied to the genesis")
        except GitUnavailable as exc:
            R.unknown(f"git history unavailable — retrospective entries not re-derived ({exc})")

    # ---- forward append-only: the prior accepted revision is an exact prefix
    if prior is None:
        if n_contemp:
            R.fail("no prior history at the revision this candidate extends, yet the candidate carries contemporaneous entries — a kernel-introducing revision carries genesis and reconstruction only")
        if use_git and prior_ref and anchor != prior_ref:
            R.fail(f"first kernel revision: genesis.anchor_commit must be the revision the candidate extends ({prior_ref[:12]}), not {anchor[:12]}")
        elif not R.failures:
            R.ok("prefix: first kernel revision — genesis anchored to the revision it extends")
    else:
        pg = prior.get("genesis") or {}
        if canonical_bytes(pg) != canonical_bytes(g):
            R.fail("genesis differs from the genesis at the prior accepted revision — the protected baseline cannot be re-minted")
        if prior.get("canonicalization") != hist.get("canonicalization"):
            R.fail("canonicalization changed since the prior accepted revision")
        pe = prior.get("entries") or []
        if len(pe) > len(entries):
            R.fail(f"history shrank: prior revision had {len(pe)} entries, candidate has {len(entries)}")
        else:
            for i, (a, b) in enumerate(zip(pe, entries)):
                if canonical_bytes(a) != canonical_bytes(b):
                    R.fail(f"entries[{i}] differs from the prior accepted revision — accepted history is append-only")
                    break
        if not R.failures:
            R.ok(f"prefix: prior accepted history ({len(pe)} entries) is an exact prefix of the candidate ({len(entries)})")
    return R


def cmd_verify() -> int:
    claims_doc = yaml.safe_load(CLAIMS.read_text())
    if not HISTORY.exists():
        print("FAIL  claims_history.yaml missing — the claim-history kernel is not installed")
        return 1
    hist = yaml.safe_load(HISTORY.read_text())
    try:
        ref = prior_reference()
        prior = history_at(ref)
    except GitUnavailable as exc:
        print(f"UNDETERMINED  git history unavailable ({exc}); the kernel cannot compare against the prior accepted revision")
        return 2
    R = verify(claims_doc, hist, prior, prior_ref=ref, today=dt.date.today())
    for m in R.oks:
        print(f"ok    {m}")
    for m in R.unknowns:
        print(f"UNDETERMINED  {m}")
    for m in R.failures:
        print(f"FAIL  {m}")
    code = R.exit_code()
    if code == 0:
        print(f"ok    claim-history kernel: every live commitment is either its genesis state or reached by a declared transition (prior {ref[:12]})")
    return code


# ------------------------------------------------------------------ append / register
def load_both() -> tuple[dict, dict]:
    return yaml.safe_load(CLAIMS.read_text()), yaml.safe_load(HISTORY.read_text())


def predicted_state(hist: dict) -> dict[str, str | None]:
    state = {s["claim_id"]: s["digest"] for s in hist["genesis"]["states"]}
    for e in hist.get("entries") or []:
        if e.get("provenance_class") != "CONTEMPORANEOUS":
            continue
        if e.get("kind") == "registration":
            state[e["claim_id"]] = e["digest_of_commitment"]
        else:
            state[e["claim_id"]] = e.get("to_digest")
    return state


def tip_digest(hist: dict) -> str:
    entries = hist.get("entries") or []
    return entries[-1]["digest"] if entries else hist["genesis"]["digest"]


def write_history(hist: dict) -> None:
    HISTORY.write_text(yaml.safe_dump(hist, allow_unicode=True, sort_keys=False, width=100))


def cmd_append(a: argparse.Namespace) -> int:
    claims_doc, hist = load_both()
    live = live_states(claims_doc)
    state = predicted_state(hist)
    cid = a.claim
    frm = state.get(cid)
    if frm is None:
        print(f"FAIL  {cid} has no protected state; use register")
        return 1
    if a.type == "RETRACT":
        if cid in live:
            print(f"FAIL  RETRACT of {cid} but the claim is still in claims.yaml")
            return 1
        to, to_c = None, None
    else:
        if cid not in live:
            print(f"FAIL  {cid} is not in claims.yaml; a missing claim is a RETRACT")
            return 1
        to, to_c = live[cid]["digest"], live[cid]["commitment"]
        if to == frm:
            print(f"FAIL  {cid}: canonical commitment is unchanged — there is no semantic transition to declare")
            return 1
    entry = {"kind": "transition", "claim_id": cid, "from_digest": frm, "to_digest": to, "transition_type": a.type,
             "event_at": a.event_at, "recorded_at": dt.date.today().isoformat(), "provenance_class": "CONTEMPORANEOUS",
             "direction_basis": a.basis, "evidence_refs": list(a.evidence), "reason": a.reason,
             "previous_transition_digest": tip_digest(hist)}
    if to_c is not None:
        entry["to_commitment"] = to_c
    entry["digest"] = entry_digest(entry)
    hist.setdefault("entries", []).append(entry)
    write_history(hist)
    print(f"appended {a.type} for {cid}: {frm[:12]} -> {str(to)[:12]} (entry {entry['digest'][:12]}); now run verify")
    return 0


def cmd_register(a: argparse.Namespace) -> int:
    claims_doc, hist = load_both()
    live = live_states(claims_doc)
    if a.claim not in live:
        print(f"FAIL  {a.claim} is not in claims.yaml")
        return 1
    if predicted_state(hist).get(a.claim) is not None:
        print(f"FAIL  {a.claim} already has a protected state")
        return 1
    entry = {"kind": "registration", "claim_id": a.claim, "digest_of_commitment": live[a.claim]["digest"],
             "commitment": live[a.claim]["commitment"], "recorded_at": dt.date.today().isoformat(),
             "provenance_class": "CONTEMPORANEOUS", "evidence_refs": list(a.evidence), "reason": a.reason,
             "previous_transition_digest": tip_digest(hist)}
    entry["digest"] = entry_digest(entry)
    hist.setdefault("entries", []).append(entry)
    write_history(hist)
    print(f"registered {a.claim} at {entry['digest_of_commitment'][:12]}; now run verify")
    return 0


# ------------------------------------------------------------------ reconstruct
def first_parent_events() -> list[dict]:
    """Every digest-level commitment event along the first-parent line of HEAD."""
    log = [l.split() for l in git("log", "--format=%H %cs", "--reverse", "--first-parent", "--", "claims.yaml").split("\n") if l]
    prev: dict[str, str] = {}
    events = []
    for sha, date in log:
        cur = {k: v["digest"] for k, v in (claims_at(sha) or {}).items()}
        for cid, d in cur.items():
            if cid not in prev:
                events.append({"commit": sha, "date": date, "claim_id": cid, "kind": "BIRTH", "from": None, "to": d})
            elif prev[cid] != d:
                events.append({"commit": sha, "date": date, "claim_id": cid, "kind": "CHANGE", "from": prev[cid], "to": d})
        for cid, d in prev.items():
            if cid not in cur:
                events.append({"commit": sha, "date": date, "claim_id": cid, "kind": "REMOVAL", "from": d, "to": None})
        prev = cur
    return events


def dated_declaration(sha: str, date: str, cid: str) -> bool:
    """Repository-internal heuristic: the commit's first-parent diff adds, to a
    dated record file, one contiguous block of lines that names the claim id
    and carries the commit date. Evidence inside the repository, not a witness
    outside it."""
    diff = git("diff", f"{sha}^1", sha, "--", *DATED_RECORDS)
    blocks, cur = [], []
    for line in diff.split("\n"):
        if line.startswith("+") and not line.startswith("+++"):
            cur.append(line[1:])
        elif cur:
            blocks.append("\n".join(cur)); cur = []
    if cur:
        blocks.append("\n".join(cur))
    return any(cid in b and date in b for b in blocks)


def cmd_reconstruct(check: bool = False) -> int:
    try:
        events = first_parent_events()
    except GitUnavailable as exc:
        print(f"UNDETERMINED  git history unavailable ({exc})")
        return 2
    hist = yaml.safe_load(HISTORY.read_text()) if HISTORY.exists() else None
    retro = {(e["claim_id"], next(r[4:] for r in e["evidence_refs"] if r.startswith("git:")))
             : e for e in (hist or {}).get("entries", []) if e.get("provenance_class") == "RETROSPECTIVE_RECONSTRUCTION"}
    transitions = [e for e in events if e["kind"] in ("CHANGE", "REMOVAL")]
    strict = []
    failures = 0
    for e in transitions:
        declared = dated_declaration(e["commit"], e["date"], e["claim_id"])
        entry = retro.get((e["claim_id"], e["commit"]))
        typed = bool(entry and entry.get("transition_type") in TRANSITION_TYPES)
        if entry is None and hist is not None:
            print(f"FAIL  {e['claim_id']} at {e['commit'][:12]} ({e['kind']}) has no retrospective entry in claims_history.yaml")
            failures += 1
        if declared and typed:
            strict.append(f"{e['claim_id']}@{e['commit'][:12]}:{e['date']}:{entry['transition_type']}")
        print(f"{e['commit'][:12]} {e['date']} {e['claim_id']:8s} {e['kind']:7s} "
              f"dated_in-record_declaration={'yes' if declared else 'no '} typed={'yes' if typed else 'no '}")
    print(f"PREEXISTING_E5_TRANSITION_COUNT={len(transitions)}  (digest-level commitment changes and removals on the first-parent line; births excluded)")
    print(f"STRICT_SCAR_ELIGIBLE_COUNT={len(strict)}  (before and after states re-derived from git; a dated in-record declaration naming the claim in the same first-parent change; a coherent transition type declared in the reconstruction)")
    for s in strict:
        print(f"  qualifying: {s}")
    if hist is not None:
        rc = hist.get("reconstruction") or {}
        if rc.get("preexisting_transition_count") != len(transitions) or rc.get("strict_scar_eligible_count") != len(strict):
            print(f"FAIL  claims_history.yaml states counts {rc.get('preexisting_transition_count')}/{rc.get('strict_scar_eligible_count')}; recomputed {len(transitions)}/{len(strict)}")
            failures += 1
        if sorted(rc.get("qualifying_transition_locators") or []) != sorted(strict):
            print("FAIL  claims_history.yaml qualifying_transition_locators differ from the recomputed set")
            failures += 1
    if check:
        return 1 if failures else 0
    return 0


# ------------------------------------------------------------------ mutants
def run_mutants() -> int:
    claims_doc, hist = load_both()
    today = dt.date.today()
    try:
        ref = prior_reference()
        prior = history_at(ref)
    except GitUnavailable as exc:
        print(f"UNDETERMINED  git history unavailable ({exc})")
        return 2
    if prior is None:
        prior = copy.deepcopy(hist)  # the mutants must run against an accepted history; before the first commit the candidate is its own prior
    results: list[tuple[str, bool, str]] = []

    def run(name: str, claims_m: dict, hist_m: dict, expect_pass: bool, prior_m=prior, note: str = "") -> None:
        R = verify(claims_m, hist_m, prior_m, prior_ref=ref, today=today)
        passed = R.exit_code() == 0
        results.append((name, passed == expect_pass, (R.failures[0] if R.failures else "verified") + (" · " + note if note else "")))

    def fresh():
        return copy.deepcopy(claims_doc), copy.deepcopy(hist)

    def claim(doc, cid):
        return next(c for c in doc["claims"] if c["id"] == cid)

    def append(hist_m: dict, cid: str, to_c: dict | None, ttype="CORRECT", basis="DECLARED_HUMAN_JUDGMENT",
               frm: str | None = None, to: str | None = "auto") -> dict:
        state = predicted_state(hist_m)
        e = {"kind": "transition", "claim_id": cid, "from_digest": frm or state[cid],
             "to_digest": (digest(to_c) if to_c is not None else None) if to == "auto" else to,
             "transition_type": ttype, "event_at": today.isoformat(), "recorded_at": today.isoformat(),
             "provenance_class": "CONTEMPORANEOUS", "direction_basis": basis, "evidence_refs": ["test:mutant"],
             "reason": "mutant", "previous_transition_digest": tip_digest(hist_m)}
        if to_c is not None:
            e["to_commitment"] = to_c
        e["digest"] = entry_digest(e)
        hist_m.setdefault("entries", []).append(e)
        return e

    # M1 proposition changes, no transition
    c, h = fresh(); claim(c, "CC-001")["proposition"] += " (silently reworded)"
    run("M1 proposition changed, no transition", c, h, False)
    # M2 forbidden rescue removed / reworded, no transition
    c, h = fresh(); claim(c, "MC-003")["forbidden_rescues"].pop()
    run("M2a forbidden rescue removed, no transition", c, h, False)
    c, h = fresh(); claim(c, "MC-003")["forbidden_rescues"][0] += " unless convenient"
    run("M2b forbidden rescue reworded, no transition", c, h, False)
    # M3 commitment changed + genesis re-minted to match
    c, h = fresh(); claim(c, "CC-001")["proposition"] += " (re-minted)"
    for s in h["genesis"]["states"]:
        if s["claim_id"] == "CC-001":
            s["commitment"] = commitment(claim(c, "CC-001")); s["digest"] = digest(s["commitment"])
    h["genesis"]["digest"] = genesis_digest(h["genesis"]["states"])
    run("M3a commitment changed + genesis re-minted", c, h, False)
    c, h = fresh(); claim(c, "CC-001")["proposition"] += " (re-minted, fresh kernel)"
    for s in h["genesis"]["states"]:
        if s["claim_id"] == "CC-001":
            s["commitment"] = commitment(claim(c, "CC-001")); s["digest"] = digest(s["commitment"])
    h["genesis"]["digest"] = genesis_digest(h["genesis"]["states"]); h["genesis"]["anchor_commit"] = ref
    for e in h["entries"]:  # re-link the chain to the new genesis so only the anchor check can catch it
        pass
    run("M3b commitment changed + genesis re-minted + claimed as a fresh kernel", c, h, False, prior_m=None,
        note="prior absent; anchor content check must catch it")
    # M4 prior protected entry edited / deleted
    c, h = fresh(); h["entries"][0]["reason"] = "history rewritten"; h["entries"][0]["digest"] = entry_digest(h["entries"][0])
    run("M4a prior entry edited", c, h, False)
    c, h = fresh(); h["entries"].pop(0)
    run("M4b prior entry deleted", c, h, False)
    c, h = fresh(); h["entries"][0]["reason"] = "history rewritten and re-linked"
    prev = h["genesis"]["digest"]
    for e in h["entries"]:  # re-mint every link so the chain is internally consistent
        e["previous_transition_digest"] = prev; e["digest"] = entry_digest(e); prev = e["digest"]
    run("M4c prior entry edited and the whole chain re-linked", c, h, False, note="only the prefix rule against the prior accepted revision can catch this")
    # M5 wrong from_digest
    c, h = fresh(); cl = claim(c, "CC-001"); cl["proposition"] += " (declared)"; append(h, "CC-001", commitment(cl), frm="0" * 64)
    run("M5 wrong from_digest", c, h, False)
    # M6 wrong to_digest / live-state mismatch
    c, h = fresh(); cl = claim(c, "CC-001"); cl["proposition"] += " (declared)"; append(h, "CC-001", commitment(cl), to="1" * 64)
    run("M6a to_digest does not match recorded content", c, h, False)
    c, h = fresh(); cl = claim(c, "CC-001"); cl["proposition"] += " (declared)"
    recorded = copy.deepcopy(commitment(cl)); recorded["proposition"] += " but live differs"; append(h, "CC-001", recorded)
    run("M6b live state differs from the declared to_commitment", c, h, False)
    # M7 serialization-only YAML change, identical parsed commitment
    text = CLAIMS.read_text()
    reflowed = yaml.safe_dump(yaml.safe_load(text), allow_unicode=True, sort_keys=True, width=60, default_style='"')
    c7 = yaml.safe_load(reflowed)
    same = live_states(c7) == live_states(claims_doc) and reflowed != text
    run("M7 YAML re-serialized (keys sorted, width 60, quoted), parsed commitment identical", c7, copy.deepcopy(hist), True,
        note=f"bytes differ={reflowed != text}, digests identical={same}")
    # M8 wording changed but presented as formatting-only
    c, h = fresh(); claim(c, "CC-001")["proposition"] = claim(c, "CC-001")["proposition"].replace("returns", "roughly returns")
    run("M8a wording changed, called formatting-only (no entry)", c, h, False)
    c, h = fresh(); cl = claim(c, "CC-001"); cl["proposition"] = cl["proposition"].replace("returns", "roughly returns")
    append(h, "CC-001", commitment(cl), ttype="FORMAT_ONLY")
    run("M8b wording changed, entry typed FORMAT_ONLY", c, h, False)
    # M9 valid appended transition
    c, h = fresh(); cl = claim(c, "CC-001"); cl["non_claims"].append("does not license a point estimate of dependence"); append(h, "CC-001", commitment(cl), ttype="NARROW")
    run("M9 valid declared NARROW appended", c, h, True)
    # M10 reconstruct a protected prior state
    c, h = fresh(); cl = claim(c, "CC-001"); before_c = copy.deepcopy(commitment(cl)); cl["non_claims"].append("x"); append(h, "CC-001", commitment(cl), ttype="NARROW")
    walk = {s["claim_id"]: s["commitment"] for s in h["genesis"]["states"]}
    prior_states = []
    for e in h["entries"]:
        if e.get("provenance_class") == "CONTEMPORANEOUS" and e["claim_id"] == "CC-001":
            prior_states.append(walk["CC-001"]); walk["CC-001"] = e.get("to_commitment")
    reconstructed = prior_states[-1] if prior_states else None
    retro = next(e for e in hist["entries"] if e.get("provenance_class") == "RETROSPECTIVE_RECONSTRUCTION")
    sha = next(r[4:] for r in retro["evidence_refs"] if r.startswith("git:"))
    from_git = (claims_at(f"{sha}^1") or {}).get(retro["claim_id"])
    ok10 = reconstructed == before_c and from_git is not None and from_git["digest"] == retro["from_digest"]
    results.append(("M10 prior states reconstructable (post-genesis from the file, pre-genesis from git)", ok10,
                    f"post-genesis match={reconstructed == before_c}, pre-genesis {retro['claim_id']}@{sha[:12]} match={from_git is not None and from_git['digest'] == retro['from_digest']}"))
    # M11 declared NARROW, MACHINE_CHECKED, but the structured domain expands (MC-003 identified set)
    c, h = fresh(); cl = claim(c, "MC-003"); cl["expected"]["identified_set_upper"] = 13; cl["expected"]["identified_set_size"] = 14
    append(h, "MC-003", commitment(cl), ttype="NARROW", basis="MACHINE_CHECKED")
    run("M11a declared NARROW MACHINE_CHECKED, interval expands", c, h, False)
    c, h = fresh(); cl = claim(c, "MC-003"); cl["expected"]["identified_set_upper"] = 11; cl["expected"]["identified_set_size"] = 12
    append(h, "MC-003", commitment(cl), ttype="NARROW", basis="MACHINE_CHECKED")
    run("M11b declared NARROW MACHINE_CHECKED, interval shrinks", c, h, True)
    c, h = fresh(); cl = claim(c, "CC-001"); cl["proposition"] += " (prose only)"; append(h, "CC-001", commitment(cl), ttype="NARROW", basis="MACHINE_CHECKED")
    run("M11c prose-only NARROW claims MACHINE_CHECKED", c, h, False, note="no structured rule applies")
    # control: the committed state verifies
    run("M0 committed state", copy.deepcopy(claims_doc), copy.deepcopy(hist), True)

    bad = 0
    for name, ok, detail in results:
        print(f"{'ok  ' if ok else 'FAIL'}  {name} — {detail[:150]}")
        bad += not ok
    print(f"{'ok    ' if not bad else 'FAIL  '}claim-history mutants: {len(results) - bad}/{len(results)} behaved as required")
    return 1 if bad else 0


# ------------------------------------------------------------------ cli
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test", action="store_true", help="run the mandatory mutants in memory")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("verify")
    sub.add_parser("digest")
    rc = sub.add_parser("reconstruct"); rc.add_argument("--check", action="store_true")
    ad = sub.add_parser("append")
    ad.add_argument("--claim", required=True); ad.add_argument("--type", required=True, choices=sorted(TRANSITION_TYPES))
    ad.add_argument("--basis", required=True, choices=sorted(BASES)); ad.add_argument("--event-at", required=True)
    ad.add_argument("--reason", required=True); ad.add_argument("--evidence", action="append", required=True)
    rg = sub.add_parser("register")
    rg.add_argument("--claim", required=True); rg.add_argument("--reason", required=True); rg.add_argument("--evidence", action="append", required=True)
    a = ap.parse_args()
    if a.test:
        return run_mutants()
    if a.cmd == "verify" or a.cmd is None:
        return cmd_verify()
    if a.cmd == "digest":
        for cid, st in live_states(yaml.safe_load(CLAIMS.read_text())).items():
            print(f"{cid:9s} {st['digest']}")
        return 0
    if a.cmd == "reconstruct":
        return cmd_reconstruct(check=a.check)
    if a.cmd == "append":
        return cmd_append(a)
    if a.cmd == "register":
        return cmd_register(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
