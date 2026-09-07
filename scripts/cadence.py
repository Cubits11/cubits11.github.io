#!/usr/bin/env python3
"""The cadence instrument: this repository measured against itself, one row a day.

    python3 scripts/cadence.py record    # append today's row (once per UTC day)
    python3 scripts/cadence.py report    # the window's deltas, today's slot, the standing blocker
    python3 scripts/cadence.py check     # append-only and chain integrity (runs in the manifest)
    python3 scripts/cadence.py backfill  # genesis only: reconstruct one row per historical day
    python3 scripts/cadence.py --test    # planted mutations the check must catch

The evidence ledger answers "has anything been measured?" for one instant. It is
deliberately not a gate, because a number that can fail CI becomes a number
people manage. This records the same counts on a hash chain, so the second
question becomes answerable: is the answer moving, and which class of number
moved.

Two classes, declared below. EVIDENCE moves when an instrument runs against a
system or a human clears a blocker; nothing written here can move it. SCAFFOLD
moves when someone writes a file. A window where SCAFFOLD rose and EVIDENCE did
not is the failure mode .claude/skills/evidence-ledger/SKILL.md names, and this
is where it appears as a number rather than as a commit log.

Rows carry a `basis`. `live` was recorded on the day it names. `reconstructed`
was measured later by this instrument against that day's committed tree, which
is a weaker object: it is the true state of the repository at that commit, read
by an instrument that did not exist yet. Reconstruction runs once, at genesis;
after that the series only grows forward.

What CI enforces is the chain, never the counts. `check` fails if a recorded row
is edited, reordered, dropped or truncated, and passes on any values whatsoever.
The numbers are only allowed to be true; they are never allowed to be a target.
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

SERIES = ROOT / "metrics" / "repo_state.jsonl"
LEDGER_REL = pathlib.Path(".claude/skills/evidence-ledger/ledger.py")
GENESIS = "0" * 64

# The row, in order. `check` requires this exact tuple: a field added or dropped
# without editing this line is a schema break, not a silent widening.
FIELDS = (
    "date", "head", "basis",
    "claims_total", "own_measurement", "own_artifact", "third_party", "unsupported",
    "executed_output", "observation_rows",
    "blockers_open", "blockers_cleared", "oldest_blocker_days",
    "qualified_outcomes", "technical_interactions",
    "governing_documents", "checks", "verifiers", "generators",
    "prev",
)

# Direction of progress, declared once. +1 means larger is progress, -1 smaller.
EVIDENCE = {"own_measurement": 1, "observation_rows": 1, "qualified_outcomes": 1,
            "technical_interactions": 1, "blockers_open": -1, "blockers_cleared": 1}
SCAFFOLD = {"claims_total": 1, "governing_documents": 1, "checks": 1,
            "verifiers": 1, "generators": 1}
# Rises by one a day on its own while a blocker stays open. It is the price of
# the wait, so it is reported and counted as movement in neither class.
COST = ("oldest_blocker_days",)

# The week as slots rather than as a syllabus. `moves` names the series field the
# slot exists to move, which makes a slot that never moves its field answerable.
# Monday is index 0, matching date.weekday().
ROTATION = (
    ("evidence-ledger", "review windows and decay clocks: re-pin what expired, bump last_reviewed", "claims_total"),
    ("missing-column", "audit one primary-source public eval; classify joint-artifact preservation", "claims_total"),
    ("cc-framework", "Frechet-Hoeffding endpoint witnesses for a composed detector", "checks"),
    ("measurement", "run an instrument against a system I chose; the only slot that can move own_measurement", "observation_rows"),
    ("distribution", "qualified outcomes against the technical-interaction budget", "qualified_outcomes"),
    ("ghost-ark", "provenance harness: read-only from this host, so read and report, never write", None),
    (None, "no slot; the row is recorded anyway", None),
)


def git(*args: str, cwd: pathlib.Path | None = None) -> str:
    return subprocess.run(["git", *args], cwd=cwd or ROOT, capture_output=True, text=True).stdout.strip()


def run(command: list[str], cwd: pathlib.Path) -> None:
    """Fail loudly: a swallowed git error here silently truncates the history."""
    out = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    if out.returncode:
        raise SystemExit(f"FAIL  {' '.join(command)} in {cwd}: "
                         f"{(out.stderr or out.stdout).strip().splitlines()[-1:] or [out.returncode]}")


def digest(line: str) -> str:
    return hashlib.sha256(line.encode()).hexdigest()


def serialize(row: dict) -> str:
    return json.dumps({k: row[k] for k in FIELDS}, separators=(",", ":"))


def lines_of(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip()]


# ── measuring ────────────────────────────────────────────────────────────────
def ledger_json(tree: pathlib.Path) -> dict:
    """Today's ledger, run against `tree`. One instrument, many states."""
    target = tree / LEDGER_REL
    if tree != ROOT:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / LEDGER_REL, target)
    out = subprocess.run([sys.executable, str(target), "--json"], cwd=tree,
                         capture_output=True, text=True)
    if out.returncode:
        raise RuntimeError(out.stderr.strip().splitlines()[-1:] or ["the ledger did not run"])
    return json.loads(out.stdout)


def manifest_checks(tree: pathlib.Path) -> int:
    """Count CHECKS by parsing, not importing: a historical manifest need not import."""
    manifest = tree / "scripts/verification_manifest.py"
    if not manifest.exists():
        return 0  # before the manifest existed there was no deterministic surface to count
    source = manifest.read_text()
    for node in ast.walk(ast.parse(source)):
        target = getattr(node, "target", None) or (getattr(node, "targets", [None]) or [None])[0]
        if isinstance(target, ast.Name) and target.id == "CHECKS" and isinstance(node.value, ast.Tuple):
            return len(node.value.elts)
    return 0


def script_counts(tree: pathlib.Path) -> tuple[int, int]:
    """Borrowed from repo_graph so the two instruments cannot disagree on a kind."""
    import repo_graph
    previous, repo_graph.ROOT = repo_graph.ROOT, tree
    try:
        kinds = [node["kind"] for node in repo_graph.scan_scripts()[0]]
    finally:
        repo_graph.ROOT = previous
    return kinds.count("verifier"), kinds.count("generator")


def measure(tree: pathlib.Path, as_of: dt.date, basis: str, head: str) -> dict:
    data = ledger_json(tree)
    # Blocker age is computed against the row's own date, never against the day
    # the instrument happened to run, so a reconstructed row is not backdated.
    ages = [(as_of - dt.date.fromisoformat(hit["since"])).days
            for hit in data["blocking"]["hits"] if hit.get("since")]
    verifiers, generators = script_counts(tree)
    return {
        "date": as_of.isoformat(),
        "head": head[:12],
        "basis": basis,
        "claims_total": data["claims"]["total"],
        "own_measurement": data["claims"]["own_measurement"],
        "own_artifact": data["claims"]["by_origin"].get("own-artifact", 0),
        "third_party": data["claims"]["by_origin"].get("third-party-artifact", 0),
        "unsupported": data["claims"]["by_origin"].get("unsupported", 0),
        "executed_output": data["claims"]["executed_output"],
        "observation_rows": data["rows"]["observation_rows"],
        "blockers_open": data["blocking"]["open"],
        "blockers_cleared": data["blocking"]["cleared"],
        "oldest_blocker_days": max(ages) if ages else 0,
        # Before distribution/outcomes.yaml existed there was nothing recording a
        # qualified outcome, so its absence reads as zero rather than as unknown.
        "qualified_outcomes": data["outcomes"].get("qualified_total") or 0,
        "technical_interactions": data["outcomes"].get("technical_interactions") or 0,
        "governing_documents": sum(e["governing_documents"] for e in data["scaffolding"]["experiments"]),
        "checks": manifest_checks(tree),
        "verifiers": verifiers,
        "generators": generators,
        "prev": GENESIS,
    }


# ── integrity ────────────────────────────────────────────────────────────────
def verify_lines(lines: list[str], committed: str | None = None) -> list[str]:
    """Every way the series can be wrong, as a list of failures."""
    failures: list[str] = []
    previous_date: dt.date | None = None
    for i, line in enumerate(lines):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            failures.append(f"row {i}: not JSON ({exc})")
            continue
        if tuple(row) != FIELDS:
            failures.append(f"row {i}: fields are not the declared schema")
            continue
        if row["basis"] not in ("live", "reconstructed"):
            failures.append(f"row {i}: basis {row['basis']!r} is not live or reconstructed")
        try:
            date = dt.date.fromisoformat(row["date"])
        except (TypeError, ValueError):
            failures.append(f"row {i}: date {row['date']!r} is not a date")
            continue
        if previous_date is not None and date <= previous_date:
            failures.append(f"row {i}: {date} does not follow {previous_date}")
        previous_date = date
        expected = GENESIS if i == 0 else digest(lines[i - 1])
        if row["prev"] != expected:
            failures.append(f"row {i} ({row['date']}): prev {str(row['prev'])[:12]} breaks the chain, "
                            f"expected {expected[:12]}")
    if committed is not None:
        recorded = lines_of(committed)
        if lines[:len(recorded)] != recorded:
            failures.append(f"the {len(recorded)} committed rows are not a prefix of the working file: "
                            f"the series was rewritten, not appended")
    return failures


def committed_series() -> str | None:
    rel = SERIES.relative_to(ROOT).as_posix()
    out = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=ROOT, capture_output=True, text=True)
    return out.stdout if out.returncode == 0 else None


def check() -> int:
    if not SERIES.exists():
        print(f"FAIL  {SERIES.relative_to(ROOT)} is missing")
        return 1
    lines = lines_of(SERIES.read_text())
    if not lines:
        print(f"FAIL  {SERIES.relative_to(ROOT)} has no rows")
        return 1
    failures = verify_lines(lines, committed_series())
    for failure in failures:
        print(f"FAIL  {failure}")
    if failures:
        return 1
    first, last = json.loads(lines[0]), json.loads(lines[-1])
    live = sum(1 for line in lines if json.loads(line)["basis"] == "live")
    print(f"ok    cadence series append-only and chained: {len(lines)} rows "
          f"({live} live), {first['date']} to {last['date']}")
    return 0


# ── recording ────────────────────────────────────────────────────────────────
def append(rows: list[dict]) -> int:
    SERIES.parent.mkdir(parents=True, exist_ok=True)
    lines = lines_of(SERIES.read_text()) if SERIES.exists() else []
    written = 0
    with SERIES.open("a") as handle:
        for row in rows:
            row["prev"] = digest(lines[-1]) if lines else GENESIS
            line = serialize(row)
            handle.write(line + "\n")
            lines.append(line)
            written += 1
    return written


def record(date: str | None = None) -> int:
    as_of = dt.date.fromisoformat(date) if date else dt.datetime.now(dt.timezone.utc).date()
    lines = lines_of(SERIES.read_text()) if SERIES.exists() else []
    if lines:
        last = json.loads(lines[-1])
        if last["date"] == as_of.isoformat():
            print(f"ok    {as_of} already recorded; the series takes one row a day ({len(lines)} rows)")
            return 0
        if as_of.isoformat() < last["date"]:
            print(f"FAIL  {as_of} precedes the last row {last['date']}; the series only appends")
            return 1
    row = measure(ROOT, as_of, "live", git("rev-parse", "HEAD"))
    append([row])
    print(f"ok    recorded {row['date']} · row {len(lines) + 1} · "
          f"{row['observation_rows']} observation rows · "
          f"{row['own_measurement']} own-measurement claims · "
          f"{row['blockers_open']} open blockers")
    return 0


def indexed(tree: pathlib.Path) -> int:
    """Tracked files git can see in `tree`. Zero means the index is unusable."""
    return len(subprocess.run(["git", "ls-files"], cwd=tree, capture_output=True, text=True).stdout.split())


def add_worktree(tree: pathlib.Path) -> None:
    """`git worktree add` here occasionally lands a zero-length index. Retry once,
    then refuse: measuring an empty index reports zeros as if they were history."""
    for attempt in (1, 2):
        run(["git", "worktree", "add", "--detach", "--quiet", str(tree), "HEAD"], ROOT)
        if indexed(tree):
            return
        subprocess.run(["git", "worktree", "remove", "--force", str(tree)], cwd=ROOT, capture_output=True)
        subprocess.run(["git", "worktree", "prune"], cwd=ROOT, capture_output=True)
    raise SystemExit(f"FAIL  git worktree add wrote an empty index twice at {tree}")


def backfill() -> int:
    """Genesis only: one reconstructed row per historical day, from that day's last commit."""
    if SERIES.exists() and lines_of(SERIES.read_text()):
        print("FAIL  backfill is a genesis operation and the series already has rows; "
              "the series only appends forward")
        return 1
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    last_of_day: dict[str, str] = {}
    for line in git("log", "--format=%ad %H", "--date=short").splitlines():
        date, commit = line.split()
        if date < today:
            last_of_day.setdefault(date, commit)  # log is newest first, so the first seen is the last commit
    rows, skipped = [], []
    with tempfile.TemporaryDirectory() as temp:
        tree = pathlib.Path(temp) / "tree"
        add_worktree(tree)
        try:
            for date in sorted(last_of_day):
                commit = last_of_day[date]
                run(["git", "checkout", "--detach", "--force", "--quiet", commit], tree)
                if not indexed(tree):
                    raise SystemExit(f"FAIL  the worktree index is empty at {commit[:12]}; "
                                     f"a reconstructed row read from it would be zeros, not history")
                try:
                    rows.append(measure(tree, dt.date.fromisoformat(date), "reconstructed", commit))
                    print(f"      {date}  {commit[:12]}  rows {rows[-1]['observation_rows']:>5}  "
                          f"own {rows[-1]['own_measurement']}  open {rows[-1]['blockers_open']}")
                except (RuntimeError, OSError, ValueError, KeyError) as exc:
                    skipped.append(f"{date} {commit[:12]}: {exc}")
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(tree)],
                           cwd=ROOT, capture_output=True)
    if not rows:
        print("FAIL  no historical day could be measured")
        return 1
    append(rows)
    for note in skipped:
        print(f"      skipped {note}")
    print(f"ok    reconstructed {len(rows)} days, {rows[0]['date']} to {rows[-1]['date']}"
          + (f", {len(skipped)} skipped" if skipped else ""))
    return 0


# ── reporting ────────────────────────────────────────────────────────────────
def last_moved(rows: list[dict], field: str) -> int | None:
    """Days since `field` last changed, or None if it never has."""
    today = dt.date.fromisoformat(rows[-1]["date"])
    for older, newer in zip(reversed(rows[:-1]), reversed(rows[1:])):
        if older[field] != newer[field]:
            return (today - dt.date.fromisoformat(newer["date"])).days
    return None


def block(title: str, note: str, spec: dict, base: dict, now: dict,
          words: tuple[str, str]) -> list[str]:
    """`words` is (with the sign, against it). Scaffolding growing is not progress,
    so the two blocks are never labelled with the same pair."""
    out = [f"{title}  {note}"]
    for field, sign in spec.items():
        delta = now[field] - base[field]
        mark = "" if delta == 0 else f"  {words[0] if delta * sign > 0 else words[1]}"
        out.append(f"  {field:<24}{now[field]:>8}   {delta:+d}{mark}")
    return out


def report(days: int = 7) -> int:
    if not SERIES.exists() or not lines_of(SERIES.read_text()):
        print("no rows yet · python3 scripts/cadence.py record")
        return 1
    rows = [json.loads(line) for line in lines_of(SERIES.read_text())]
    now = rows[-1]
    today = dt.date.fromisoformat(now["date"])
    window = [r for r in rows if dt.date.fromisoformat(r["date"]) >= today - dt.timedelta(days=days)]
    base = window[0]
    span = (today - dt.date.fromisoformat(base["date"])).days

    out = [f"CADENCE · {now['date']} · {len(rows)} rows · window {span}d of {days}d requested", ""]
    out += block("EVIDENCE", "moves only when an instrument runs or a human acts",
                  EVIDENCE, base, now, ("progress", "regress"))
    out.append("")
    out += block("SCAFFOLD", "moves when someone writes a file",
                  SCAFFOLD, base, now, ("written", "removed"))
    out.append("")
    out.append("COST      the price of the wait, counted in neither class")
    for field in COST:
        out.append(f"  {field:<24}{now[field]:>8}   {now[field] - base[field]:+d}")
    out.append("")

    advanced = [f for f, s in EVIDENCE.items() if (now[f] - base[f]) * s > 0]
    written = [f for f in SCAFFOLD if now[f] != base[f]]
    if len(window) < 2:
        verdict = "FIRST ROW — no window yet; the series needs a second day before it can say anything"
    elif advanced:
        verdict = f"MOVED — evidence advanced on {', '.join(advanced)}"
    elif written:
        verdict = ("SCAFFOLD-ONLY — " + ", ".join(written) + " moved and no evidence field did. "
                   "This is the failure mode .claude/skills/evidence-ledger/SKILL.md names.")
    else:
        verdict = f"FLAT — nothing moved in {span}d"
    out += [f"VERDICT {verdict}", ""]

    component, task, moves = ROTATION[today.weekday()]
    out.append(f"SLOT    {today.strftime('%A')} · {component or 'none'}")
    out.append(f"        {task}")
    if moves:
        since = last_moved(rows, moves)
        out.append(f"        moves {moves} · last moved "
                   + (f"{since}d ago" if since is not None else "never in this series"))
    out.append("")

    hits = sorted(ledger_json(ROOT)["blocking"]["hits"], key=lambda h: h.get("since") or "9999")
    if hits:
        oldest = hits[0]
        age = (today - dt.date.fromisoformat(oldest["since"])).days if oldest.get("since") else 0
        out.append(f"STANDING BLOCKER  {age}d · {oldest['file']}:{oldest['line']} · {oldest['marker']}")
        out.append(f"        {oldest['text'].strip()[:100]}")
        out.append(f"        {now['blockers_open']} open in total; no amount of writing here clears one.")
    print("\n".join(out))
    return 0


# ── fixtures ─────────────────────────────────────────────────────────────────
def synthetic(n: int = 3) -> list[str]:
    lines: list[str] = []
    for i in range(n):
        row = {field: 0 for field in FIELDS}
        row["date"] = (dt.date(2026, 1, 1) + dt.timedelta(days=i)).isoformat()
        row["head"] = f"{i:012d}"
        row["basis"] = "live"
        row["prev"] = GENESIS if i == 0 else digest(lines[-1])
        lines.append(serialize(row))
    return lines


def selftest() -> int:
    clean = synthetic(3)

    def mutate(index: int, change) -> list[str]:
        rows = [json.loads(line) for line in clean]
        change(rows[index])
        out = list(clean)
        out[index] = json.dumps(rows[index], separators=(",", ":"))
        return out

    cases = [
        ("a clean chain passes", clean, None, False),
        ("an edited row breaks the chain",
         mutate(1, lambda r: r.__setitem__("observation_rows", 10 ** 6)), None, True),
        ("a dropped row breaks the chain", [clean[0], clean[2]], None, True),
        ("reordered rows break the chain", [clean[0], clean[2], clean[1]], None, True),
        ("an added field breaks the schema", mutate(2, lambda r: r.__setitem__("momentum", 1)), None, True),
        ("a removed field breaks the schema", mutate(2, lambda r: r.pop("technical_interactions")), None, True),
        ("an undeclared basis is rejected", mutate(2, lambda r: r.__setitem__("basis", "estimated")), None, True),
        ("a rewritten committed row is not a prefix", clean,
         "\n".join(mutate(1, lambda r: r.__setitem__("checks", 999))) + "\n", True),
        ("a truncated series is not a prefix", clean[:2], "\n".join(clean) + "\n", True),
        ("appending to committed rows is a prefix", clean, "\n".join(clean[:2]) + "\n", False),
    ]
    bad = 0
    for name, lines, committed, should_fail in cases:
        failures = verify_lines(lines, committed)
        if bool(failures) != should_fail:
            print(f"FAIL  {name}: expected {'a failure' if should_fail else 'none'}, got {failures or 'none'}")
            bad += 1
        else:
            print(f"ok    {name}")
    if bad:
        return 1
    print(f"ok    cadence fixtures: {len(cases)} planted states, every mutation caught")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", nargs="?", default="report",
                        choices=("record", "report", "check", "backfill"))
    parser.add_argument("--check", action="store_true", help="alias for the check mode")
    parser.add_argument("--test", action="store_true", help="run the planted-mutation fixtures")
    parser.add_argument("--days", type=int, default=7, help="report window in days (default 7)")
    parser.add_argument("--date", help="record under this UTC date (backfill and fixtures only)")
    args = parser.parse_args()
    if args.test:
        return selftest()
    if args.check or args.mode == "check":
        return check()
    if args.mode == "record":
        return record(args.date)
    if args.mode == "backfill":
        return backfill()
    return report(args.days)


if __name__ == "__main__":
    sys.exit(main())
