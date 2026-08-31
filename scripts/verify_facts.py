#!/usr/bin/env python3
"""Gate every current factual surface against the census arithmetic.

The existing gates proved three things: the census file is internally
coherent, the generated HTML matches its generator, and the deployed bytes
match the checked revision. All three passed while the public flagship page
said the joint-evidence count was both 5 and 4.

Nothing was lying. The headline was derived from ``counts``; a later sentence
had been typed by hand. The gates compared artifacts to each other and never
asked whether the page agreed with itself. This script asks that:

    every present-tense statement of a census quantity, on every page,
    states the value that quantity currently has.

Run with no arguments to audit the working tree. ``--test`` runs the
adversarial fixtures, which matter more than the audit: they render the site
under synthetic censuses and assert that every current surface moves when the
underlying count moves, and that the exact defect this script was written for
is caught rather than merely absent.
"""

from __future__ import annotations

import copy
import datetime
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import facts  # noqa: E402
import generate_missing_column as gen  # noqa: E402
import verify_census  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# Pages whose owner-review date must not predate the newest correction they
# describe. A page cannot coherently say both "corrected on the 30th" and
# "last reviewed on the 27th": whoever reviewed it on the 27th cannot have
# reviewed a correction that did not yet exist.
REVIEW_RE = re.compile(r"Last owner review:\s*(\d{4}-\d{2}-\d{2})")
CORRECTED_RE = re.compile(r"[Cc]orrected\s+(?:on\s+)?(\d{4}-\d{2}-\d{2})")


def pages() -> list[Path]:
    return sorted(
        p for p in ROOT.rglob("*.html")
        if ".git" not in p.parts and "docs" not in p.parts
        and "scripts" not in p.parts and "fixtures" not in p.parts
        and ".venv" not in p.parts)


def check_freshness(html_text: str, where: str) -> list[str]:
    """last_owner_review >= the newest current correction the page states."""
    review = REVIEW_RE.search(facts.visible_text(html_text))
    if not review:
        return []
    reviewed = datetime.date.fromisoformat(review.group(1))
    failures = []
    text = facts.visible_text(facts.strip_historical(html_text))
    for match in CORRECTED_RE.finditer(text):
        corrected = datetime.date.fromisoformat(match.group(1))
        if corrected > reviewed:
            failures.append(
                f"{where}: states a correction dated {corrected} but claims a "
                f"last owner review of {reviewed} — a review cannot predate "
                f"the correction it is supposed to cover")
    return failures


# ----------------------------------------------------------- replay manifest
REPLAY_PAGE = "missing-column/index.html"
REPLAY_CLONE = "git clone https://github.com/Cubits11/cubits11.github.io.git"
REPLAY_VENV = ("python3 -m venv .venv", ". .venv/bin/activate")
REPLAY_INSTALL = "python -m pip install -r requirements.txt"
REPLAY_ADVERTISED = (
    "scripts/verify_census.py --counts",
    "scripts/generate_missing_column.py --check",
    "scripts/verify_figures.py",
    "scripts/mjgd_reference.py --test",
)
REPLAY_FULL = "scripts/verify_clean_clone.py"


def replay_commands(html_text: str) -> list[str] | None:
    """The replay manifest's command lines, comments stripped — or None when
    the section or its command block is gone."""
    section = re.search(
        r'<section class="zone replay".*?<pre[^>]*>(?P<block>.*?)</pre>',
        html_text, re.S)
    if not section:
        return None
    lines = []
    for raw in html.unescape(section.group("block")).splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            lines.append(line)
    return lines


def check_replay_manifest(html_text: str, where: str) -> list[str]:
    """The public reproduction surface must run from an empty shell.

    This page shipped calling itself a clean-checkout replay while its first
    command assumed a repository, a working directory, an installed
    dependency, and an interpreter name it never established: a stranger in
    an empty directory got ``Errno 2``, not a census. Every clause below
    either failed then or guards one that did:

      * the block's first act is the clone, and the ``cd`` enters exactly
        the directory that clone creates;
      * dependency setup installs the declared requirements file inside an
        environment the block itself created (``python3 -m venv`` then
        activation) — bare ``pip install`` refuses on PEP 668 systems;
      * every advertised verification command appears after setup, in
        order, uses the interpreter the activation established, and points
        at a script that exists in this repository;
      * the venv the block creates is git-ignored — otherwise the block's
        own side effect dirties the worktree and vetoes the
        whole-repository replay the section advertises alongside it.
    """
    cmds = replay_commands(html_text)
    if cmds is None:
        return [f"{where}: replay manifest section or its command block is gone"]
    failures: list[str] = []

    def missing(what: str) -> None:
        failures.append(f"{where}: replay manifest lost {what} — a stranger "
                        f"in an empty shell cannot reproduce the census")

    if not cmds or cmds[0] != REPLAY_CLONE:
        missing(f"its clone step ({REPLAY_CLONE!r} must come first)")
    target = REPLAY_CLONE.rsplit("/", 1)[-1].removesuffix(".git")
    if len(cmds) < 2 or cmds[1] != f"cd {target}":
        missing(f"its working-directory step ('cd {target}' must follow the clone)")

    def index(cmd: str) -> int:
        return cmds.index(cmd) if cmd in cmds else -1

    venv, activate = (index(c) for c in REPLAY_VENV)
    install = index(REPLAY_INSTALL)
    if venv < 0 or activate < 0 or not venv < activate:
        missing("its interpreter setup (venv creation, then activation)")
    if install < 0 or (activate >= 0 and install < activate):
        missing(f"its dependency step ({REPLAY_INSTALL!r} after activation)")
    if not (ROOT / "requirements.txt").exists():
        failures.append(f"{where}: replay manifest installs requirements.txt, "
                        f"which does not exist")

    previous = install
    for advertised in REPLAY_ADVERTISED:
        at = index(f"python {advertised}")
        if at < 0 or at < previous:
            missing(f"the advertised check 'python {advertised}' "
                    f"(present, after setup, in order)")
            continue
        previous = at
        script = advertised.split()[0]
        if not (ROOT / script).exists():
            failures.append(f"{where}: replay manifest advertises {script}, "
                            f"which does not exist")

    gitignore = ROOT / ".gitignore"
    if ".venv/" not in (gitignore.read_text() if gitignore.exists() else ""):
        failures.append(f"{where}: the replay block creates .venv inside the "
                        f"clone, but .gitignore does not ignore it — the "
                        f"block's own side effect would dirty the worktree "
                        f"and veto the whole-repository replay")

    section = re.search(r'<section class="zone replay".*?</section>',
                        html_text, re.S)
    if section and REPLAY_FULL not in section.group(0):
        missing(f"the whole-repository replay pointer ({REPLAY_FULL})")
    if not (ROOT / REPLAY_FULL).exists():
        failures.append(f"{where}: the whole-repository replay points at "
                        f"{REPLAY_FULL}, which does not exist")
    return failures


def audit_tree() -> list[str]:
    registry = facts.registry()
    accepted = facts.accepted_triples()
    failures: list[str] = []
    checked = 0
    for page in pages():
        rel = page.relative_to(ROOT).as_posix()
        html_text = page.read_text(encoding="utf-8")
        failures += facts.audit_html(html_text, registry, rel,
                                     facts.REQUIRED_BINDINGS.get(rel), accepted)
        failures += check_freshness(html_text, rel)
        if rel == REPLAY_PAGE:
            failures += check_replay_manifest(html_text, rel)
        checked += 1
    if not failures:
        values = " ".join(f"{k.split('.', 1)[1]}={v}"
                          for k, v in sorted(registry.items()))
        print(f"ok    {checked} pages agree with the census ({values})")
    return failures


# ------------------------------------------------------------------ fixtures
def synthetic(data: dict, *, present: int | None = None,
              examined: int | None = None) -> dict:
    """A census with counts moved deliberately, to see what fails to follow.

    Rows are reclassified rather than invented, so ``compute_counts`` does the
    same arithmetic it always does. The fixture changes the world; it never
    changes the way the world is counted.
    """
    out = copy.deepcopy(data)
    rows = [r for r in out["benchmarks"] if r.get("status") == "examined"]
    if present is not None:
        current = [r for r in rows if r["classification"] == "PRESENT"]
        absent = [r for r in rows if r["classification"] == "ABSENT"]
        for row in absent[:max(0, present - len(current))]:
            row["classification"] = "PRESENT"
            row["joint_scope"] = "printed_full_stack"
            row["joint_statistic_evidence"] = "Synthetic fixture: printed union row."
    if examined is not None:
        for row in rows[examined:]:
            row["status"] = "under_review"
            row["notes"] = "Synthetic fixture: withheld from the examined set."
    return out


def current_k_surfaces(html_text: str) -> list[str]:
    """Every rendered surface that asserts K right now."""
    found = []
    for match in facts.FACT_SPAN.finditer(html_text):
        if match.group("fid") == "MC-001.K" and \
                'data-fact-state="current"' in match.group("attrs"):
            found.append(match.group("value").strip())
    text = facts.visible_text(facts.strip_historical(html_text))
    for fid, _label, pattern in facts.COMPILED:
        if fid != "MC-001.K":
            continue
        found += [m.group(1) for m in pattern.finditer(text)]
    return found


def run_tests() -> list[str]:
    failures: list[str] = []
    data = verify_census.load()

    def check(name: str, condition: bool, detail: str = "") -> None:
        if condition:
            print(f"ok    fixture: {name}")
        else:
            failures.append(f"fixture {name} failed{': ' + detail if detail else ''}")

    # 1. The defect itself. This is the regression test that matters: the
    #    exact sentence that shipped must be caught, not merely absent.
    registry = facts.registry()
    shipped = ("<p>It does not claim the unmeasured joint statistics would "
               "reveal dependence. Its 4 is an inclusive discovery count of "
               "noninterchangeable artifacts.</p>")
    caught = facts.audit_html(shipped, registry, "fixture")
    check("the shipped 'Its 4' sentence is caught", bool(caught),
          "the sweep accepted the exact defect it was written for")

    # 2. Every awkward surface form of the same assertion. A scanner that
    #    catches one phrasing and misses its pronoun variant is why this
    #    defect reached production in the first place.
    for prose in ("The 4 is an inclusive discovery count of artifacts.",
                  "Its 4 is a heterogeneous discovery count.",
                  "Four provide heterogeneous joint-evidence artifacts.",
                  "4 provide one of the census's declared joint-evidence artifacts.",
                  "Nineteen artifacts examined against primary sources."):
        hit = facts.audit_html(f"<p>{prose}</p>", registry, "fixture")
        check(f"stale phrasing caught: {prose[:44]!r}", bool(hit))

    # 3. A page that states the current values in those same forms passes.
    #    A checker that fires on correct prose is not usable.
    k, n = registry["MC-001.K"], registry["MC-001.N"]
    clean = (f"<p>Its {k} is an inclusive discovery count. {n} artifacts "
             f"examined against primary sources.</p>")
    check("current values in the same phrasings pass",
          not facts.audit_html(clean, registry, "fixture"),
          "the sweep rejected a correct sentence")

    # 4. Move K and require every current K surface to follow. This is the
    #    property the site actually needs: not that today's number is right,
    #    but that no surface can be left behind when it changes.
    baseline = gen.render_landing(data)
    baseline_k = current_k_surfaces(baseline)
    check("the live page states K on at least two surfaces",
          len(baseline_k) >= 2, f"found {len(baseline_k)}")
    for target in (7, 9):
        moved = synthetic(data, present=target)
        moved_counts = verify_census.compute_counts(moved)
        if moved_counts["K"] != target:
            failures.append(f"fixture setup: synthetic K is {moved_counts['K']}, "
                            f"wanted {target}")
            continue
        html_text = gen.render_landing(moved)
        surfaces = current_k_surfaces(html_text)
        stale = [v for v in surfaces if facts.as_int(v) != target]
        check(f"every current K surface follows K={target}", not stale,
              f"{len(stale)} surface(s) still state {sorted(set(stale))}")
        check(f"K={target} page passes its own audit",
              not facts.audit_html(html_text, facts.registry(moved_counts),
                                   "fixture", accepted=facts.accepted_triples(moved)))
        # N and M must not have moved: a fixture that changes everything
        # proves nothing about which surface tracks which quantity.
        check(f"K={target} leaves N unchanged",
              moved_counts["N"] == verify_census.compute_counts(data)["N"])

    # 5. Move N while K stays put, to prove the surfaces are bound to distinct
    #    identities rather than to "whatever number appears nearby".
    fewer = synthetic(data, examined=17)
    fewer_counts = verify_census.compute_counts(fewer)
    html_text = gen.render_landing(fewer)
    check("N moves independently and its page still agrees with itself",
          not facts.audit_html(html_text, facts.registry(fewer_counts),
                               "fixture", accepted=facts.accepted_triples(fewer)),
          f"N={fewer_counts['N']} K={fewer_counts['K']}")

    # 6. Marked-fact discipline: an unknown id, a wrong current value, and an
    #    undated historical value each fail.
    check("an unknown fact id fails",
          bool(facts.audit_html(
              '<span data-fact="MC-001.Q" data-fact-state="current">3</span>',
              registry, "fixture")))
    check("a wrong current value fails",
          bool(facts.audit_html(
              f'<span data-fact="MC-001.K" data-fact-state="current">{k + 1}</span>',
              registry, "fixture")))
    check("an undated historical value fails",
          bool(facts.audit_html(
              '<span data-fact="MC-001.K" data-fact-state="historical">4</span>',
              registry, "fixture")))
    check("a dated historical value passes",
          not facts.audit_html(
              '<span data-fact="MC-001.K" data-fact-state="historical" '
              'data-as-of="2026-08-27">4</span>', registry, "fixture"))
    check("an undated historical region fails",
          bool(facts.audit_html(
              '<ul data-fact-state="historical"><li>Its 4 was the count.</li></ul>',
              registry, "fixture")))

    # 7. A stale envelope with no date is caught; the current one needs none.
    check("an undated superseded N/M/K envelope fails",
          bool(facts.audit_html("<p>The 19/13/4 envelope.</p>", registry, "fixture")))
    check("the current envelope needs no date",
          not facts.audit_html(
              f"<p>N/M/K = {registry['MC-001.N']}/{registry['MC-001.M']}/"
              f"{registry['MC-001.K']}.</p>", registry, "fixture"))

    # 8. Coverage is asserted, not assumed: a page that simply drops its
    #    bound sentence must fail rather than pass by silence.
    check("a page that stops stating its facts fails",
          bool(facts.audit_html("<p>Nothing numeric here.</p>", registry,
                                "fixture", required={"MC-001.K"})))

    # 9. The freshness relation.
    check("a review predating a correction fails",
          bool(check_freshness(
              "<p>Corrected 2026-08-30.</p><p>Last owner review: 2026-08-27</p>",
              "fixture")))
    check("a review on or after the correction passes",
          not check_freshness(
              "<p>Corrected 2026-08-30.</p><p>Last owner review: 2026-08-30</p>",
              "fixture"))

    # 10. The replay manifest is self-contained and each load-bearing line is
    #     load-bearing: the rendered block passes, and losing the clone, the
    #     cd, the interpreter setup, the dependency install, or any advertised
    #     check makes the gate fail rather than pass by silence. The mutations
    #     are exactly the defect that shipped: a "clean checkout" replay whose
    #     first command assumed a checkout.
    rendered = gen.render_landing(data)
    check("the generator's replay manifest is self-contained",
          not check_replay_manifest(rendered, "fixture"),
          "; ".join(check_replay_manifest(rendered, "fixture")))
    mutations = {
        "clone line removed": (REPLAY_CLONE, ""),
        "cd line removed": ("cd cubits11.github.io", ""),
        "venv creation removed": (REPLAY_VENV[0], ""),
        "venv activation removed": (REPLAY_VENV[1], ""),
        "dependency install removed": (REPLAY_INSTALL, ""),
        "an advertised check removed": ("python scripts/verify_figures.py", ""),
        "an advertised check reordered before setup": (
            REPLAY_CLONE,
            f"python {REPLAY_ADVERTISED[0]}\n{REPLAY_CLONE}"),
        "a check retargeted at a ghost script": (
            "scripts/verify_figures.py", "scripts/verify_figments.py"),
        "whole-repository pointer removed": (REPLAY_FULL, "scripts/"),
    }
    for name, (old, new) in mutations.items():
        mutated = rendered.replace(old, new)
        if mutated == rendered:
            failures.append(f"fixture setup: replay mutation {name!r} "
                            f"matched nothing")
            continue
        check(f"replay mutation caught: {name}",
              bool(check_replay_manifest(mutated, "fixture")))

    # 11. The evidence-mode counts must reconcile with K by inclusion-exclusion.
    #     If they ever stop doing so, the prose describing the overlap is
    #     describing something other than the census.
    modes = verify_census.compute_counts(data)["K_evidence_modes"]
    check("evidence modes reconcile with K",
          modes["prints_composition_result"] + modes["releases_computable_items"]
          - modes["does_both"] == registry["MC-001.K"],
          f"{modes} against K={registry['MC-001.K']}")
    return failures


def main() -> int:
    failures = run_tests() if "--test" in sys.argv else audit_tree()
    if failures:
        for failure in failures:
            print(f"FAIL  {failure}")
        print(f"{len(failures)} check(s) failed.")
        return 1
    print("Every current factual surface agrees with the census arithmetic."
          if "--test" not in sys.argv else
          "Fact binding holds under adversarial fixtures.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
