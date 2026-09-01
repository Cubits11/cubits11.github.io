#!/usr/bin/env python3
"""Generate /missing-column/ and /missing-column/disclosure/ from census.yaml.

The Missing Column is a campaign about reporting, so its own reporting is
generated: the census table, the headline counts, the criteria, and the
correction history all render from census.yaml through this script.
Hand-editing the pages breaks the build; hand-typing a count is impossible
because the only arithmetic lives in verify_census.compute_counts, which
this renderer imports.

Fail-closed rendering: while any starting row is under_review and no row
is examined, the page says exactly that and claims no number. The headline
proposition appears only when N > 0, filled from the census's own
template.

The two figures are drawn from named constants and re-derived by
scripts/verify_figures.py — the illustrative numbers cannot drift from the
geometry that draws them.

CI runs `generate_missing_column.py --check` and fails on drift.
"""

import hashlib
import json
import pathlib
import re
import sys

import generate_ledger as ledger
import identification
import outcomes
import reanalyze_msbench
import validate_mjgd
import facts as fact_registry
import verify_census

esc = ledger.esc
squash = ledger.squash
ROOT = pathlib.Path(__file__).resolve().parent.parent

SITE = "https://cubits11.github.io"

# ---------------------------------------------------------------- figures
# Illustrative constants for the residual-coverage figure. verify_figures.py
# re-derives every drawn width and printed count from these same numbers —
# stated in the caption as illustrative, never as observations.
RC_TOTAL = 1000          # illustrative attack set
RC_A_CATCH = 900         # guard A catches 900 → misses 100
RC_WORLDS = {            # among the 100 A missed: what B catches / what slips
    "i": {"b_catch": 90, "all_miss": 10,
          "name": "the world independence assumes"},
    "ii": {"b_catch": 20, "all_miss": 80,
           "name": "a correlated-miss world — same marginals"},
}
RC_X0, RC_W = 40.0, 560.0   # strip origin and width, SVG units

LADDER_RUNGS = [
    ("1 · Per-guard marginals",
     "each guard alone, same items, stated denominator"),
    ("2 · Pairwise intersections",
     "where two guards' catches and misses overlap"),
    ("3 · Union and all-miss",
     "what any guard catches; what all miss on the stated item set"),
    ("4 · Per-item release",
     "one row per item — every statistic above recomputable"),
]


def render_motif() -> str:
    """The campaign mark: a real table whose last column is not filled in."""
    return '''
<figure class="motif-fig" id="motif">
  <div class="fig-scroll" tabindex="0" role="region" aria-label="Illustrative benchmark table, scrollable">
  <table class="motif">
    <caption class="sr-only">An illustrative benchmark table: four guardrails
      with individual catch rates, and a final column for a declared
      full-exposure composition, which is not reported.</caption>
    <thead>
      <tr>
        <th scope="col">Guard A</th>
        <th scope="col">Guard B</th>
        <th scope="col">Guard C</th>
        <th scope="col">Guard D</th>
        <th scope="col" class="motif-stack">THE STACK</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>91%</td>
        <td>88%</td>
        <td>94%</td>
        <td>86%</td>
        <td class="motif-missing"><span class="mono">not reported</span></td>
      </tr>
    </tbody>
  </table>
  </div>
  <figcaption class="motif-caption"><strong>The missing column.</strong> Illustrative —
    the shape of the reporting gap, not any specific evaluation's numbers. Four
    individual catch rates on one attack set say almost nothing about the fifth
    cell: a static joint result for all four on the stated item set. The census
    below records which bounded inventory rows contain that evidence and which do
    not.</figcaption>
</figure>'''


def render_residual_fig() -> str:
    """Two worlds with identical marginals and different residual coverage."""
    panels = []
    a_w = RC_W * RC_A_CATCH / RC_TOTAL
    m_x = RC_X0 + a_w
    m_w = RC_W - a_w
    a_miss = RC_TOTAL - RC_A_CATCH
    y = 64
    for wid in ("i", "ii"):
        w = RC_WORLDS[wid]
        b_w = RC_W * w["b_catch"] / a_miss
        x_x = RC_X0 + b_w
        x_w = RC_W - b_w
        panels.append(f'''
<g class="rc-panel" data-world="{wid}">
<text x="{RC_X0:g}" y="{y - 10}" class="hmono">World {wid} — {esc(w["name"])}</text>
<rect x="{RC_X0:g}" y="{y}" width="{a_w:g}" height="26" class="rcA"/>
<rect x="{m_x:g}" y="{y}" width="{m_w:g}" height="26" class="rcM"/>
<text x="{RC_X0:g}" y="{y + 44}" class="hmono">A catches {RC_A_CATCH:,} of {RC_TOTAL:,} · misses {a_miss}</text>
<text x="{RC_X0:g}" y="{y + 76}" class="hmono">the {a_miss} A missed, magnified ↓</text>
<rect x="{RC_X0:g}" y="{y + 88}" width="{b_w:g}" height="26" class="rcB"/>
<rect x="{x_x:g}" y="{y + 88}" width="{x_w:g}" height="26" class="rcX"/>
<text x="{RC_X0:g}" y="{y + 132}" class="hmono">B catches {w["b_catch"]} of the {a_miss} A missed · {w["all_miss"]} remain uncaught in this static illustration</text>
</g>''')
        y += 170
    return f'''
<figure class="rc-fig" id="residual">
  <div class="fig-scroll" tabindex="0" role="region" aria-label="Residual coverage figure, scrollable">
  <svg viewBox="0 0 700 {y - 10}" role="img" aria-labelledby="rcft rcfd">
  <title id="rcft">Identical individual rates, different residual coverage</title>
  <desc id="rcfd">Two panels, each showing an illustrative attack set of one
thousand items. In both, guard A catches nine hundred and misses one hundred.
The one hundred missed items are magnified into a second strip showing what
guard B catches among them. In world one, B catches ninety of the hundred and
ten remain uncaught. In world two, B catches only twenty of the same hundred
and eighty remain uncaught. Guard B's overall rate is the same in both
worlds; only the overlap of the two guards' misses differs, and per-guard
rates do not report it.</desc>
{"".join(panels)}
  </svg>
  </div>
  <figcaption class="rc-caption"><strong>What does the second guard catch among what
    the first missed?</strong> Illustrative. Both worlds keep every per-guard rate
    identical; only the overlap of misses moves. The static all-miss count differs by
    a factor of {RC_WORLDS["ii"]["all_miss"] // RC_WORLDS["i"]["all_miss"]}. No table of per-guard columns
    distinguishes these worlds; the missing column does. This figure asserts its own
    geometry in CI and is not evidence about any real guardrail pair.</figcaption>
</figure>'''


def render_ladder_fig() -> str:
    """The disclosure ladder — four rungs from marginals to per-item release."""
    rungs = []
    x0, step_w, step_h = 40, 150, 44
    base_y = 218
    for i, (name, sub) in enumerate(LADDER_RUNGS):
        x = x0 + i * step_w
        y = base_y - i * step_h
        rungs.append(
            f'<rect x="{x}" y="{y}" width="{step_w - 10}" height="{step_h - 8}" '
            f'class="rung"/>'
            f'<text x="{x + 10}" y="{y + 17}" class="rung-name">{esc(name)}</text>'
            f'<foreignObject x="{x + 10}" y="{y + 22}" width="{step_w - 28}" height="66">'
            f'<p xmlns="http://www.w3.org/1999/xhtml" class="rung-sub">{esc(sub)}</p>'
            f'</foreignObject>')
    return f'''
<figure class="ladder-fig" id="ladder">
  <div class="fig-scroll" tabindex="0" role="region" aria-label="Minimum joint disclosure ladder figure, scrollable">
  <svg viewBox="0 0 660 260" role="img" aria-labelledby="ldt ldd">
  <title id="ldt">The minimum joint disclosure, as four ascending steps</title>
  <desc id="ldd">Four ascending steps. Step one: per-guard marginals — each
guard alone, on the same items, with a stated denominator. Step two: pairwise
intersections — where two guards' catches and misses overlap. Step three:
union and all-miss — what any guard catches and what all guards miss on the
stated item set. Step
four: per-item release — one row per item, from which every earlier statistic
can be recomputed.</desc>
  {"".join(rungs)}
  </svg>
  </div>
  <figcaption class="rc-caption"><strong>The disclosure ladder.</strong> Each step up
    reports strictly more of the joint structure. Step 3 is the campaign's ask — one
    union row and one all-miss row beside the marginals every evaluation already
    prints. Step 4 makes every other step recomputable by anyone.</figcaption>
</figure>'''


# ---------------------------------------------------------------- census
LABELS = {
    "PRESENT": ("present", "state-present"),
    "ABSENT": ("not published", "state-absent"),
    "AMBIGUOUS": ("ambiguous", "state-ambiguous"),
    "NOT_COMPARABLE": ("not comparable", "state-ambiguous"),
}
SCOPE_LABELS = {
    "printed_full_stack": "printed — covers the evaluated stack",
    "printed_partial_stack": "printed — covers part of the evaluated set",
    "computable_via_item_release": "computable — per-item outcomes released",
    "none": "",
}


def tri(row: dict, field: str) -> str:
    cell = row.get(field)
    return cell.get("value", "unstated") if isinstance(cell, dict) else "unstated"


def tri_cell(row: dict, field: str) -> str:
    cell = row.get(field) or {}
    value = esc(cell.get("value", "unstated"))
    evidence = esc(cell.get("evidence", ""))
    return (f'<span class="tri tri-{value}">{value}</span>'
            f'<span class="tri-ev">{evidence}</span>')


def native_action_translation_cell(row: dict) -> str:
    """An optional semantic annotation, separate from the ground-truth event."""
    cell = row.get("native_action_translation") or {}
    status = esc(str(cell.get("status", "not_established")).replace("_", " "))
    evidence = esc(cell.get("evidence", ""))
    return (f'<span class="mono">{status}</span>'
            f'<span class="tri-ev">{evidence}</span>')


def render_headline(census: dict, counts: dict) -> str:
    if counts["N"] == 0:
        return f'''
    <div class="headline headline-held">
      <p class="mono head-kicker">No count is claimed yet</p>
      <p>The criteria wording is locked and the starting rows are under primary-source
        examination. This page renders its headline from
        <a class="u" href="{SITE}/census.yaml">census.yaml</a> when rows are
        classified — until then it states only that the census exists. A census
        about missing reporting does not get to assert numbers it has not
        earned.</p>
    </div>'''
    proposition = census["proposition_template"].format(
        as_of=census["frozen_as_of"], N=counts["N"], M=counts["M"],
        K=counts["K"], criteria_version=census["criteria_version"])
    proposition = re.sub(r"\s+", " ", proposition.strip())
    scopes = counts["present_by_scope"]
    scope_bits = []
    for key in ("printed_full_stack", "printed_partial_stack",
                "computable_via_item_release"):
        if scopes.get(key):
            scope_bits.append(f'{scopes[key]} {SCOPE_LABELS[key]}')
    scope_line = (" · ".join(scope_bits)) if scope_bits else "—"
    # Identity, not just value: each numeral below says which census quantity
    # it is, so a later edit that retypes one is a failure rather than a
    # second opinion.
    f = fact_registry.fact_span
    strata = counts["M_strata"]
    modes = counts["K_evidence_modes"]
    return f'''
    <div class="headline">
      <p class="mono head-kicker">The census result — regenerated from the source file</p>
      <p class="head-prop">{esc(proposition)}</p>
      <p class="mono head-scope">The {f("MC-001.K", counts["K"])} is a heterogeneous discovery count, not one deployment estimand. Its primary joint-evidence classification splits as: {esc(scope_line)}. {f("MC-001.K.prints_composition_result", modes["prints_composition_result"])} artifacts print at least one composition result and {f("MC-001.K.releases_computable_items", modes["releases_computable_items"])} release aligned per-item outcomes; {f("MC-001.K.does_both", modes["does_both"])} artifact does both, so those descriptions overlap by construction.</p>
      <p class="mono head-scope">The {f("MC-001.M", counts["M"])} is a ladder, not a verdict — {f("MC-001.M1", strata["shared_basis"])} document a
        shared item set and a common event definition · {f("MC-001.M2", strata["threshold_not_contradicted"])} have no stated
        threshold mismatch · {f("MC-001.M3", strata["threshold_documented_full_exposure"])} document matched
        operating thresholds together with full exposure.</p>
      <p class="head-note">A qualifying artifact this search missed, or a row shown to be
        misclassified, changes these numbers — the criteria and the correction route are
        below, and every change lands in the revision history.</p>
    </div>'''


def render_criteria(data: dict) -> str:
    census = data["census"]
    items = "".join(
        f'<li><span class="mono crit-key">{esc(c["key"])}</span>'
        f'{esc(squash(c["text"]))}</li>'
        for c in census["inclusion_criteria"])
    exclusions = "".join(
        f"<li>{esc(squash(x))}</li>"
        for x in census["exclusion_rules"])
    protocol = census["search_protocol"]
    queries = "".join(f"<li>{esc(q)}</li>" for q in protocol["queries"])
    return f'''
    <div class="crit-grid">
      <div>
        <h3 class="mono crit-h">Inclusion — all must hold</h3>
        <ul class="crit-list">{items}</ul>
      </div>
      <div>
        <h3 class="mono crit-h">Excluded by rule</h3>
        <ul class="crit-list">{exclusions}</ul>
        <h3 class="mono crit-h" style="margin-top:1.2rem">Not a joint statistic</h3>
        <p class="crit-note">{esc(squash(census["non_criteria_note"]))}</p>
      </div>
    </div>
    <details class="protocol">
      <summary class="mono">The bounded search protocol — executed {esc(protocol["executed"])}</summary>
      <p class="crit-note">{esc(squash(protocol["bounded"]))}</p>
      <p class="mono crit-h" style="margin-top:.9rem">Fixed query list</p>
      <ul class="crit-list">{queries}</ul>
      <p class="crit-note" style="margin-top:.7rem">Snowball: {esc(protocol["snowball"])} ·
        Budget: {esc(squash(protocol["budget"]))}</p>
    </details>'''


def render_interpretation_sensitivities(data: dict, primary: dict) -> str:
    """Render alternate readings beside, never inside, the primary result.

    Counts are recomputed here rather than copied from a declared expected
    block. The verifier separately asserts that block, so this view makes the
    counterfactual legible while CI protects both paths.
    """
    sensitivities = data["census"].get("interpretation_sensitivities") or []
    if not sensitivities:
        return ""
    lock = data["census"].get("frozen_criteria_lock") or {}
    source_commit = str(lock.get("source_commit", ""))
    lock_html = ""
    if source_commit:
        lock_html = f'''
      <p class="mono crit-note">Frozen-wording lock: the literal inclusion criteria match
        <a class="u" href="https://github.com/Cubits11/cubits11.github.io/commit/{esc(source_commit)}">{esc(source_commit[:12])}</a>
        · sha256 {esc(str(lock.get("sha256", ""))[:12])} · checked by
        <span class="mono">verify_census.py</span>.</p>'''
    rows_by_id = {str(r.get("id")): r for r in data.get("benchmarks") or []}
    rows = []
    for sensitivity in sensitivities:
        alternative = verify_census.compute_counts(
            data, set(sensitivity["exclude_benchmark_ids"]))
        excluded = []
        for row_id in sensitivity["exclude_benchmark_ids"]:
            row = rows_by_id.get(row_id, {})
            excluded.append(
                f'<a class="u" href="#{esc(row_id)}">{esc(row_id)}</a>'
                if row else esc(row_id))
        rows.append(
            f'<li><span class="mono crit-key">{esc(sensitivity["label"])}</span>'
            f'{esc(squash(sensitivity["premise"]))} '
            f'Excludes {", ".join(excluded)}. '
            f'<span class="mono">counterfactual N/M/K = '
            f'{alternative["N"]}/{alternative["M"]}/{alternative["K"]}; '
            f'primary = {primary["N"]}/{primary["M"]}/{primary["K"]}</span></li>')
    return f'''
    <aside class="sensitivity" id="sensitivity" aria-labelledby="sensitivity-h">
      <h3 class="mono crit-h" id="sensitivity-h">Interpretive sensitivity</h3>
      <p class="crit-note">The primary result above is unchanged. This is a declared
        post-freeze counterfactual, not a retroactive rewrite of the criteria.</p>
{lock_html}
      <ul class="crit-list">{"".join(rows)}</ul>
    </aside>'''


def render_census_table(examined: list) -> str:
    if not examined:
        return ""
    rows = []
    for r in examined:
        cls, pill = LABELS[r["classification"]]
        scope = SCOPE_LABELS.get(r.get("joint_scope", "none"), "")
        scope_html = f'<span class="tri-ev">{esc(scope)}</span>' if scope else ""
        same_items = tri(r, "same_items_for_all_systems")
        rows.append(f'''
      <tr>
        <th scope="row"><a class="u" href="#{esc(r["id"])}">{esc(r["title"])}</a>
          <span class="tri-ev">{esc(r["authors_or_org"])} · {esc(r["publication_date"])}</span></th>
        <td>{esc(str(r["n_systems"]))}</td>
        <td>{esc(str(r["n_items"]))}</td>
        <td><span class="tri tri-{esc(same_items)}">{esc(same_items)}</span></td>
        <td class="stack-cell"><span class="mono {pill}">{esc(cls)}</span>{scope_html}</td>
      </tr>''')
    return f'''
    <div class="fig-scroll" tabindex="0" role="region" aria-label="The census table, scrollable">
    <table class="census-table">
      <caption class="sr-only">The census: each public guardrail evaluation
        examined, with its joint-statistic status in the final column.</caption>
      <thead>
        <tr>
          <th scope="col">Artifact</th>
          <th scope="col">Systems</th>
          <th scope="col">Items</th>
          <th scope="col">Same items</th>
          <th scope="col" class="motif-stack">THE STACK</th>
        </tr>
      </thead>
      <tbody>{"".join(rows)}
      </tbody>
    </table>
    </div>'''


DETAIL_FIELDS = [
    ("task", "Task"),
    ("dataset_population", "Population"),
    ("per_system_metrics", "Per-system results"),
    ("joint_statistic_evidence", "Joint statistic"),
    ("classification_reason", "Why this classification"),
]
DETAIL_TRIS = [
    ("same_items_for_all_systems", "Same items for all systems"),
    ("same_event_definition", "Same event definition"),
    ("thresholds_comparable", "Thresholds comparable"),
    ("all_systems_saw_all_items", "All systems saw all items"),
    ("item_level_outcomes_released", "Per-item outcomes released"),
    ("union_detection_reported", "Union detection reported"),
    ("all_miss_rate_reported", "All-miss rate reported"),
    ("pairwise_intersections_reported", "Pairwise intersections reported"),
    ("residual_coverage_reported", "Residual coverage reported"),
    ("uncertainty_reported", "Joint uncertainty reported"),
]


def render_row_details(examined: list) -> str:
    blocks = []
    for r in examined:
        cls, pill = LABELS[r["classification"]]
        dl = []
        for field, label_text in DETAIL_FIELDS:
            value = re.sub(r"\s+", " ", str(r[field]).strip())
            dl.append(f"<dt>{esc(label_text)}</dt><dd>{esc(value)}</dd>")
        for field, label_text in DETAIL_TRIS:
            dl.append(f"<dt>{esc(label_text)}</dt><dd>{tri_cell(r, field)}</dd>")
        if r.get("native_action_translation"):
            dl.append("<dt>Native action → shared-event translation</dt><dd>"
                      f"{native_action_translation_cell(r)}</dd>")
        systems = ", ".join(str(s) for s in r["systems"])
        dl.append(f"<dt>Systems</dt><dd>{esc(systems)}</dd>")
        prose = r.get("combination_prose")
        if prose:
            prose_note = (
                "The measured joint evidence and its scope are recorded above."
                if r["classification"] == "PRESENT" else
                "A recommendation to combine is recorded here because it is not a "
                "measured joint statistic."
            )
            dl.append("<dt>Combination prose</dt>"
                      f"<dd>“{esc(prose['quote'])}” — {esc(prose['location'])}. "
                      f"{prose_note}</dd>")
        passages = "".join(f"<li>{esc(p)}</li>" for p in r["source_passages"])
        dl.append(f'<dt>Source passages</dt><dd><ul class="nc">{passages}</ul></dd>')
        corrections = r.get("correction_history") or []
        if corrections:
            citems = "".join(
                f'<li><span class="mono">{esc(c["date"])}</span> — {esc(c["change"])}</li>'
                for c in corrections)
            dl.append(f'<dt>Corrections</dt><dd><ul class="nc">{citems}</ul></dd>')
        else:
            dl.append("<dt>Corrections</dt><dd>none recorded yet — the row "
                      "invites them</dd>")
        dl.append(f'<dt>Checked</dt><dd>{esc(r["last_checked"])}</dd>')
        archived = (f' · <a class="u" href="{esc(r["archived_url"])}">archived copy ↗</a>'
                    if r.get("archived_url") else "")
        blocks.append(f'''
    <article class="claim census-row" id="{esc(r["id"])}">
      <div class="claim-head">
        <h3 class="mono claim-id">{esc(r["id"])}</h3>
        <span class="mono {pill}">{esc(cls)}</span>
      </div>
      <p class="prop">{esc(r["title"])} — {esc(r["authors_or_org"])},
        {esc(r["publication_date"])} ·
        <a class="u" href="{esc(r["primary_url"])}">primary source ↗</a>{archived}</p>
      <dl>{"".join(dl)}</dl>
    </article>''')
    return "".join(blocks)


def render_under_review(rows: list) -> str:
    if not rows:
        return ""
    items = []
    for r in rows:
        link = (f'<a class="u" href="{esc(r["primary_url"])}">source ↗</a>'
                if r.get("primary_url") else
                '<span class="mono">no source bound yet</span>')
        note = re.sub(r"\s+", " ", str(r.get("notes", "")).strip())
        items.append(
            f'<div class="wall-row"><span class="mono wall-id">{esc(r["id"])}</span>'
            f'<div><p class="ur-title">{esc(r["title"])} — {link}</p>'
            f'<p class="ur-note">{esc(note)}</p></div></div>')
    return f'''
  <section class="zone" id="under-review" aria-labelledby="ur-h">
    <h2 id="ur-h">Under examination</h2>
    <p class="zone-intro">Named and sourced, not yet classified. These rows count toward
      nothing — a census about reporting standards does not get to count rows it has
      not finished reading.</p>
    <div class="wall">{"".join(items)}
    </div>
  </section>'''


def render_exclusions(data: dict) -> str:
    exclusions = data.get("exclusions") or []
    unexamined = data.get("unexamined_candidates") or []
    if not exclusions and not unexamined:
        return ""
    body = []
    if exclusions:
        rows = "".join(
            f'<div class="wall-row"><span class="mono wall-id">{esc(r["id"])}</span>'
            f'<div><p class="ur-title">{esc(r["title"])}'
            + (f' — <a class="u" href="{esc(r["primary_url"])}">source ↗</a>'
               if r.get("primary_url") else "")
            + f'</p><p class="ur-note">Excluded: {esc(squash(r["reason"]))}</p></div></div>'
            for r in exclusions)
        body.append(f'<h3 class="mono crit-h">Examined and excluded</h3>'
                    f'<div class="wall">{rows}</div>')
    if unexamined:
        rows = "".join(
            f'<li>{esc(c.get("title", c.get("url", "?")))}'
            + (f' — <a class="u" href="{esc(c["url"])}">source ↗</a>'
               if c.get("url") else "") + "</li>"
            for c in unexamined)
        body.append('<h3 class="mono crit-h" style="margin-top:1.4rem">Surfaced, not examined'
                    '</h3><p class="zone-intro">Candidates the bounded search found but did '
                    'not examine. They are listed so the bound is visible, and they count '
                    f'toward nothing.</p><ul class="crit-list">{rows}</ul>')
    return f'''
  <section class="zone" id="exclusions" aria-labelledby="ex-h">
    <h2 id="ex-h">The boundary of the search</h2>
    {"".join(body)}
  </section>'''


def render_revisions(census: dict, examined: list) -> str:
    entries = []
    for e in census["revision_history"]:
        entries.append(f'<li><span class="mono">{esc(e["date"])}</span> — '
                       f'{esc(squash(e["change"]))}</li>')
    row_corrections = sum(len(r.get("correction_history") or []) for r in examined)
    return f'''
  <section class="zone" id="corrections" aria-labelledby="corr-h">
    <h2 id="corr-h">Corrections and revision history</h2>
    <p class="zone-intro">Changes to this census are recorded here, in the page they
      change — not only in a repository log. Row-level corrections
      ({row_corrections} recorded) live inside each row above. The canonical
      <a class="u" href="/corrections/">correction policy</a> states the
      response and logging rules.</p>
    <ul class="manual-list" data-fact-state="historical">{"".join(entries)}</ul>
    <div class="correct-route">
      <h3 class="mono crit-h">Correct this record</h3>
      <p class="zone-intro">If a row misreads its source, a supposedly absent statistic
        exists, or a qualifying evaluation is missing:
        <a class="u" href="https://github.com/Cubits11/cubits11.github.io/issues">open an
        issue ↗</a> or write to
        <a class="u" href="mailto:bhavepranavwork@gmail.com">bhavepranavwork@gmail.com</a>.
        A confirmed correction updates the row, the counts, and this history — being
        corrected is the mechanism working, and correction credit is recorded in the row.</p>
      <p class="zone-intro" style="margin-top:.8rem"><strong>Benchmark authors:</strong> if you
        retained one decision per item per system, the
        <a class="u" href="/missing-column/disclosure/">minimum joint disclosure</a> is one
        table away — and this census reclassifies your row to
        <span class="mono">present</span> the day you publish it.</p>
    </div>
  </section>'''


# ---------------------------------------------------------------- chrome
def jsonld_script(obj: dict) -> str:
    return ('\n<script type="application/ld+json">\n'
            + json.dumps(obj, indent=2, ensure_ascii=False)
            + "\n</script>")


def breadcrumbs(*trail: tuple) -> str:
    items = []
    for i, (name, url) in enumerate(trail, start=1):
        item = {"@type": "ListItem", "position": i, "name": name}
        if url:
            item["item"] = SITE + url
        items.append(item)
    return jsonld_script({"@context": "https://schema.org",
                          "@type": "BreadcrumbList",
                          "itemListElement": items})


def census_dataset_jsonld(census: dict) -> str:
    modified = max(e["date"] for e in census["revision_history"])
    return jsonld_script({
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "The Missing Column Census",
        "description": (
            "A source-bound census of public evaluations that compare two or "
            "more LLM guardrail, safeguard, or moderation systems, recording "
            "whether each reports any item-level joint statistic for the "
            "combined stack (union detection, all-miss rate, pairwise "
            "intersections, residual coverage, or released per-item "
            "outcomes) or only per-system marginals. The literal inclusion "
            "criteria are locked in repository history before row "
            "classification; every row binds to its primary "
            "source; counts are recomputed mechanically from the file."),
        "url": f"{SITE}/missing-column/",
        "sameAs": "https://github.com/Cubits11/cubits11.github.io/blob/main/census.yaml",
        "isAccessibleForFree": True,
        "creator": {"@type": "Person", "name": "Pranav Bhave",
                    "url": f"{SITE}/"},
        "dateModified": str(modified),
        "keywords": ["LLM guardrails", "AI safety evaluation",
                     "content moderation benchmarks", "jailbreak detection",
                     "joint failure statistics", "reporting standards"],
        "distribution": [{
            "@type": "DataDownload",
            "encodingFormat": "application/yaml",
            "contentUrl": f"{SITE}/census.yaml",
        }],
    })


def page_head(title: str, desc: str, path: str, extra_css: str,
              jsonld: str = "", release_marker: str = "") -> str:
    return f'''<!doctype html>
<!-- GENERATED FILE — do not edit by hand.
     Source: census.yaml · renderer: scripts/generate_missing_column.py
     CI regenerates this page and fails on drift. -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{SITE}{path}">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{SITE}{path}">
<meta property="og:image" content="{SITE}/assets/img/og-missing-column.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="A benchmark table with four filled guardrail columns and an empty fifth column labelled THE STACK">
<meta property="og:site_name" content="Cubits11">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{SITE}/assets/img/og-missing-column.png">
<meta name="twitter:image:alt" content="A benchmark table with four filled guardrail columns and an empty fifth column labelled THE STACK">
<meta name="robots" content="max-image-preview:large">
<meta name="theme-color" media="(prefers-color-scheme: light)" content="#F1EDE2">
<meta name="theme-color" media="(prefers-color-scheme: dark)" content="#0B0F0A">
{release_marker}
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%230B0F0A'/%3E%3Crect x='12' y='11' width='17' height='17' rx='4' fill='%23EDE8DA'/%3E%3Crect x='35' y='11' width='17' height='17' rx='4' fill='%23EDE8DA'/%3E%3Crect x='12' y='32' width='17' height='17' rx='4' fill='%23EDE8DA'/%3E%3Crect x='35' y='32' width='17' height='17' rx='4' fill='%23EDE8DA'/%3E%3Crect x='13.5' y='53' width='37' height='0.1' rx='2' fill='none' stroke='%23C9A15E' stroke-width='3'/%3E%3C/svg%3E">
<script>try{{var t=localStorage.getItem('theme');if(t==='dark'||t==='light'){{document.documentElement.dataset.theme=t;var m=document.querySelectorAll('meta[name="theme-color"]');for(var i=0;i<m.length;i++)m[i].content=t==='dark'?'#0B0F0A':'#F1EDE2'}}}}catch(e){{}}</script>
<link rel="stylesheet" href="/assets/site.css">{jsonld}
<script defer src="/assets/site.js"></script>
<style>
body{{font-size:1rem;line-height:1.65}}
.container{{width:min(1060px,100% - 2*clamp(1.25rem,5vw,3rem))}}
.mono{{font-size:.68rem}}
header.page{{padding:7.9rem 0 2.2rem}}
h1{{font-weight:520;font-size:clamp(2.4rem,6vw,3.8rem);line-height:1.04;margin:0 0 1rem;letter-spacing:-.018em}}
.intro{{color:var(--muted);max-width:48em}}
.zone{{margin-top:4rem;border-top:1px solid var(--line);padding-top:2rem}}
.zone h2{{font-weight:520;font-size:clamp(1.5rem,3vw,2.1rem);margin:0 0 .6rem;letter-spacing:-.01em}}
.zone .zone-intro{{color:var(--muted);max-width:46em}}
.zone h3{{font-weight:520;margin:1.6rem 0 .5rem}}
.fig-scroll{{overflow-x:auto}}
.lede{{font-size:1.14rem;line-height:1.5}}
.snapshot-note{{margin-top:1rem;padding:.7rem .9rem;border-left:2px solid var(--line-strong);
  color:var(--muted);font-size:.88rem}}
.epi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(15rem,100%),1fr));
  gap:1rem;margin-top:1rem}}
.epi{{border:1px solid var(--line);padding:.85rem 1rem;min-width:0}}
.epi h3{{font:400 .64rem/1.2 var(--mono);letter-spacing:.08em;text-transform:uppercase;
  color:var(--muted);margin:0 0 .4rem}}
.epi p{{margin:0;font-size:.9rem}}
.fig-scroll:focus-visible{{outline:2px solid var(--evidence,currentColor);outline-offset:3px}}
.wall{{margin-top:1.6rem;border:1px solid var(--line-strong);background:var(--surface)}}
.wall-row{{display:grid;grid-template-columns:8.5rem 1fr;gap:1rem;padding:1rem 1.2rem;border-bottom:1px solid var(--line)}}
.wall-row:last-child{{border-bottom:none}}
.wall-id{{color:var(--gold);overflow-wrap:anywhere}}
.manual-list{{margin:1.2rem 0 0;padding-left:1.1rem;color:var(--muted);font-size:.92rem}}
.manual-list li{{margin:.35rem 0}}
.ur-title{{margin:0 0 .3rem}}
.ur-note{{margin:0;color:var(--muted);font-size:.92rem}}
footer{{border-top:1px solid var(--line);margin-top:3.5rem;padding:2rem 0 3rem;color:var(--muted);font-size:.88rem}}
.foot-links{{display:flex;flex-wrap:wrap;gap:1.4rem}}
{extra_css}
@media (max-width:600px){{.wall-row{{grid-template-columns:1fr}}}}
@media print{{body{{background:#fff;color:#000}}}}
</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-head">
  <div class="container">
    <a class="wordmark" href="/">Pranav Bhave</a>
    <nav class="site-nav mono" aria-label="Site">
      <a href="/missing-column/">The Missing Column</a>
      <a href="/observatory/">Evidence</a>
      <a href="/writing/">Writing</a>
      <a href="/work/">Work with me</a>
      <a href="/resume/">About</a>
    </nav>
    <button class="theme-toggle" id="themeToggle" aria-label="Toggle color theme" aria-pressed="false">
      <svg class="sun-only" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4.4"/><path d="M12 2.5v2.4M12 19.1v2.4M2.5 12h2.4M19.1 12h2.4M5 5l1.7 1.7M17.3 17.3 19 19M19 5l-1.7 1.7M6.7 17.3 5 19"/></svg>
      <svg class="moon-only" viewBox="0 0 24 24" aria-hidden="true"><path d="M20.2 14.2A8.2 8.2 0 0 1 9.8 3.8a8.2 8.2 0 1 0 10.4 10.4z"/></svg>
    </button>
  </div>
</header>'''


PAGE_FOOT = '''
<footer>
  <div class="container">
    <div class="foot-links mono">
      <a class="u" href="/missing-column/">The Missing Column</a>
      <a class="u" href="/missing-column/disclosure/">Minimum disclosure</a>
      <a class="u" href="/answers/why-guardrail-miss-rates-do-not-multiply/">Why miss rates do not multiply</a>
      <a class="u" href="/answers/how-to-evaluate-guardrails-you-plan-to-stack/">Evaluating stacked guardrails</a>
      <a class="u" href="/answers/what-does-the-second-guardrail-add/">What the second guard adds</a>
      <a class="u" href="/corrections/">Corrections policy</a>
      <a class="u" href="/ledger/">Evidence ledger</a>
      <a class="u" href="/observatory/">Claim observatory</a>
      <a class="u" href="/modules/">Modules</a>
      <a class="u" href="/archive/">Archive</a>
      <a class="u" href="/stack-study/">Study preflight</a>
      <a class="u" href="/work/">Work with me</a>
      <a class="u" href="/">← The record</a>
    </div>
  </div>
</footer>
<script>
(function(){
  document.documentElement.classList.add('js');
  var root=document.documentElement,meta=document.querySelectorAll('meta[name="theme-color"]'),toggle=document.getElementById('themeToggle');
  if(!toggle)return;
  function isDark(){if(root.dataset.theme)return root.dataset.theme==='dark';return matchMedia('(prefers-color-scheme: dark)').matches}
  function sync(){var d=isDark();toggle.setAttribute('aria-pressed',String(d));toggle.setAttribute('aria-label',d?'Switch to light theme':'Switch to dark theme')}
  function apply(n){root.dataset.theme=n;try{localStorage.setItem('theme',n)}catch(e){}meta.forEach(function(m){m.content=n==='dark'?'#0B0F0A':'#F1EDE2'});sync()}
  toggle.addEventListener('click',function(){var n=isDark()?'light':'dark';var r=matchMedia('(prefers-reduced-motion: reduce)').matches;if(document.startViewTransition&&!r){document.startViewTransition(function(){apply(n)})}else{apply(n)}});
  sync();matchMedia('(prefers-color-scheme: dark)').addEventListener('change',sync);
})();
</script>
</body>
</html>
'''

LANDING_CSS = '''
.class-bar span b{color:var(--ink)}
.motif-fig{margin:2.6rem 0 0}
table.motif,table.census-table{border-collapse:collapse;width:100%;background:var(--surface);border:1px solid var(--line-strong)}
table.motif th,table.motif td{border:1px solid var(--line);padding:.8rem 1rem;text-align:center;font-variant-numeric:tabular-nums}
table.motif th{font-family:var(--mono);font-size:.66rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:400}
table.motif td{font-family:var(--serif);font-size:1.5rem}
th.motif-stack{color:var(--gold)!important}
td.motif-missing{background:transparent;border:1px dashed var(--review);color:var(--review)}
td.motif-missing .mono{color:var(--review);font-size:.68rem;letter-spacing:.06em}
.motif-caption,.rc-caption{margin-top:.9rem;color:var(--muted);font-size:.92rem;max-width:52em}
.motif-caption strong,.rc-caption strong{color:var(--ink)}
.mc-cta{display:flex;flex-wrap:wrap;gap:.8rem;margin-top:1.6rem}
.headline{border:1px solid var(--line-strong);border-left:2px solid var(--evidence);background:var(--surface);padding:1.4rem 1.6rem;margin-top:1.8rem}
.headline-held{border-left:2px dashed var(--line-strong)}
.head-kicker{color:var(--gold);letter-spacing:.08em;text-transform:uppercase}
.head-prop{font-family:var(--serif);font-size:1.18rem;line-height:1.55;margin:.6rem 0 .5rem}
.head-scope{color:var(--muted)}
.head-note,.headline-held p:last-child{color:var(--muted);font-size:.92rem;margin:.5rem 0 0}
.sensitivity{border:1px solid var(--line-strong);border-left:2px solid var(--review);background:var(--surface);padding:1.15rem 1.35rem;margin-top:1.2rem;scroll-margin-top:5.5rem}
.sensitivity .crit-note{margin:.35rem 0 .7rem}
.crit-grid{display:grid;grid-template-columns:1fr 1fr;gap:2rem;margin-top:1.4rem}
.crit-h{color:var(--gold);letter-spacing:.08em;text-transform:uppercase;font-size:.64rem;margin:0 0 .5rem;font-weight:400}
.crit-list{margin:0;padding-left:1.1rem;color:var(--muted);font-size:.92rem}
.crit-list li{margin:.35rem 0}
.crit-key{display:block;color:var(--ink);font-size:.62rem;letter-spacing:.06em}
.crit-note{color:var(--muted);font-size:.92rem;margin:.3rem 0 0}
.protocol{margin-top:1.6rem;border:1px solid var(--line);background:var(--surface);padding:.9rem 1.1rem}
.protocol summary{cursor:pointer;color:var(--muted)}
table.census-table th,table.census-table td{border-bottom:1px solid var(--line);padding:.75rem .9rem;text-align:left;vertical-align:top}
table.census-table thead th{font-family:var(--mono);font-size:.64rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:400}
table.census-table tbody th{font-weight:520}
.census-table .u{overflow-wrap:anywhere}
.stack-cell .mono{letter-spacing:.05em}
.state-present{color:var(--evidence)}
.state-absent{color:var(--review)}
.state-ambiguous{color:var(--muted)}
.tri{font-family:var(--mono);font-size:.68rem;letter-spacing:.05em}
.tri-yes{color:var(--evidence)}
.tri-no{color:var(--review)}
.tri-unstated,.tri-mixed{color:var(--muted)}
.tri-ev{display:block;color:var(--muted);font-size:.8rem;margin-top:.15rem}
.census-row{border:1px solid var(--line-strong);background:var(--surface);padding:1.3rem 1.5rem;margin-top:1.2rem}
.claim-head{display:flex;align-items:baseline;gap:.8rem;flex-wrap:wrap}
.claim-id{color:var(--gold);font-size:.72rem;font-weight:400;margin:0;letter-spacing:.09em}
.census-row .prop{font-family:var(--serif);font-size:1.02rem;line-height:1.55;margin:.5rem 0 .9rem}
.census-row dl{display:grid;grid-template-columns:14rem 1fr;gap:.4rem 1.2rem;margin:0;font-size:.92rem}
.census-row dt{min-width:0;overflow-wrap:anywhere;font-family:var(--mono);font-size:.62rem;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);padding-top:.2rem}
.census-row dd{margin:0;color:var(--ink);min-width:0;overflow-wrap:anywhere}
ul.nc{margin:.1rem 0 0;padding-left:1.1rem;color:var(--muted)}
ul.nc li{margin:.2rem 0}
.rc-fig{margin:1.8rem 0 0}
.rc-fig svg,.motif-fig svg{width:100%;min-width:560px;height:auto;display:block}
.rcA{fill:var(--evidence);opacity:.55}
.rcM{fill:var(--review);opacity:.75}
.rcB{fill:var(--evidence);opacity:.55}
.rcX{fill:var(--invalid);opacity:.8}
.hmono,.rung-name{font-family:var(--mono);font-size:12px;fill:var(--muted)}
.correct-route{margin-top:1.8rem;border:1px solid var(--line-strong);border-left:2px solid var(--review);background:var(--surface);padding:1.2rem 1.4rem}
@media (max-width:700px){.crit-grid{grid-template-columns:1fr}.census-row dl{grid-template-columns:1fr}.census-row dt{padding-top:.5rem}}
@media (max-width:560px){table.motif th,table.motif td{padding:.55rem .3rem}table.motif td{font-size:1.02rem}table.motif th{font-size:.5rem;letter-spacing:.04em}td.motif-missing .mono{font-size:.54rem;letter-spacing:.02em}}
'''

DISCLOSURE_CSS = '''
.ladder-fig{margin:2.2rem 0 0}
.ladder-fig svg{width:100%;min-width:560px;height:auto;display:block}
.rung{fill:var(--surface);stroke:var(--line-strong)}
.rung-name{fill:var(--gold);font-size:11px;letter-spacing:.04em}
.rung-sub{margin:0;font-family:var(--sans);font-size:10.5px;line-height:1.35;color:var(--muted)}
.rc-caption{margin-top:.9rem;color:var(--muted);font-size:.92rem;max-width:52em}
.rc-caption strong{color:var(--ink)}
.fig-scroll{overflow-x:auto}
.fig-scroll:focus-visible{outline:2px solid var(--evidence,currentColor);outline-offset:3px}
pre{overflow-x:auto;max-width:100%}
pre:focus-visible{outline:2px solid var(--evidence,currentColor);outline-offset:3px}
.disc-list{margin:1.4rem 0 0;padding-left:0;list-style:none;counter-reset:disc}
.disc-list li{counter-increment:disc;border:1px solid var(--line);border-left:2px solid var(--evidence);background:var(--surface);padding:.9rem 1.1rem;margin:.6rem 0}
.disc-list li::before{content:counter(disc,decimal-leading-zero);font-family:var(--mono);color:var(--gold);font-size:.66rem;letter-spacing:.08em;display:block;margin-bottom:.3rem}
.disc-list strong{display:block;margin-bottom:.2rem}
.disc-list p{margin:0;color:var(--muted);font-size:.92rem}
.tmpl pre{background:var(--surface);border:1px solid var(--line-strong);padding:1.1rem 1.2rem;overflow-x:auto;font-family:var(--mono);font-size:.76rem;line-height:1.75;color:var(--ink);margin:1.2rem 0 0}
table.census-table{border-collapse:collapse;width:100%;background:var(--surface);border:1px solid var(--line-strong);margin-top:1.2rem}
table.census-table th,table.census-table td{border-bottom:1px solid var(--line);padding:.7rem .9rem;text-align:left;font-variant-numeric:tabular-nums}
table.census-table thead th{font-family:var(--mono);font-size:.64rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:400}
table.census-table tbody th{font-weight:520}
tr.demo-union th,tr.demo-union td{color:var(--evidence);border-top:1px solid var(--line-strong)}
tr.demo-allmiss th,tr.demo-allmiss td{color:var(--invalid)}
.precond{border:1px solid var(--line-strong);border-left:2px solid var(--review);background:var(--surface);padding:1.1rem 1.3rem;margin-top:1.4rem;color:var(--muted);font-size:.92rem}
.precond strong{color:var(--ink)}
.ask{border:1px solid var(--line-strong);background:var(--surface);padding:1.1rem 1.3rem;margin-top:1.4rem}
.ask p{margin:0;color:var(--muted);font-size:.95rem}
.crit-h{color:var(--gold);letter-spacing:.08em;text-transform:uppercase;font-size:.64rem;margin:0 0 .5rem;font-weight:400}
'''


def render_landing(data: dict) -> str:
    census = data["census"]
    counts = verify_census.compute_counts(data)
    # Every census numeral this page states carries the identity of the
    # quantity it asserts. A sentence that hand-types one has no identity to
    # check, which is exactly how a stale K survived every gate that existed.
    k_fact = fact_registry.fact_span("MC-001.K", counts["K"])
    rows = data.get("benchmarks") or []
    examined = [r for r in rows if r["status"] == "examined"]
    under_review = [r for r in rows if r["status"] == "under_review"]
    # Title and description carry the load-bearing numerals, derived from
    # compute_counts — a hand-typed numeral here would be the schema-v3
    # failure in a <title> tag.
    m3 = counts["M_strata"]["threshold_documented_full_exposure"]
    if counts["N"]:
        # verify_growth.py gates these surfaces: title <= 72 chars,
        # description 70-200.
        title = (f"The Missing Column — {m3} of {counts['N']} at matched "
                 f"thresholds (frozen {census['frozen_as_of']})")
        desc = (f"Bounded, source-bound census (frozen "
                f"{census['frozen_as_of']}): {m3} of {counts['N']} public "
                f"guardrail evaluations document matched operating "
                f"thresholds with full exposure; {counts['K']} preserve "
                f"joint evidence.")
    else:
        title = "The Missing Column — a guardrail evaluation census"
        desc = ("A bounded, source-bound inventory of which public guardrail "
                "evaluations preserve joint-evidence artifacts — union "
                "detection, all-miss, or per-item outcomes — beside "
                "per-system scores.")
    releases = counts["present_by_scope"].get("computable_via_item_release", 0)
    release_note = f" ({releases} via data release)" if releases else ""
    snapshot = census["snapshot"]
    count_bar = (f"{counts['N']} examined · {counts['M_strata']['shared_basis']} shared "
                 f"item/common-event basis ({counts['M_strata']['threshold_documented_full_exposure']} "
                 f"at documented matched thresholds with full exposure) · "
                 f"{counts['K']} heterogeneous joint-evidence artifacts{release_note}" if counts["N"]
                 else f"{counts['under_review']} under examination · no count claimed yet")
    census_zone_rows = ""
    if examined:
        census_zone_rows = (render_census_table(examined)
                            + render_row_details(examined))
    jsonld = (census_dataset_jsonld(census)
              + breadcrumbs(("The record", "/"),
                            ("The Missing Column", None)))
    census_sha = hashlib.sha256((ROOT / "census.yaml").read_bytes()).hexdigest()
    marker = (f'<meta name="census-sha256" content="{census_sha}">\n'
              f'<meta name="correction-policy-url" content="{SITE}/corrections/">')
    head = page_head(title, desc, "/missing-column/", LANDING_CSS, jsonld,
                     release_marker=marker)
    return head + f'''
<div class="class-bar mono">
  <div class="container">
    <span><b>The Missing Column</b> — a source-bound census · generated from <a class="u" href="{SITE}/census.yaml">census.yaml</a></span>
    <span>{esc(count_bar)}</span>
    <span>criteria v{esc(census["criteria_version"])} wording locked {esc(census["frozen_as_of"])}</span>
  </div>
</div>
<header class="page">
  <div class="container">
    <h1>The missing column</h1>
    <p class="intro lede">Benchmarks commonly report what each detector catches on its own.
      To understand a deployed stack, you also need what those detectors catch — and miss —
      <em>together</em>. That number is usually not published. In this census, frozen
      {esc(census["frozen_as_of"])}, {fact_registry.fact_span("MC-001.M3", counts["M_strata"]["threshold_documented_full_exposure"])} of
      {fact_registry.fact_span("MC-001.N", counts["N"])} evaluations record matched operating
      thresholds together with full exposure.</p>
    <p class="intro">This is a bounded record of which public evaluations preserve the
      evidence needed to recover it. A static evaluation and a deployed route are different
      objects, so the record tracks what each artifact actually publishes rather than what a
      stack would do. Its own headline is generated from a source file that anyone can
      mechanically make false.</p>
    <p class="snapshot-note"><b>Census {esc(snapshot["version"])}.</b> {esc(snapshot["public_statement"])}
      Frozen {esc(snapshot["frozen_as_of"])}; annotated {esc(snapshot["annotated_as_of"])}.
      Rules for new observations are fixed in advance in
      <a class="u" href="{SITE}/census_protocol_v1.yaml">census_protocol_v1.yaml</a>.</p>
  </div>
</header>
<main class="container" id="main">
  {render_motif()}
  <div class="mc-cta">
    <a class="btn btn-solid" href="#census">Inspect the census</a>
    <a class="btn" href="/missing-column/disclosure/">Publish the missing row</a>
    <a class="btn" href="#corrections">Correct this record</a>
  </div>
  <section class="zone" id="epistemic-status" aria-labelledby="epi-h">
    <h2 id="epi-h">What this page is claiming</h2>
    <div class="epi-grid">
      <div class="epi"><h3>Observed</h3><p>What the examined artifacts print, each bound to a
        quoted primary-source passage in <a class="u" href="{SITE}/census.yaml">census.yaml</a>.
        Every row records its retrieval date.</p></div>
      <div class="epi"><h3>Derived</h3><p>The counts above. They are recomputed from the rows by
        <span class="mono">verify_census.py</span> on every run; no headline number is typed by
        hand anywhere in this repository.</p></div>
      <div class="epi"><h3>Interpreted</h3><p>Where a row sits on the disclosure ladder, and its
        reconstruction class. These are judgements made under written rules, by a single
        reviewer, and they are contestable.</p></div>
      <div class="epi"><h3>Not claimed</h3><p>That the search found every qualifying artifact;
        that an unreported quantity is unknowable — comparable marginals still bound it; that
        an OR-union equals a deployed system's behaviour; or that anyone has adopted the
        proposed reporting protocol.</p></div>
    </div>
  </section>
  <div class="mc-cta-after">
  </div>

  <section class="zone" id="why" aria-labelledby="why-h">
    <h2 id="why-h">Why the last cell cannot be inferred</h2>
    <p class="zone-intro">Per-system rates do not determine the static all-miss rate of a
      declared full-exposure composition. Two guards
      that each miss 10% of attacks can jointly miss anywhere from 0% to 10% — the
      individual columns are compatible with every world in that interval, and
      multiplying the rates silently assumes the one world where the guards' failures
      are independent. The <a class="u" href="/#worlds">front-page instrument</a> lets you
      move through those worlds with both marginals pinned;
      <a class="u" href="/essays/when-marginals-are-not-enough/">the flagship essay</a>
      carries the full argument with witnessed endpoints, and
      <a class="u" href="/modules/002-pairwise-is-not-enough/">module 002</a> shows that
      even pairwise numbers cannot rescue the inference. What resolves it is not more
      per-system precision. It is one more column, measured on the same items.</p>
  </section>

  <section class="zone" id="residual-zone" aria-labelledby="rz-h">
    <h2 id="rz-h">What the second guard actually adds</h2>
    <p class="zone-intro">One static composition question is: among the items the first
      guard missed, what does the second catch? That is residual coverage, and no set
      of per-guard columns contains it. Sequential route risk requires additional
      observations beyond this static table.</p>
    {render_residual_fig()}
  </section>

  <section class="zone" id="census" aria-labelledby="census-h">
    <h2 id="census-h">The census</h2>
    <p class="zone-intro">Every row binds to its primary source and records the same
      fields; the classification enum is fixed; the counts are recomputed from the file
      by <a class="u" href="https://github.com/Cubits11/cubits11.github.io/blob/main/scripts/verify_census.py">verify_census.py</a>
      on every push. The literal inclusion wording is locked in repository history before
      row classification; that is a reproducibility lock, not an independent preregistration.</p>
    {render_criteria(data)}
    {render_headline(census, counts)}
{render_interpretation_sensitivities(data, counts)}
    {census_zone_rows}
    <div class="headline-nonclaims" style="margin-top:2rem">
      <h3 class="mono crit-h">What this census does not claim</h3>
      <ul class="crit-list">
        <li>It does not claim any evaluated stack performs poorly — an empty column is a
          reporting fact, not a performance finding.</li>
        <li>It does not claim the unmeasured joint statistics would reveal dependence;
          measuring instead of assuming is the entire point.</li>
        <li>Its {k_fact} is an inclusive discovery count of noninterchangeable artifacts — not an
          all-miss rate, a stack-quality score, or a deployment conclusion.</li>
        <li>It does not audit the quality of any per-system evaluation beyond the fields
          each row records.</li>
        <li>It covers the artifacts found by the documented bounded search — not
          everything in existence. A qualifying artifact it missed falsifies the "among
          N" statement and is added on discovery.</li>
      </ul>
    </div>
  </section>
  {render_under_review(under_review)}
  {render_exclusions(data)}

  <section class="zone" id="standard" aria-labelledby="std-h">
    <h2 id="std-h">The missing row, specified</h2>
    <p class="zone-intro">The fix is small enough to paste into a results table: union
      detection and the all-miss rate over the same items, with the denominator and
      event definition that make them meaningful. The
      <a class="u" href="/missing-column/disclosure/">Minimum Joint Guardrail
      Disclosure</a> page carries the exact template, its preconditions, and a tested
      reference implementation.</p>
  </section>
  {render_revisions(census, examined)}

  <section class="zone replay" aria-labelledby="replay-h">
    <h2 id="replay-h">Replay manifest</h2>
    <p class="zone-intro">The exact commands that re-verify this census, starting from an
      empty directory: a POSIX shell with <span class="mono">git</span> and
      Python&nbsp;3.11+ (with its standard <span class="mono">venv</span> module) is the
      whole environment. Nothing on this page requires trusting this page.</p>
    <pre style="background:var(--surface);border:1px solid var(--line-strong);padding:1.1rem 1.2rem;overflow-x:auto;font-family:var(--mono);font-size:.78rem;line-height:1.8;color:var(--ink);margin:1.4rem 0 0">git clone https://github.com/Cubits11/cubits11.github.io.git
cd cubits11.github.io
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt       # pyyaml — the only dependency
python scripts/verify_census.py --counts        # row shape + N/M/K recomputed from census.yaml
python scripts/generate_missing_column.py --check  # this page matches the census file
python scripts/verify_figures.py                # figure geometry, asserted to 1e-9
python scripts/mjgd_reference.py --test         # the disclosure arithmetic, tested</pre>
    <p class="zone-intro" style="margin-top:1.1rem">Those four checks verify this census.
      The whole-repository replay — every claim binding, generated page, figure assertion,
      and bound reproduction, re-run from a fresh clone of one commit — is one further
      command from the same shell: <span class="mono">python
      scripts/verify_clean_clone.py</span>. The separately pinned MC-004 computation is
      <a class="u" href="/missing-column/reproduce/">reproducible from its released files</a>.</p>
  </section>
</main>''' + PAGE_FOOT


def render_corrections(data: dict) -> str:
    """Render the stable policy route social copy and smoke checks can bind."""
    census = data["census"]
    entries = "".join(
        f'<li><span class="mono">{esc(entry["date"])}</span> — '
        f'{esc(squash(entry["change"]))}</li>'
        for entry in census["revision_history"])
    title = "Corrections policy — The Missing Column"
    desc = ("The correction policy and public revision history for the "
            "Missing Column Census.")
    census_sha = hashlib.sha256((ROOT / "census.yaml").read_bytes()).hexdigest()
    marker = f'<meta name="census-sha256" content="{census_sha}">'
    head = page_head(
        title, desc, "/corrections/", "", breadcrumbs(
            ("The record", "/"), ("The Missing Column", "/missing-column/"),
            ("Corrections policy", None)), release_marker=marker)
    return head + f'''
<div class="class-bar mono">
  <div class="container">
    <span><b>Corrections policy</b> — The Missing Column Census</span>
    <span>canonical route · <a class="u" href="/missing-column/#corrections">row-level history</a></span>
  </div>
</div>
<header class="page">
  <div class="container">
    <h1>Correct the record</h1>
    <p class="intro">A public record that cannot be corrected is not evidence. This
      page is the canonical correction route for the Missing Column Census.</p>
  </div>
</header>
<main class="container" id="main">
  <section class="zone" id="correction-policy" aria-labelledby="policy-h">
    <h2 id="policy-h">Policy</h2>
    <ol class="crit-list">
      <li>Send the exact row ID, the disputed field, and a stable primary-source
        locator through <a class="u" href="https://github.com/Cubits11/cubits11.github.io/issues">a repository issue ↗</a>
        or <a class="u" href="mailto:bhavepranavwork@gmail.com">email</a>.</li>
      <li>Every report is logged publicly the same calendar day it is received:
        either as a verified correction or as an explicit under-review entry.
        Silence is not a resolution.</li>
      <li>A verified correction updates the source row, all mechanically derived
        counts, generated pages, and the revision history in one reviewable change.
        The report is credited in the affected row where consent permits.</li>
      <li>If evidence remains ambiguous, the row is weakened to an explicit
        ambiguity rather than retained by confidence or rewritten criteria.</li>
    </ol>
  </section>
  <section class="zone" id="revision-history" aria-labelledby="history-h">
    <h2 id="history-h">Public revision history</h2>
    <p class="zone-intro">The full record is also embedded beside the census rows;
      this route exists so a citation, post, or correction request always has one
      stable destination.</p>
    <ul class="manual-list" data-fact-state="historical">{entries}</ul>
  </section>
  <section class="zone" aria-labelledby="scope-h">
    <h2 id="scope-h">What a correction can change</h2>
    <p class="zone-intro">A correction can change a row, a count, or the scope of a
      claim. It cannot be used to retroactively narrow a criterion merely to preserve
      a preferred result. The census's claim envelope and forbidden-rescue rules are
      public in <a class="u" href="/ledger/#MC-001">MC-001</a>.</p>
  </section>
</main>''' + PAGE_FOOT


def render_demonstration() -> str:
    """The row, demonstrated — rendered from MC-002's expected block in
    claims.yaml, the same block the reproduction script asserts, so the
    page and the executed computation cannot diverge."""
    import yaml
    registry = yaml.safe_load((ROOT / "claims.yaml").read_text())
    mc = next((c for c in registry["claims"] if c["id"] == "MC-002"), None)
    if mc is None:
        return ""
    e = mc["expected"]
    n = e["n_harmful"]
    guards = {"lakera_guard": "Lakera Guard", "prompt_guard": "Prompt Guard",
              "langkit": "LangKit", "nemo": "NeMo Guardrails",
              "llm_guard": "LLM Guard"}
    # The independence plug-in has exactly one implementation in this repo.
    product = identification.independence_plugin(
        [(n - e["per_guard_catches"][key]) / n for key in guards])
    ratio = (e["all_miss"] / n) / product
    rows = "".join(
        f'<tr><th scope="row">{esc(name)}</th>'
        f'<td>{e["per_guard_catches"][key] / n:.1%} '
        f'({e["per_guard_catches"][key]} / {n})</td></tr>'
        for key, name in guards.items())
    return f'''
  <section class="zone" id="demonstration" aria-labelledby="demo-h">
    <h2 id="demo-h">The row, demonstrated on public data</h2>
    <p class="zone-intro">BELLS's 2025 misuse-detection study released 170 prompts
      with eleven systems' decisions as columns. The census records a second aligned
      per-item release — Multimodal Safeguard Bench — whose three-guard
      adapter-bit ORs, all-zero counts, leave-one-out bit ORs, and full
      native-label pattern tables are likewise computed from the bound files and registered as
      <a class="u" href="/ledger/#MC-004">claim MC-004</a>
      (<span class="mono">python scripts/reanalyze_msbench.py</span>). This page
      demonstrates the BELLS-specific arithmetic because MC-002 binds this exact file
      and its five specialized supervisors:</p>
    <div class="fig-scroll" tabindex="0" role="region" aria-label="BELLS demonstration table, scrollable">
    <table class="census-table demo-table">
      <caption class="sr-only">The minimum joint disclosure computed on the released
        BELLS subset: per-guard catch rates, union, and all-miss over {n} harmful
        prompts.</caption>
      <thead><tr><th scope="col">System</th><th scope="col">Catch rate, {n} harmful prompts</th></tr></thead>
      <tbody>
        {rows}
        <tr class="demo-union"><th scope="row">Any guard — union</th>
          <td>{e["union_detection"] / n:.1%} ({e["union_detection"]} / {n})</td></tr>
        <tr class="demo-allmiss"><th scope="row">No guard — all-miss</th>
          <td>{e["all_miss"] / n:.1%} ({e["all_miss"]} / {n})</td></tr>
      </tbody>
    </table>
    </div>
    <p class="zone-intro" style="margin-top:1.1rem">The product of the five individual miss
      rates is {product:.1%}: an independence plug-in reference. The
      release-recomputed all-miss in this static OR aggregation is
      {e["all_miss"] / n:.1%}: about {ratio:.1f}× that plug-in on this subset.
      The same union flags {e["benign_union_flagged"]} of the {e["n_benign"]} benign
      prompts — a separate static benign-union column needed to interpret this
      aggregation, not a deployment utility assessment.</p>
    <div class="precond"><strong>Scope, stated before anyone asks:</strong> the released 170
      prompts are an author-selected subset (of 990 non-adversarial prompts; the study's
      ~4,165 adversarial prompts have no per-item release) under an unstated selection rule —
      so these are counting facts about exactly that file, not estimates of any system's true
      rate, and no interval is offered because the sampled population is undefined. The full
      envelope, falsifier, and forbidden rescues:
      <a class="u" href="/ledger/#MC-002">claim MC-002</a>. Reproduce it:
      <span class="mono">python scripts/reanalyze_bells_subset.py</span> — the file is
      hash-verified before a single count is taken.</div>
  </section>'''


def render_mjgd_v1_packet() -> str:
    """Render the machine-readable examples from validated fixture results."""
    labels = {
        validate_mjgd.STATUS_RECOMPUTABLE:
            ("recomputed static", "Complete binary full-exposure outcomes; every printed "
             "positive and benign count is recomputed."),
        validate_mjgd.STATUS_AGGREGATE_PATTERNS:
            ("recomputed aggregate patterns", "A complete controlled aggregate-pattern "
             "table; positive static results are recomputed without item identities."),
        validate_mjgd.STATUS_NOT_IDENTIFIED:
            ("not identified", "Marginals only; the exact finite all-miss identified set is "
             "shown instead of inventing a realized joint result."),
        validate_mjgd.STATUS_HOLD_ROUTE:
            ("held: route declaration", "A routed or gated declaration is held, not "
             "collapsed into static full-exposure arithmetic."),
        validate_mjgd.STATUS_HOLD_MISSING:
            ("held: missing data", "An explicit timeout, error, or non-exposure cell is held "
             "rather than silently scored."),
    }
    fixtures = validate_mjgd.validate_fixtures()
    rows = []
    raw_result = None
    for path, result in fixtures:
        label, explanation = labels[result["status"]]
        if result["status"] == validate_mjgd.STATUS_RECOMPUTABLE:
            raw_result = result
        rows.append(
            f"<tr><th scope=\"row\">{esc(path.name)}</th><td class=\"mono\">"
            f"{esc(label)}</td><td>{esc(explanation)}</td></tr>"
        )
    if raw_result is None:
        raise RuntimeError("MJGD fixture suite has no recomputable static example")
    positive = raw_result["positive"]
    return f'''
  <section class="zone" id="machine-readable" aria-labelledby="packet-h">
    <h2 id="packet-h">Machine-readable MJGD v1</h2>
    <p class="zone-intro">The human template above now has a small
      <a class="u" href="/schemas/mjgd-v1.schema.json">structural JSON schema</a>,
      <a class="u" href="/docs/MJGD_V1.md">implementation notes</a>, and a
      standard-library validator. Use the validator for semantic conformance:
      it checks declared evidence boundaries and arithmetic, not safety,
      calibration, route risk, or adaptive robustness.</p>
    <div class="fig-scroll" tabindex="0" role="region" aria-label="Disclosure comparison table, scrollable">
    <table class="census-table">
      <caption class="sr-only">MJGD v1 conformance fixtures and their validated states</caption>
      <thead><tr><th scope="col">Illustrative fixture</th><th scope="col">Validator state</th><th scope="col">What that state means</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    </div>
    <div class="precond"><strong>One recomputed fixture, not a benchmark result:</strong>
      4 positives, A catches {positive["per_system_catches"]["a"]}, B catches
      {positive["per_system_catches"]["b"]}, any guard catches
      {positive["union_detection"]}, and all guards miss {positive["all_miss"]}.
      Its benign union is {raw_result["benign"]["union_flags"]} of
      {raw_result["benign"]["denominator"]}. These are synthetic fixture counts,
      included to make the contract replayable rather than to characterize any
      deployed system.</div>
    <pre tabindex="0" role="region" aria-label="Validator commands, scrollable">python scripts/validate_mjgd.py --test      # five fixture states + refusal tests
python scripts/validate_mjgd.py --fixtures  # inspect every committed fixture</pre>
  </section>'''


def render_disclosure(data: dict) -> str:
    census = data["census"]
    counts = verify_census.compute_counts(data)
    title = "Minimum Joint Guardrail Disclosure — Pranav Bhave"
    desc = ("A proposed reporting protocol small enough to paste into a results table: "
            "union detection, all-miss rate, denominator, and event "
            "definition — what to publish before characterizing a stack.")
    items = [
        ("Population and denominator",
         "What set of items, how many, and where they came from. Every joint "
         "statistic below is a fraction of this set."),
        ("Event definition",
         "What counts as a positive — the thing a guard should catch — stated "
         "once, identically, for every system."),
        ("Per-guard configuration",
         "Version, threshold, and settings for each guard. A threshold moved "
         "between guards silently changes what a comparison means."),
        ("Same-items confirmation",
         "An explicit statement that every guard was evaluated on the same "
         "items. Same benchmark name is not the same item set."),
        ("Full exposure",
         "Every guard saw every applicable item. If an earlier guard's block "
         "gated later guards, say so — gated and ungated numbers answer "
         "different questions."),
        ("Per-guard counts",
         "Catches among positives and false positives among negatives, as "
         "counts with denominators, not only as rates."),
        ("Union detection",
         "Items caught by at least one guard, among positives on the stated "
         "full-exposure item set. It is unrecoverable from marginals."),
        ("All-miss rate",
         "Items caught by no guard, among positives on that same static item "
         "set. It equals 100% minus union detection; it is not, by itself, "
         "terminal deployment risk under routing, gating, or adaptation."),
        ("Residual coverage",
         "For each added guard: what it catches among the items the preceding "
         "set missed. This is the measured value of adding the guard."),
        ("Intersections",
         "Pairwise (and higher-order, where feasible) overlaps of catches or "
         "misses. Pairwise alone does not determine the higher-order "
         "structure; it still constrains it."),
        ("Uncertainty",
         "Intervals for the joint statistics, not only the marginals. A union "
         "estimate without uncertainty invites overreading."),
        ("Missingness",
         "Errors, refusals, and timeouts, and how each was scored. A timeout "
         "scored as a catch is a decision, not an accident."),
        ("Order semantics",
         "For sequential stacks: the order, and what a block at stage k means "
         "for the stages after it."),
        ("Per-item release",
         "One row per item with each guard's decision, when license and "
         "safety permit. This single artifact makes every statistic above "
         "recomputable by anyone."),
    ]
    items_html = "".join(
        f"<li><strong>{esc(name)}</strong><p>{esc(text)}</p></li>"
        for name, text in items)
    template = '''| System                  | Catch rate on the positive set |
|-------------------------|--------------------------------|
| Guard A (version, thr.) | 91.0%  (910 / 1,000)           |
| Guard B (version, thr.) | 88.0%  (880 / 1,000)           |
| Any guard — union       | __._%  (___ / 1,000)           |
| No guard — all-miss     | __._%  (___ / 1,000)           |

Denominator: 1,000 positives, defined as <event definition>.
Every guard scored every item independently (no gating).
Errors/timeouts: <n>, scored as <policy>.'''
    head = page_head(title, desc, "/missing-column/disclosure/", DISCLOSURE_CSS,
                     breadcrumbs(("The record", "/"),
                                 ("The Missing Column", "/missing-column/"),
                                 ("Minimum disclosure", None)))
    return head + f'''
<div class="class-bar mono">
  <div class="container">
    <span><b>Minimum Joint Guardrail Disclosure</b> — working disclosure schema, v1</span>
    <span>maintained beside the <a class="u" href="/missing-column/">census</a> · criteria v{esc(census["criteria_version"])} wording locked {esc(census["frozen_as_of"])}</span>
  </div>
</div>
<header class="page">
  <div class="container">
    <h1>The missing row, specified</h1>
    <p class="intro">"Publish the stack" compresses to one table row — union detection and
      all-miss over the same items — but the row is only meaningful with its denominator,
      event definition, and alignment conditions attached. This page is the exact
      proposal: fourteen components, a paste-in template, and a tested reference
      implementation. It is a working schema maintained by one person, with no external
      use recorded so far; the census records the day that changes.</p>
  </div>
</header>
<main class="container" id="main">
  {render_ladder_fig()}

  <div class="precond"><strong>Turn this draft into a reviewable packet:</strong> the
    browser-local <a class="u" href="/stack-study/">Stack Study Preflight</a> records the
    system, observation mode, denominator, and static aggregate checks together. It computes
    only declared full-exposure static evidence; deployed routes and adaptive tests remain
    separate protocol objects.</div>

  <section class="zone" id="components" aria-labelledby="comp-h">
    <h2 id="comp-h">The fourteen components</h2>
    <p class="zone-intro">Components 1–6 make the marginals interpretable; most careful
      evaluations already publish them. Components 7–9 are the missing column. 10–13
      make it trustworthy. 14 makes it reproducible.</p>
    <ol class="disc-list">{items_html}</ol>
  </section>

  <section class="zone tmpl" id="template" aria-labelledby="tmpl-h">
    <h2 id="tmpl-h">The paste-in row</h2>
    <p class="zone-intro">For a results table that already lists per-guard rates, the
      minimum viable disclosure is two added rows and three lines of caption:</p>
    <pre tabindex="0" role="region" aria-label="Machine-readable disclosure template, scrollable">{esc(template)}</pre>
    <div class="precond"><strong>The row is meaningful only if:</strong> the denominator and
      event definition are stated; every guard scored the same items; every guard scored
      every item (or the gating is declared as the object of measurement); and
      missingness is scored by a stated policy. Absent those, a union number is not
      evidence about the stack.</div>
  </section>

  {render_demonstration()}
{render_mjgd_v1_packet()}

  <section class="zone" id="ask" aria-labelledby="ask-h">
    <h2 id="ask-h">The ask, for benchmark authors</h2>
    <div class="ask"><p>You evaluated multiple guardrails on a common benchmark. Did you
      retain one binary decision per item for every system? If so, would you consider
      publishing the union detection rate and the corresponding all-miss rate, together
      with the denominator and event definition? Those two rows identify static all-miss
      for the declared full-exposure evaluation without assuming independence — and I will gladly supply the
      calculation or a small reporting patch:
      <a class="u" href="mailto:bhavepranavwork@gmail.com">bhavepranavwork@gmail.com</a>.</p></div>
  </section>

  <section class="zone" id="reference" aria-labelledby="ref-h">
    <h2 id="ref-h">Reference implementation</h2>
    <p class="zone-intro"><a class="u" href="https://github.com/Cubits11/cubits11.github.io/blob/main/scripts/mjgd_reference.py">scripts/mjgd_reference.py</a>
      computes every static component above from one decision per item per guard — union,
      all-miss, residual coverage in stack order, and pairwise intersections — and
      asserts its own identities (union + all-miss = denominator; residual coverage
      telescopes to the union; intersections respect their feasibility bounds) against
      synthetic fixtures in CI. It is ~a hundred lines, and it is the entire cost of the
      disclosure when per-item decisions were retained.</p>
    <p class="zone-intro" style="margin-top:.8rem">What this page does not claim: that any
      organization has adopted this schema; that the missing statistics, once measured,
      would show strong dependence; or that disclosure alone makes a stack safe. The
      <a class="u" href="/missing-column/">census</a> tracks the first; measurement — not
      assumption — settles the second; nothing settles the third.</p>
  </section>
</main>''' + PAGE_FOOT


def render_reproduce(data: dict) -> str:
    """The stranger reproduction page for MC-004 — one claim, one receipt,
    one non-claim, one reproduction action. Hashes and the bound commit come
    from reanalyze_msbench itself and the numerals from MC-004's expected
    block, so this page cannot disagree with the script or the registry
    without failing a drift check."""
    import yaml
    registry = yaml.safe_load((ROOT / "claims.yaml").read_text())
    mc = next((c for c in registry["claims"] if c["id"] == "MC-004"), None)
    if mc is None:
        return ""
    e = mc["expected"]
    outcome_ledger = outcomes.load()
    qualified_outcomes = outcomes.qualified_total(outcome_ledger)
    technical_interactions = outcomes.technical_interactions(outcome_ledger)
    bt, bi = e["benign_text"], e["benign_image"]
    ht, hi = e["harmful_text"], e["harmful_image"]
    lg3v_benign = bi["per_guard"]["llama_guard_3_vision"]
    commit = reanalyze_msbench.BOUND_COMMIT
    hash_rows = "".join(
        f'<tr><th scope="row" class="mono" style="font-size:.72rem">{esc(name)}</th>'
        f'<td class="mono" style="font-size:.68rem;word-break:break-all">{esc(digest)}</td></tr>'
        for name, digest in reanalyze_msbench.SHA256.items())
    issue_url = ("https://github.com/Cubits11/cubits11.github.io/issues/new"
                 "?template=reproduction.yml")
    title = "Reproduce claim MC-004 — a three-guard recomputation"
    desc = ("One command block, eight pinned hashes, the expected output, "
            "and what must fail — reproduce claim MC-004's three-guard "
            "recomputation from released files; match and mismatch both "
            "get credited.")
    head = page_head(
        title, desc, "/missing-column/reproduce/", "", breadcrumbs(
            ("The record", "/"), ("The Missing Column", "/missing-column/"),
            ("Reproduce MC-004", None)))
    pre_style = ("background:var(--surface);border:1px solid var(--line-strong);"
                 "padding:1.1rem 1.2rem;overflow-x:auto;font-family:var(--mono);"
                 "font-size:.78rem;line-height:1.8;color:var(--ink);margin:1.2rem 0 0")
    return head + f'''
<div class="class-bar mono">
  <div class="container">
    <span><b>Reproduce it</b> — claim <a class="u" href="/ledger/#MC-004">MC-004</a></span>
    <span>a recomputation on released files · census counts unchanged</span>
  </div>
</div>
<header class="page">
  <div class="container">
    <h1>Reproduce this recomputation</h1>
    <p class="intro">MC-004 is counting arithmetic on harness-normalized adapter bits
      Multimodal Safeguard Bench already released — not new data, and not a census change: N/M/K stays
      <span data-fact="MC-001.N" data-fact-state="current">{fact_registry.registry()["MC-001.N"]}</span>/{fact_registry.registry()["MC-001.M1"]}/{fact_registry.registry()["MC-001.K"]} and the
      stricter ladder stays 14/12/0. The guards run at native, unmatched operating
      points. The least favorable column comes first: the three-guard bit OR is 1 on
      every one of the {bi["n"]} benign-labelled image items — saturation owed to Llama Guard 3
      Vision's own {lg3v_benign}/{bi["n"]} bit column — and {bt["union"]} of {bt["n"]} benign-
      labelled text items. The harness itself uses a <span class="mono">blocked</span> item
      to suppress target generation, so this static OR is a valid counterfactual
      harness-block computation under a fixed block-on-any rule. No source-defined
      translation makes it a shared-event catch union. This page exists so a stranger
      can check the bounded bit arithmetic in about a minute.</p>
  </div>
</header>
<main class="container" id="main">
  <section class="zone" id="claim" aria-labelledby="claim-h">
    <h2 id="claim-h">The claim, exactly</h2>
    <p class="zone-intro">On the six per-item verdict files of the release's
      <span class="mono">full_run</span> directory at commit
      <span class="mono">{esc(commit[:12])}</span> (hash-verified below), the harness stores
      each guard's native <span class="mono">unsafe</span> label as a Boolean
      <span class="mono">blocked</span> bit. The static OR of those bits is 1 on
      {bi["union"]}/{bi["n"]} benign-labelled image and {bt["union"]}/{bt["n"]} benign-labelled
      text rows, and on {ht["union"]}/{ht["n"]} harmful-labelled text rows
      ({ht["all_miss"]} all-zero rows) and {hi["union"]}/{hi["n"]} harmful-labelled image
      rows. Llama Guard 3 Vision is a multimodal prompt/response classifier;
      ShieldGemma 2 is image-only and its text rows are deterministic passes as released.
      The harness uses a <span class="mono">blocked</span> item to suppress target generation,
      so, under a fixed block-on-any rule, this is a valid counterfactual harness-block
      calculation for these pinned rows. No examined source defines a translation of all
      native predicates to one shared catch event, so it remains a released-bit aggregate,
      not a shared-policy safety result, a deployed stack, or a three-independent-catcher
      result. The full bit-pattern
      tables, leave-one-out bit ORs, scope, falsifier, and forbidden rescues are registered as
      <a class="u" href="/ledger/#MC-004">claim MC-004</a>.</p>
  </section>
  <section class="zone" id="run" aria-labelledby="run-h">
    <h2 id="run-h">Run it</h2>
    <p class="zone-intro">From an empty directory — a POSIX shell with
      <span class="mono">git</span> and Python&nbsp;3.11+ (with its standard
      <span class="mono">venv</span> module). The script downloads the eight pinned
      files from the bound commit and refuses to count anything until every hash
      matches.</p>
    <pre style="{pre_style}">git clone https://github.com/Cubits11/cubits11.github.io.git
cd cubits11.github.io
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/reanalyze_msbench.py</pre>
  </section>
  <section class="zone" id="expect" aria-labelledby="expect-h">
    <h2 id="expect-h">What you should see</h2>
    <p class="zone-intro">Dozens of <span class="mono">ok</span> assertion lines —
      every recomputed quantity that overlaps the release's own printed metrics is
      asserted equal to the printed value — then this summary and exit code 0:</p>
    <pre style="{pre_style}">{esc(reanalyze_msbench.summary_line("benign", "text", bt["union"], bt["n"], bt["all_miss"]))}
{esc(reanalyze_msbench.summary_line("benign", "image", bi["union"], bi["n"], bi["all_miss"]))}
{esc(reanalyze_msbench.summary_line("harmful", "text", ht["union"], ht["n"], ht["all_miss"]))}
{esc(reanalyze_msbench.summary_line("harmful", "image", hi["union"], hi["n"], hi["all_miss"]))}

{esc(reanalyze_msbench.SUCCESS_LINE)}</pre>
  </section>
  <section class="zone" id="must-fail" aria-labelledby="fail-h">
    <h2 id="fail-h">What must fail</h2>
    <p class="zone-intro">A reproduction that cannot fail proves nothing. Save the
      eight files locally, flip one byte of any of them, and re-run offline:</p>
    <pre style="{pre_style}">python scripts/reanalyze_msbench.py --dir path/to/mutated_full_run
FAIL  guard_…jsonl: sha256 …  != recorded …  — the bound artifact changed;
      MC-004 must be re-reviewed, not silently recomputed   (exit code 1)</pre>
    <p class="zone-intro" style="margin-top:.9rem">The same flip smuggled past the hash
      gate trips nine independent count, pattern, and printed-agreement assertions —
      that mutation test is part of the claim's record, not a promise.</p>
  </section>
  <section class="zone" id="pins" aria-labelledby="pins-h">
    <h2 id="pins-h">The eight pinned files</h2>
    <p class="zone-intro">All at
      <a class="u" href="https://github.com/PatrickKollman/Multimodal-Safeguard-Bench/tree/{esc(commit)}/results/full_run">PatrickKollman/Multimodal-Safeguard-Bench@{esc(commit[:12])} ↗</a>
      under <span class="mono">results/full_run/</span> (MIT-licensed upstream; cited
      and hash-verified here, never redistributed).</p>
    <div class="fig-scroll" tabindex="0" role="region" aria-label="Pinned release files and digests, scrollable">
    <table class="census-table">
      <caption class="sr-only">The eight pinned release files and their sha256 digests.</caption>
      <thead><tr><th scope="col">File</th><th scope="col">sha256</th></tr></thead>
      <tbody>{hash_rows}</tbody>
    </table>
    </div>
  </section>
  <section class="zone" id="file-your-run" aria-labelledby="file-h">
    <h2 id="file-h">File your run — match or mismatch</h2>
    <p class="zone-intro">Both outcomes are wanted. A matching run becomes this claim's
      first independent reproduction; a mismatching run is a correction, handled under
      the <a class="u" href="/corrections/">same-day correction policy</a> and credited
      where consent permits. Use the
      <a class="u" href="{issue_url}">reproduction issue form ↗</a> (evidence class:
      <span class="mono">static-reconstruction</span> or <span class="mono">direct-route</span>;
      environment, commit, command, stdout, match or mismatch) or
      <a class="u" href="mailto:bhavepranavwork@gmail.com">email</a>. The project-wide
      <a class="u" href="/distribution/outcomes.yaml">qualified-outcome ledger</a> currently
      records {qualified_outcomes} qualified external outcome{'s' if qualified_outcomes != 1 else ''};
      it also records {technical_interactions} technical interaction{'s' if technical_interactions != 1 else ''},
      which is diagnostic rather than evidence. That public null is not a growth metric. MC-004 has no recorded independent
      reproduction — this page is the standing invitation, not evidence that one exists.</p>
  </section>
  <section class="zone" id="not-claimed" aria-labelledby="nc-h">
    <h2 id="nc-h">Not claimed</h2>
    <ul class="crit-list">
      <li>No shared-event catch statistic: the common <span class="mono">blocked</span> bit
        is a harness normalization of native predicates, and no source-defined
        translation to a single event has been identified.</li>
      <li>No vendor ranking, endorsement, or indictment — the verdicts are at native,
        unmatched operating rules, and no threshold calibration is documented upstream.</li>
      <li>No population estimate and no interval; the items are the release's own
        construction, and the counts are about exactly these bytes.</li>
      <li>Not an observed deployed stack; the OR aggregation is arithmetic, not a
        deployment.</li>
      <li>The harmful-image {hi["union"]}/{hi["n"]} bit-OR count is a fact about these
        {hi["n"]} released items, not evidence of image-attack safety in
        general — and the release's own changelog documents that ShieldGemma 2's image
        scores are sensitive to the text-rendering stack.</li>
      <li>A recomputation on released files: it changes no census count and adds no
        new measurement.</li>
    </ul>
  </section>
</main>''' + PAGE_FOOT


def main() -> int:
    data = verify_census.load()
    outputs = {
        ROOT / "missing-column" / "index.html": render_landing(data),
        ROOT / "missing-column" / "disclosure" / "index.html":
            render_disclosure(data),
        ROOT / "missing-column" / "reproduce" / "index.html":
            render_reproduce(data),
        ROOT / "corrections" / "index.html": render_corrections(data),
    }
    if "--check" in sys.argv:
        for target, out in outputs.items():
            current = target.read_text() if target.exists() else ""
            if current != out:
                rel = target.relative_to(ROOT)
                print(f"DRIFT: {rel} does not match what census.yaml generates.")
                print("Run: python scripts/generate_missing_column.py")
                return 1
        print(f"ok    {len(outputs)} missing-column pages match the census "
              f"(generated, no drift)")
        return 0
    for target, out in outputs.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(out)
        print(f"wrote {target.relative_to(ROOT)} ({len(out)} bytes) from census.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
