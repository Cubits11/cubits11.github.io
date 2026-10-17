"""The facts a render read, bound as one digest.

A render receipt binds the facts its film read at render time, not the whole
films/data/facts.json file. The digest is sha256 over the canonical JSON of
{fact_id: value} for exactly the ids in the receipt's facts_used: keys sorted,
separators (",", ":"), non-ASCII escaped. A fact the film never read cannot
make its render stale; a fact it read cannot change without making it stale.

facts_used is what the runtime's fact() accessor logged during the render. The
digest is complete only if that log is: scripts/films/mutation_completeness.py
is the test of that, film by film and fact by fact.
"""

from __future__ import annotations

import hashlib
import json

FILE = "films/data/facts.json"
RULE = "sha256 of canonical JSON {fact_id: value} over facts_used (sorted keys, separators ',' ':', ASCII)"


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def digest(facts: dict, facts_used: list[str]) -> str:
    """Digest of the values a render read. A fact missing from facts raises KeyError."""
    missing = sorted(f for f in facts_used if f not in facts)
    if missing:
        raise KeyError(f"no longer in {FILE}: {missing}")
    return hashlib.sha256(canonical({f: facts[f]["value"] for f in facts_used})).hexdigest()


def binding(facts: dict, facts_used: list[str]) -> dict:
    """The receipt field render_film.py writes."""
    return {"file": FILE, "over": "facts_used", "rule": RULE, "sha256": digest(facts, facts_used)}


def stale(receipt: dict, facts: dict) -> str | None:
    """None when the receipt's facts binding matches the current facts; otherwise why not."""
    bound = (receipt.get("facts_subset") or {}).get("sha256")
    if not isinstance(receipt.get("facts_used"), list):
        return "receipt records no facts_used list"
    if not bound:
        return "receipt carries no facts_subset digest (rendered before the subset rule)"
    try:
        live = digest(facts, receipt["facts_used"])
    except KeyError as exc:
        return f"a fact it read is gone: {exc.args[0]}"
    if live != bound:
        return f"a fact it read changed since the receipt (one of {len(receipt['facts_used'])} in facts_used)"
    return None
