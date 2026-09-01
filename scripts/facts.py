#!/usr/bin/env python3
"""The current-fact registry: census arithmetic bound to semantic identities.

The census already had one arithmetic (``verify_census.compute_counts``) and a
drift check proving the generated HTML matches its generator. Those two gates
together still permitted a real defect: a generator whose headline was derived
from ``counts`` while a later sentence in the same page hand-typed a stale
``4``. Both files agreed with each other, the census checksum matched, and the
page contradicted itself in public.

The missing invariant was never "the numbers are somewhere in a file". It was:

    every present-tense sentence that asserts a census quantity states the
    value that quantity currently has.

That requires facts to have *identities*, not just values. This module gives
each census quantity a stable id, its current value derived from census.yaml,
and the English phrasings that assert it. Two mechanisms then use those ids:

  1. Marked facts — the generator emits every census numeral inside
     ``<span data-fact="MC-001.K" data-fact-state="current">5</span>``. A
     hand-typed numeral has no id, so it cannot pass.
  2. Phrase binding — a sweep over rendered text binds a recognized English
     assertion to the fact it asserts and compares the numeral it carries.
     This reaches prose the generator does not control: claim text quoted from
     claims.yaml, and hand-maintained pages such as the resume.

Neither mechanism is a hand-maintained second copy of the counts. There is one
source (census.yaml), one arithmetic (compute_counts), and this registry
derived from it. Adding a hand-edited fact store would restore exactly the
class of drift the registry exists to remove.

No fact-checking scanner is complete: it catches the phrasings it knows. That
is why ``REQUIRED_BINDINGS`` asserts that each fact-bearing page still states
its facts in a bound form — a checker that passes because it found nothing is
not evidence of anything.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_census  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# Spelled-out numerals count as assertions too. "Four artifacts print ..." is
# every bit as much a public claim as "4 artifacts print ...".
WORD_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20,
}
NUM = r"(\d+|" + "|".join(WORD_NUMBERS) + r")"


def as_int(token: str) -> int | None:
    token = token.strip().lower()
    if token.isdigit():
        return int(token)
    return WORD_NUMBERS.get(token)


def accepted_triples(data: dict | None = None) -> set[tuple[int, int, int]]:
    """Every three-number envelope the record may state bare, with no context.

    Two shapes qualify: the primary N/M/K and the M ladder. Sensitivity
    envelopes are deliberately NOT accepted bare: an alternative envelope may
    be numerically identical to a superseded one (19/13/4 is both the
    envelope this census rejected on 2026-08-30 and what the
    pre-freeze-visibility-evidenced sensitivity computes), so a bare triple
    cannot say which it means. A sensitivity envelope passes the triple
    backstop only inside a declared-alternative context — near a date or the
    word "sensitivity"/"counterfactual" — which is how the generated aside
    and the dated revision entries state it. Sensitivity drift is caught
    upstream by verify_census.check_interpretation_sensitivities, not here.
    """
    data = data or verify_census.load()
    counts = verify_census.compute_counts(data)
    strata = counts["M_strata"]
    return {
        (counts["N"], counts["M"], counts["K"]),
        (strata["shared_basis"], strata["threshold_not_contradicted"],
         strata["threshold_documented_full_exposure"]),
    }


def registry(counts: dict | None = None) -> dict[str, int]:
    """Every census quantity the public record states, keyed by identity.

    Derived, never declared. A new public quantity is added here only by
    deriving it from the census rows — which is what makes the scope-mode
    counts below computable rather than counted by hand in prose.
    """
    counts = counts or verify_census.compute_counts(verify_census.load())
    strata = counts["M_strata"]
    modes = counts["K_evidence_modes"]
    scopes = counts["present_by_scope"]
    return {
        "MC-001.N": counts["N"],
        "MC-001.M": counts["M"],
        "MC-001.M1": strata["shared_basis"],
        "MC-001.M2": strata["threshold_not_contradicted"],
        "MC-001.M3": strata["threshold_documented_full_exposure"],
        "MC-001.ABSENT": counts["by_classification"].get("ABSENT", 0),
        "MC-001.K": counts["K"],
        "MC-001.K.prints_composition_result": modes["prints_composition_result"],
        "MC-001.K.releases_computable_items": modes["releases_computable_items"],
        "MC-001.K.does_both": modes["does_both"],
        "MC-001.K.printed_full_stack": scopes.get("printed_full_stack", 0),
        "MC-001.K.printed_partial_stack": scopes.get("printed_partial_stack", 0),
        "MC-001.K.computable_via_item_release": scopes.get(
            "computable_via_item_release", 0),
    }


# Phrase → fact identity. Each pattern captures exactly the numeral that the
# surrounding English asserts, so the binding survives rewording of everything
# else in the sentence. The capture is positioned by the pattern rather than by
# a proximity window, because "the nearest number" is a guess and this file
# exists to stop guessing.
#
# The patterns deliberately cover the awkward forms: bare article ("The 5 is"),
# possessive ("Its 5 is"), restrictive ("Only 5"), and spelled-out ("Five
# provide"). A scanner that catches one surface form and misses its pronoun
# variant is how "Its 4" survived four public checks.
BINDINGS: list[tuple[str, str, str]] = [
    # (fact id, description used in failure output, regex)
    ("MC-001.N", "the census proposition's N",
     rf"among\s+{NUM}\s+public guardrail evaluations"),
    ("MC-001.N", "the examined-artifact count",
     rf"{NUM}\s+(?:public guardrail evaluations|artifacts|rows)\s+"
     r"(?:have now been\s+)?examined"),
    ("MC-001.N", "the examined-artifact count",
     rf"{NUM}\s+artifacts have now been examined"),
    ("MC-001.N", "the examined-artifact count",
     rf"examined\s+{NUM}\s+public guardrail evaluations"),
    ("MC-001.N", "the examined-artifact count",
     rf"{NUM}\s+evaluations examined"),
    ("MC-001.M1", "M ladder rung 1 (shared basis)",
     rf"{NUM}\s+(?:document|establish)\s+a shared item set and (?:a )?common event"),
    ("MC-001.M1", "M ladder rung 1 (shared basis)",
     rf"{NUM}\s+document shared items and a common event definition"),
    ("MC-001.M2", "M ladder rung 2 (no stated threshold mismatch)",
     rf"{NUM}\s+have no stated threshold mismatch"),
    ("MC-001.M3", "M ladder rung 3 (matched thresholds, full exposure)",
     rf"{NUM}\s+document matched"),
    ("MC-001.K", "the joint-evidence count K",
     rf"{NUM}\s+(?:provide|preserve|carry)\s+(?:one of\s+)?"
     r"(?:the census's|the census&#x27;s|a|the)?\s*declared joint-evidence"),
    ("MC-001.K", "the joint-evidence count K",
     rf"{NUM}\s+provide one of the census(?:'s|&#x27;s)? declared"),
    ("MC-001.K", "the joint-evidence count K",
     rf"{NUM}\s+(?:provide|preserve|carry)\s+heterogeneous\s+joint-evidence"),
    ("MC-001.K", "the joint-evidence count K",
     rf"{NUM}\s+(?:provide|preserve|carry)\s+an?\s+joint-evidence artifact"),
    ("MC-001.K", "the joint-evidence count K",
     rf"{NUM}\s+preserve a joint-evidence artifact"),
    ("MC-001.K", "the joint-evidence count K",
     rf"{NUM}\s+preserve joint evidence"),
    ("MC-001.K", "K described as a discovery count",
     rf"(?:the|its)\s+{NUM}\s+is\s+(?:an inclusive|a heterogeneous)"
     r"\s+discovery count"),
    ("MC-001.K", "K described as a discovery count",
     rf"{NUM}\s+is an inclusive discovery count"),
    ("MC-001.K.prints_composition_result", "artifacts printing a composition result",
     rf"{NUM}\s+(?:artifacts\s+)?print(?:s)?\s+(?:at least one\s+)?a?\s*"
     r"composition result"),
    ("MC-001.K.releases_computable_items", "artifacts releasing aligned per-item outcomes",
     rf"{NUM}\s+release aligned per-item outcomes"),
    ("MC-001.K.does_both", "artifacts carrying both kinds of joint evidence",
     rf"{NUM}\s+artifact does both"),
    ("MC-001.K.printed_full_stack", "the printed-full-stack scope split",
     rf"{NUM}\s+print(?:ing)? a full-stack"),
    ("MC-001.K.computable_via_item_release", "the item-release scope split",
     rf"{NUM}\s+releas(?:e|ing) per-item outcomes"),
]

COMPILED = [(fid, label, re.compile(pattern, re.I))
            for fid, label, pattern in BINDINGS]

# Pages that carry census facts must keep carrying them in a bound form.
# Without this, deleting the sentence would "fix" a drift failure.
REQUIRED_BINDINGS: dict[str, set[str]] = {
    "missing-column/index.html": {
        "MC-001.N", "MC-001.M1", "MC-001.M2", "MC-001.M3", "MC-001.K"},
    "ledger/index.html": {"MC-001.N", "MC-001.M1", "MC-001.K"},
    "observatory/index.html": {"MC-001.N", "MC-001.M1", "MC-001.K"},
    "resume/index.html": {"MC-001.N", "MC-001.M1", "MC-001.K"},
    "index.html": {"MC-001.N", "MC-001.K", "MC-001.M3", "MC-001.M1",
                   "MC-001.ABSENT"},
    "answers/why-guardrail-miss-rates-do-not-multiply/index.html": {
        "MC-001.N", "MC-001.K", "MC-001.M3"},
    "answers/how-to-evaluate-guardrails-you-plan-to-stack/index.html": {
        "MC-001.N", "MC-001.M1", "MC-001.M2", "MC-001.M3"},
}

TRIPLE = re.compile(r"(\d{1,3})\s*/\s*(\d{1,3})\s*/\s*(\d{1,3})")
DATE_NEAR = re.compile(r"\b(?:19|20)\d{2}(?:-\d{2}-\d{2})?\b")
DECLARED_ALTERNATIVE = re.compile(r"counterfactual|sensitivity", re.I)
FACT_SPAN = re.compile(
    r'<span\b(?P<attrs>[^>]*\bdata-fact="(?P<fid>[^"]+)"[^>]*)>(?P<value>[^<]*)</span>')
HISTORICAL_REGION = re.compile(
    r'<(?P<tag>\w+)\b[^>]*\bdata-fact-state="historical"[^>]*>', re.I)


def fact_span(fact_id: str, value, *, state: str = "current",
              as_of: str | None = None) -> str:
    """Emit one census numeral carrying the identity of what it asserts.

    A number rendered through this function can be checked; a number typed
    into a template string cannot. That asymmetry is the whole point.
    """
    if state == "historical" and not as_of:
        raise ValueError(
            f"{fact_id}: a historical value must carry the date it was current")
    stamp = f' data-as-of="{html.escape(as_of)}"' if as_of else ""
    return (f'<span data-fact="{html.escape(fact_id)}" '
            f'data-fact-state="{state}"{stamp}>{value}</span>')


def strip_historical(html_text: str) -> str:
    """Blank out regions explicitly declared historical.

    Marking is required rather than inferred: prose about a superseded count
    is legitimate, but only when the page says, in markup a machine can read,
    that it is no longer current.
    """
    out = html_text
    for match in list(HISTORICAL_REGION.finditer(out)):
        tag = match.group("tag")
        close = f"</{tag}>"
        end = out.find(close, match.end())
        if end == -1:
            continue
        out = out[:match.start()] + " " * (end + len(close) - match.start()) \
            + out[end + len(close):]
    return out


def visible_text(html_text: str) -> str:
    """Rendered text, with script/style dropped and entities left intact.

    Entities stay because the bound phrasings quoted from claims.yaml carry
    ``&#x27;`` where an apostrophe belongs, and a binding must match the page
    as served rather than an idealized decoding of it.
    """
    text = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", html_text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text)


def check_marked_facts(html_text: str, facts: dict[str, int],
                       where: str) -> list[str]:
    """Every ``data-fact`` span states a value its identity licenses."""
    failures = []
    seen_current = 0
    for match in FACT_SPAN.finditer(html_text):
        fid = match.group("fid")
        attrs = match.group("attrs")
        raw = match.group("value").strip()
        state = re.search(r'data-fact-state="([^"]*)"', attrs)
        state = state.group(1) if state else ""
        as_of = re.search(r'data-as-of="([^"]*)"', attrs)
        if fid not in facts:
            failures.append(f"{where}: unknown fact id {fid!r} — the registry "
                            f"derives from census.yaml and has no such quantity")
            continue
        value = as_int(raw)
        if value is None:
            failures.append(f"{where}: fact {fid} carries non-numeric {raw!r}")
            continue
        if state == "current":
            seen_current += 1
            if value != facts[fid]:
                failures.append(
                    f"{where}: current {fid} states {value}, census computes "
                    f"{facts[fid]}")
        elif state == "historical":
            if not as_of:
                failures.append(
                    f"{where}: historical {fid}={value} carries no data-as-of "
                    f"date — an undated superseded count reads as current")
        else:
            failures.append(
                f"{where}: fact {fid} has data-fact-state={state!r}; a census "
                f"numeral is either current or dated history")
    return failures


def check_bound_phrases(html_text: str, facts: dict[str, int],
                        where: str) -> tuple[list[str], set[str]]:
    """Bind present-tense census assertions to the quantity they assert.

    Runs on text with marked spans intact: a marked numeral is checked by
    identity above and by phrasing here, and the two must agree.
    """
    failures: list[str] = []
    bound: set[str] = set()
    text = visible_text(strip_historical(html_text))
    for fid, label, pattern in COMPILED:
        for match in pattern.finditer(text):
            value = as_int(match.group(1))
            if value is None:
                continue
            bound.add(fid)
            if value != facts[fid]:
                snippet = text[max(0, match.start() - 40):match.end() + 40]
                failures.append(
                    f"{where}: {label} states {value}, census computes "
                    f"{facts[fid]} — …{snippet.strip()}…")
    return failures, bound


def check_triples(html_text: str, facts: dict[str, int], where: str,
                  accepted: set[tuple[int, int, int]] | None = None) -> list[str]:
    """A superseded N/M/K envelope must say when it was current.

    The current envelope, the current M ladder, and each declared sensitivity
    need no marking — all three are recomputed from the census. Any other
    triple is a claim about a state of the record that no longer holds, and an
    undated one reads to a visitor exactly like the live result.

    This is a backstop, not the primary guarantee: it looks for a date in a
    generous window rather than parsing the document's block structure, so it
    is deliberately tuned to miss nothing rather than to catch everything. The
    marked spans and phrase bindings above are what actually bind the values.
    """
    failures = []
    accepted = accepted if accepted is not None else accepted_triples()
    current = (facts["MC-001.N"], facts["MC-001.M"], facts["MC-001.K"])
    text = visible_text(strip_historical(html_text))
    for match in TRIPLE.finditer(text):
        triple = tuple(int(g) for g in match.groups())
        if triple in accepted:
            continue
        window = text[max(0, match.start() - 400):match.end() + 400]
        if DATE_NEAR.search(window) or DECLARED_ALTERNATIVE.search(window):
            continue
        failures.append(
            f"{where}: N/M/K triple {triple[0]}/{triple[1]}/{triple[2]} is not "
            f"the current {current[0]}/{current[1]}/{current[2]} and carries "
            f"neither a date nor a declared-alternative label")
    return failures


def check_historical_regions(html_text: str, where: str) -> list[str]:
    """A region declared historical must say when it was current.

    Marking a section historical exempts its numerals from the current-value
    check. That exemption is only honest if the section dates itself, so an
    undated historical region fails rather than quietly silencing a count.
    """
    failures = []
    for match in HISTORICAL_REGION.finditer(html_text):
        tag = match.group("tag")
        close = f"</{tag}>"
        end = html_text.find(close, match.end())
        region = html_text[match.start():end if end != -1 else len(html_text)]
        if not DATE_NEAR.search(visible_text(region)) \
                and 'data-as-of="' not in match.group(0):
            failures.append(
                f"{where}: a region marked data-fact-state=\"historical\" "
                f"carries no date — undated history is indistinguishable from "
                f"a current claim")
    return failures


def audit_html(html_text: str, facts: dict[str, int], where: str,
               required: set[str] | None = None,
               accepted: set[tuple[int, int, int]] | None = None) -> list[str]:
    """Every fact check one page must pass, on rendered output."""
    failures = check_marked_facts(html_text, facts, where)
    phrase_failures, bound = check_bound_phrases(html_text, facts, where)
    failures += phrase_failures
    # A marked span is a stronger binding than a recognized phrasing, so it
    # satisfies coverage on its own. Coverage asks whether the page still
    # states the fact checkably, not which of the two mechanisms caught it.
    for match in FACT_SPAN.finditer(html_text):
        if 'data-fact-state="current"' in match.group("attrs"):
            bound.add(match.group("fid"))
    failures += check_triples(html_text, facts, where, accepted)
    failures += check_historical_regions(html_text, where)
    for fid in sorted((required or set()) - bound):
        failures.append(
            f"{where}: expected a bound statement of {fid} and found none — "
            f"either the page stopped stating it, or it now states it in a "
            f"phrasing no binding recognizes")
    return failures
