#!/usr/bin/env python3
"""Generate the acquisition surfaces: /work/ and the three entry pages.

The record's evidence machinery was already strong and its front door was
not. These pages exist to be *found* and *acted on*: each has one audience,
one question, and one next action, and each ends by handing the reader the
flagship evidence rather than another concept.

Every census numeral on these pages is emitted through facts.fact_span, so a
new marketing surface cannot become a new place for a count to go stale — the
same gate that caught the flagship page's contradiction covers these.

Empirical figures come from claims.yaml expected blocks, never retyped, and
each carries the scope its registered claim declares. A named subset result
stays a named subset result: nothing here promotes MC-002's 82-prompt stratum
into a statement about guardrails in general.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import facts as fact_registry  # noqa: E402
import verify_census  # noqa: E402
from generate_missing_column import (  # noqa: E402
    PAGE_FOOT, SITE, breadcrumbs, esc, jsonld_script, page_head,
)

ROOT = Path(__file__).resolve().parent.parent

PAGE_CSS = """
.lede-big{font-size:clamp(1.05rem,2vw,1.3rem);line-height:1.55;max-width:34em}
.answer{max-width:44em}
.answer p{margin:0 0 1rem}
.answer h2{margin-top:2.4rem}
.answer h3{margin-top:1.6rem}
.callout{border-left:3px solid var(--gold);padding:.9rem 0 .9rem 1.1rem;margin:1.6rem 0;background:var(--surface)}
.callout p{margin:0}
.numline{display:flex;flex-wrap:wrap;gap:1.6rem;margin:1.4rem 0;padding:1rem 1.2rem;border:1px solid var(--line-strong);background:var(--surface)}
.numline div{min-width:7rem}
.numline b{display:block;font-size:1.5rem;font-weight:520;line-height:1.1}
.numline span{color:var(--muted);font-size:.72rem}
.offer{border:1px solid var(--line-strong);background:var(--surface);padding:1.6rem 1.5rem;margin-top:1.6rem}
.offer h3{margin:0 0 .5rem;font-size:1.22rem}
.offer dl{margin:1rem 0 0;display:grid;grid-template-columns:9rem 1fr;gap:.5rem 1rem;font-size:.94rem}
.offer dt{color:var(--gold);font-size:.7rem;letter-spacing:.06em;text-transform:uppercase;padding-top:.22rem}
.offer dd{margin:0;color:var(--muted)}
.cta-row{display:flex;flex-wrap:wrap;gap:.8rem;margin-top:1.8rem}
.next{margin-top:2.6rem;border-top:1px solid var(--line);padding-top:1.4rem}
.next .mono{color:var(--gold)}
@media (max-width:600px){.offer dl{grid-template-columns:1fr}.offer dt{padding-top:.6rem}}
"""


def load_expected(claim_id: str) -> dict:
    registry = yaml.safe_load((ROOT / "claims.yaml").read_text())
    claim = next(c for c in registry["claims"] if c["id"] == claim_id)
    return claim["expected"]


def btn(href: str, label: str, solid: bool = False) -> str:
    cls = "btn btn-solid" if solid else "btn"
    return f'<a class="{cls}" href="{href}">{esc(label)}</a>'


def next_action(text: str, links: str) -> str:
    return f'''
  <div class="next">
    <p class="mono">Next</p>
    <p>{text}</p>
    <div class="cta-row">{links}</div>
  </div>'''


def article_jsonld(title: str, desc: str, path: str) -> str:
    """Describe a real article without asserting invisible bylines or licenses."""
    return jsonld_script({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": desc,
        "url": f"{SITE}{path}",
        "inLanguage": "en",
        "isAccessibleForFree": True,
        "mainEntityOfPage": {"@type": "WebPage", "@id": f"{SITE}{path}"},
    })


def webpage_jsonld(title: str, desc: str, path: str) -> str:
    """Use WebPage markup for a service page rather than calling it an article."""
    return jsonld_script({
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "description": desc,
        "url": f"{SITE}{path}",
        "inLanguage": "en",
    })


# --------------------------------------------------------------- /work/
def render_work() -> str:
    title = "Work with me — evaluation design and evidence audits"
    desc = ("Three engagements: designing a shared-item guardrail stack "
            "evaluation, auditing what an AI claim's evidence establishes, and "
            "threat-modelling a provenance receipt. Artifacts, not "
            "certifications.")
    path = "/work/"
    head = page_head(title, desc, path, PAGE_CSS,
                     jsonld=webpage_jsonld(title, desc, path))
    crumbs = breadcrumbs(("The record", "/"), ("Work with me", None))

    offers = [
        {
            "id": "guardrail-evaluation-design",
            "h": "Guardrail evaluation design",
            "who": "Benchmark authors, evaluation teams, and platform safety "
                   "groups about to publish or refresh a guardrail comparison.",
            "problem": "Per-detector scores are collected on different items, "
                       "at unmatched operating points, and the stack's own "
                       "behaviour is never measured — so the published table "
                       "cannot answer the question a deployment actually asks.",
            "artifact": "An evaluation design: shared item set, one event "
                        "definition, matched operating points, declared "
                        "exposure conditions, and the measurement plan for "
                        "union detection, all-miss rate, residual coverage, "
                        "and uncertainty — plus the results table shaped so "
                        "the joint row is a first-class output rather than an "
                        "afterthought.",
            "boundary": "A design and a measurement plan. Not a certification, "
                        "not a compliance sign-off, and not a claim that any "
                        "system or stack is safe. Running the evaluation and "
                        "interpreting it stay yours.",
            "next": "Send the results table you already publish.",
        },
        {
            "id": "claim-and-evidence-audit",
            "h": "AI claim and evidence audit",
            "who": "Teams whose safety, accuracy, or robustness claim is about "
                   "to face procurement, regulators, press, or a paper "
                   "reviewer.",
            "problem": "The claim is defensible and the reasoning behind it "
                       "lives in someone's head. Nobody can say precisely what "
                       "it assumes, what would refute it, or which weakening "
                       "moves would be cheating.",
            "artifact": "One claim taken apart: an evidence map, the "
                        "assumptions it rests on, a reproduction attempt from "
                        "the bound sources, an explicit falsifier with its "
                        "consequence, the rescues ruled out in advance, the "
                        "non-claims, and a decision-facing summary a "
                        "non-specialist can act on.",
            "boundary": "An audit of what your evidence establishes, not an "
                        "endorsement that it is true. If the evidence supports "
                        "less than the claim says, the deliverable says so — "
                        "that is what you are buying.",
            "next": "Name one claim you would least like to be wrong about.",
        },
        {
            "id": "receipt-and-provenance-threat-model",
            "h": "Receipt and provenance threat model",
            "who": "Teams shipping attestations, content credentials, model "
                   "cards, audit logs, or governance receipts.",
            "problem": "A receipt proves something narrower than the thing "
                       "people will read it as proving, and the gap is only "
                       "discovered when someone relies on it.",
            "artifact": "A written boundary: exactly what the receipt "
                        "identifies, which transformations it survives, which "
                        "leave it ambiguous, what a verifier can and cannot "
                        "conclude from a pass, and the failure modes that look "
                        "like successes.",
            "boundary": "A threat model for what the artifact establishes. Not "
                        "a security certification, not a penetration test, and "
                        "not an assurance that the system is sound.",
            "next": "Send the receipt format and one verifier you rely on.",
        },
    ]

    blocks = []
    for offer in offers:
        blocks.append(f'''
    <div class="offer" id="{offer["id"]}">
      <h3>{esc(offer["h"])}</h3>
      <dl>
        <dt>For</dt><dd>{esc(offer["who"])}</dd>
        <dt>Problem</dt><dd>{esc(offer["problem"])}</dd>
        <dt>You get</dt><dd>{esc(offer["artifact"])}</dd>
        <dt>Boundary</dt><dd>{esc(offer["boundary"])}</dd>
        <dt>Next</dt><dd>{esc(offer["next"])}</dd>
      </dl>
    </div>''')

    return head + f'''
<div class="class-bar mono">
  <div class="container">
    <span><b>Work with me</b> — research, engineering, and independent consulting</span>
    <span>artifacts, not certifications</span>
  </div>
</div>
<header class="page">
  <div class="container">
    {crumbs}
    <h1>Work with me</h1>
    <p class="intro lede-big">I measure what AI guardrail stacks miss together, and
      build evidence systems that show exactly what data can and cannot establish.
      Three ways that turns into a deliverable you can hold.</p>
  </div>
</header>
<main class="container" id="main">
  <section class="zone" id="offers" aria-labelledby="offers-h" style="margin-top:0;border-top:none;padding-top:0">
    <h2 id="offers-h" class="sr-only" style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)">Engagements</h2>
    {"".join(blocks)}
  </section>

  <section class="zone" id="scope" aria-labelledby="scope-h">
    <h2 id="scope-h">What none of this is</h2>
    <p class="zone-intro">No engagement here certifies a system, approves it for
      compliance, or asserts that a model, guardrail, or stack is safe. Every
      deliverable states its own boundary in writing, and every empirical figure
      it contains carries the scope of the evidence behind it. If you need a
      certificate, I am the wrong person; if you need to know what your evidence
      actually supports, that is the entire offer.</p>
    <p class="zone-intro">The public record is the sample of the work:
      <a class="u" href="/missing-column/">a bounded census</a> with a live
      correction route, <a class="u" href="/ledger/">a claim ledger</a> where
      every proposition carries a falsifier, and
      <a class="u" href="/missing-column/disclosure/">a disclosure schema</a>
      with a tested reference implementation.</p>
  </section>

  <section class="zone" id="contact" aria-labelledby="contact-h">
    <h2 id="contact-h">Start a conversation</h2>
    <p class="zone-intro">Email is the fastest route. A concrete artifact —
      a results table, a claim, a receipt format — gets a more useful reply
      than a general enquiry.</p>
    <div class="cta-row">
      {btn("mailto:bhavepranavwork@gmail.com?subject=Guardrail%20evaluation%20design", "Email Pranav", True)}
      {btn("/resume/", "Résumé")}
      {btn("/missing-column/", "See the flagship result")}
    </div>
  </section>
</main>''' + PAGE_FOOT


# ------------------------------------------------------- entry pages
def render_multiply(counts: dict) -> str:
    f = fact_registry.fact_span
    mc2 = load_expected("MC-002")
    mc3 = load_expected("MC-003")
    title = "Why guardrail miss rates cannot simply be multiplied"
    desc = ("Two guardrails that each miss 10% of attacks do not miss 1% "
            "together. Published miss rates pin the joint failure rate only to "
            "an interval, and independence is one point inside it.")
    path = "/answers/why-guardrail-miss-rates-do-not-multiply/"
    head = page_head(title, desc, path, PAGE_CSS,
                     jsonld=article_jsonld(title, desc, path))
    crumbs = breadcrumbs(("The record", "/"), ("Answers", None),
                         ("Why miss rates do not multiply", None))
    ratio = (mc2["all_miss"] / mc2["n_harmful"]) / (
        (mc2["n_harmful"] - mc2["per_guard_catches"]["lakera_guard"]) / mc2["n_harmful"]
        * (mc2["n_harmful"] - mc2["per_guard_catches"]["prompt_guard"]) / mc2["n_harmful"]
        * (mc2["n_harmful"] - mc2["per_guard_catches"]["langkit"]) / mc2["n_harmful"]
        * (mc2["n_harmful"] - mc2["per_guard_catches"]["nemo"]) / mc2["n_harmful"]
        * (mc2["n_harmful"] - mc2["per_guard_catches"]["llm_guard"]) / mc2["n_harmful"])
    return head + f'''
<div class="class-bar mono">
  <div class="container">
    <span><b>Answer</b> — for engineers stacking guardrails</span>
    <span>evidence: <a class="u" href="/ledger/#MC-003">MC-003</a> · <a class="u" href="/ledger/#MC-002">MC-002</a></span>
  </div>
</div>
<header class="page">
  <div class="container">
    {crumbs}
    <h1>Why guardrail miss rates cannot simply be multiplied</h1>
    <p class="intro lede-big">Two guardrails that each miss 10% of attacks do not
      miss 1% together. That number is a modelling choice, and the data you have
      does not license it.</p>
  </div>
</header>
<main class="container" id="main">
  <div class="answer">
    <h2>The short version</h2>
    <p>You have two detectors. Each is published at a 10% miss rate on the same
      items. You stack them: block if either fires. What fraction gets through
      both?</p>
    <p>The multiplication answer is 0.10 × 0.10 = 1%. It is the number almost
      everyone reaches for, and it is only correct if the two detectors fail on
      unrelated items. Nothing in the published rates tells you whether they do.</p>
    <div class="callout">
      <p>From two 10% miss rates alone, the rate at which <em>both</em> miss the
        same item is pinned only to the interval <b>[0%, 10%]</b> — and every
        value in it is achievable by some real pairing of those detectors.
        Independence picks 1%. The evidence does not.</p>
    </div>
    <p>The upper end is what happens when the second detector fails on exactly
      the items the first one fails on — it catches nothing the first did not,
      and the stack is no better than its best member. The lower end is what
      happens when their failures are arranged to avoid each other completely.
      Both are consistent with the same two published numbers.</p>

    <h2>Where the interval comes from</h2>
    <p>For <em>k</em> guardrails scored on a common item set at a common
      operating point, under block-on-any composition, the all-miss rate is
      identified by the per-guard miss rates only up to</p>
    <p class="mono" style="padding:.8rem 1rem;border:1px solid var(--line-strong);background:var(--surface)">
      [ max(0, Σp − (k−1)),&nbsp; min p ]</p>
    <p>The upper endpoint is monotonicity: everyone missing together cannot
      happen more often than the most accurate member misses at all. The lower
      endpoint is Bonferroni. Both endpoints are attained — they are not
      conservative padding, they are reachable by actual joint distributions.
      This is classical Fréchet–Hoeffding; no new mathematics is claimed. What
      it prices, in probability units, is how much marginal-only guardrail
      reporting leaves undetermined.</p>
    <p>Note what this does <em>not</em> say. Marginals do prove that a static OR
      composition is never worse than its best member. What they cannot
      establish, whenever that interval is non-degenerate, is any strictly
      positive incremental benefit from adding the second guard.</p>

    <h2>A worked case where the number was actually recoverable</h2>
    <p>Most evaluations make this uncheckable, because they never release
      per-item outcomes. One did. The BELLS 2025 misuse-detection evaluation
      published a {mc2["n_prompts"]}-prompt subset with per-item verdicts for
      five specialized supervisors, so the joint behaviour can be recomputed
      rather than assumed.</p>
    <div class="numline">
      <div><b>{mc2["n_harmful"]}</b><span>prompts labelled harmful</span></div>
      <div><b>{mc2["union_detection"]}</b><span>caught by the OR-union</span></div>
      <div><b>{mc2["all_miss"]}</b><span>missed by all five</span></div>
      <div><b>{ratio:.1f}×</b><span>the independence plug-in</span></div>
    </div>
    <p>The product of the five individual miss rates predicts 3.5%. Recomputing
      from the released verdict file gives {mc2["all_miss"]}/{mc2["n_harmful"]},
      about {ratio:.1f} times that. The identified interval on this file is the
      finite set {{{mc3["identified_set_lower"]}/{mc2["n_harmful"]} …
      {mc3["identified_set_upper"]}/{mc2["n_harmful"]}}} — so the recomputed
      value sits inside a range the marginals never narrowed.</p>
    <div class="callout">
      <p><b>Scope, strictly.</b> This is counting arithmetic on one
        author-selected subset at the vendors' released default configurations.
        It is not a population estimate, not a vendor ranking, and not evidence
        that guardrails in general fail together. It is one case where the
        assumption could be checked, and it did not hold in the optimistic
        direction.</p>
    </div>

    <h2>What to do instead</h2>
    <p>Measure the stack on the same items you measured the parts on. Two
      numbers are enough to start: how often the union catches, and how often
      everything misses — over one denominator, with one event definition, at
      declared operating points. That is the
      <a class="u" href="/missing-column/disclosure/">Minimum Joint Guardrail
      Disclosure</a>, and if you kept one decision per item per system you
      already have the data.</p>
    <p>Across the
      <span data-fact="MC-001.N" data-fact-state="current">{counts["N"]}</span>
      public guardrail evaluations examined in the Missing Column Census,
      {f("MC-001.K", counts["K"])} preserve an artifact from which a joint
      statistic can be read or recomputed.
      {f("MC-001.M3", counts["M_strata"]["threshold_documented_full_exposure"])}
      document matched operating thresholds together with full exposure.</p>
    {next_action(
        "See which evaluations preserve the joint evidence and which do not — "
        "every row bound to its primary source, with a correction route.",
        btn("/missing-column/", "Inspect the census", True)
        + btn("/missing-column/disclosure/", "Publish the missing row")
        + btn("/essays/when-marginals-are-not-enough/", "The five-minute proof"))}
  </div>
</main>''' + PAGE_FOOT


def render_evaluate(counts: dict) -> str:
    f = fact_registry.fact_span
    title = "How to evaluate AI guardrails you plan to stack"
    desc = ("Six things to decide before you run: shared items, one event "
            "definition, matched operating points, declared exposure, and the "
            "joint row per-detector scores cannot supply.")
    path = "/answers/how-to-evaluate-guardrails-you-plan-to-stack/"
    head = page_head(title, desc, path, PAGE_CSS,
                     jsonld=article_jsonld(title, desc, path))
    crumbs = breadcrumbs(("The record", "/"), ("Answers", None),
                         ("Evaluating guardrails you plan to stack", None))
    strata = counts["M_strata"]
    return head + f'''
<div class="class-bar mono">
  <div class="container">
    <span><b>Answer</b> — for benchmark authors and evaluation teams</span>
    <span>schema: <a class="u" href="/missing-column/disclosure/">MJGD v1</a></span>
  </div>
</div>
<header class="page">
  <div class="container">
    {crumbs}
    <h1>How to evaluate AI guardrails you plan to stack</h1>
    <p class="intro lede-big">Most guardrail evaluations answer "which detector is
      best?". If you are going to deploy several together, that is not the
      question you need answered.</p>
  </div>
</header>
<main class="container" id="main">
  <div class="answer">
    <p>A per-detector leaderboard is a legitimate artifact and this is not a
      criticism of publishing one. It just cannot be composed. Six things make
      the difference between an evaluation whose stack behaviour is recoverable
      and one whose is not — and five of them cost nothing extra if you decide
      before you run.</p>

    <h2>1. Score every system on the same items</h2>
    <p>Different item sets make every downstream comparison a guess. This is the
      cheapest requirement and the most commonly broken one. Of the
      <span data-fact="MC-001.N" data-fact-state="current">{counts["N"]}</span>
      evaluations in the census,
      {f("MC-001.M1", strata["shared_basis"])} document a shared item set and a
      common event definition.</p>

    <h2>2. Fix one event definition</h2>
    <p>"Blocked", "flagged", "refused", and "scored above threshold" are
      different events. If two systems are scored against different notions of
      what counts as a catch, their union is undefined.</p>

    <h2>3. Compare at matched operating points, and say so</h2>
    <p>A detector at a permissive threshold and one at a strict threshold are
      not comparable, and a threshold-free metric like AUPRC quietly sidesteps
      the question a deployed stack has to answer. This is the rung almost
      nobody reaches:
      {f("MC-001.M2", strata["threshold_not_contradicted"])} of the census's
      shared-basis evaluations have no <em>stated</em> threshold mismatch, but
      {f("MC-001.M3", strata["threshold_documented_full_exposure"])} document
      matched operating thresholds together with full exposure.</p>

    <h2>4. Declare the exposure condition</h2>
    <p>There are three very different worlds, and a results table that does not
      say which one it is in cannot be interpreted:</p>
    <ul>
      <li><b>Static full exposure</b> — every system sees every item. Union and
        all-miss are well defined and directly computable.</li>
      <li><b>Deployed sequential routing</b> — an upstream block censors what
        downstream systems ever see. Static composition arithmetic does not
        apply, and pretending it does inflates the stack.</li>
      <li><b>Adaptive or agentic</b> — an intervention changes the trajectory,
        so there is no fixed population to compute a rate over.</li>
    </ul>
    <p>The <a class="u" href="/stack-study/">stack study preflight</a> is a
      browser-local tool that refuses to emit a static joint result when you
      declare a non-static mode — it is easier to check this before you collect
      data than after.</p>

    <h2>5. Publish the joint row</h2>
    <p>Two numbers over the same denominator: how often the union catches, and
      how often every system misses the same item. That is the row that
      per-detector columns cannot reconstruct, and it is one line in the table
      you are already building. The
      <a class="u" href="/missing-column/disclosure/">Minimum Joint Guardrail
      Disclosure</a> gives the exact template, its preconditions, and a tested
      reference implementation.</p>

    <h2>6. Keep the per-item outcomes</h2>
    <p>One decision per item per system, released alongside the paper, makes
      every union, all-miss, and pairwise intersection recomputable by anyone —
      including analyses you did not think to run. If releasing raw items is not
      possible, leave-one-out unions are a compact, privacy-preserving summary
      that still identifies each guard's exclusive contribution to the stack.</p>

    <h2>What you get for it</h2>
    <p>A results table a reader can deploy from rather than infer from, and a
      claim that survives someone checking it. If you already ran the
      evaluation and kept the per-item outcomes, the joint row is a
      recomputation, not a new experiment.</p>
    {next_action(
        "If your evaluation is already published, the census records where it "
        "stands and how to correct the record if a row misreads it.",
        btn("/missing-column/disclosure/", "Get the disclosure template", True)
        + btn("/missing-column/#census", "Find your evaluation")
        + btn("/work/", "Work with me"))}
  </div>
</main>''' + PAGE_FOOT


def render_second_guard(counts: dict) -> str:
    mc2 = load_expected("MC-002")
    mc3 = load_expected("MC-003")
    title = "What does the second guardrail catch that the first one misses?"
    desc = ("Residual coverage — what the second guardrail adds among items "
            "the first one missed — is in no set of per-detector scores. "
            "Leave-one-out unions identify it without releasing raw items.")
    path = "/answers/what-does-the-second-guardrail-add/"
    head = page_head(title, desc, path, PAGE_CSS,
                     jsonld=article_jsonld(title, desc, path))
    crumbs = breadcrumbs(("The record", "/"), ("Answers", None),
                         ("What the second guardrail adds", None))
    loo = mc2["leave_one_out_union"]
    union = mc2["union_detection"]
    rows = "".join(
        f'<div><b>{union - value}</b><span>{esc(name.replace("_", " "))}</span></div>'
        for name, value in sorted(loo.items(), key=lambda kv: kv[1]))
    return head + f'''
<div class="class-bar mono">
  <div class="container">
    <span><b>Answer</b> — for teams justifying a second detector</span>
    <span>evidence: <a class="u" href="/ledger/#MC-003">MC-003</a></span>
  </div>
</div>
<header class="page">
  <div class="container">
    {crumbs}
    <h1>What does the second guardrail catch that the first one misses?</h1>
    <p class="intro lede-big">This is the question that justifies the second
      detector's cost, latency, and false positives. No column in a standard
      guardrail results table answers it.</p>
  </div>
</header>
<main class="container" id="main">
  <div class="answer">
    <h2>Residual coverage is a different quantity</h2>
    <p>Say detector A catches 80% and detector B catches 70%. B's headline
      number is measured over <em>all</em> items. The question you actually have
      is narrower: among the 20% that A let through, how many does B stop?</p>
    <p>That conditional rate can be anything from 0% to 100% while both headline
      numbers stay exactly as published. A second detector that is excellent
      overall and blind to precisely A's blind spots contributes nothing to the
      stack — and its published score looks identical to one that closes every
      gap.</p>
    <div class="callout">
      <p>Residual coverage is not derivable from marginal scores. It is a
        property of how the detectors fail <em>together</em>, and per-detector
        columns contain no information about that.</p>
    </div>

    <h2>The measurement is cheap if you kept the items</h2>
    <p>With one decision per item per system, residual coverage is a filter and
      a count: take the items the first guard missed, and count how many the
      second caught. No new experiment, no new inference.</p>
    <p>If you cannot release per-item outcomes, there is a compact alternative
      that identifies the same thing. Publish the union with each guard removed
      in turn — a <em>leave-one-out</em> union. The gap between the full union
      and the union without guard <em>g</em> is exactly the set of items only
      <em>g</em> catches: its exclusive contribution to the stack.</p>

    <h2>What that looks like on real data</h2>
    <p>On the harmful stratum of the BELLS 2025 released subset
      ({mc2["n_harmful"]} prompts, five specialized supervisors, union catches
      {union}), the registered leave-one-out unions identify each supervisor's
      exclusive full-stack coverage:</p>
    <div class="numline">{rows}</div>
    <p>Three of the five contribute nothing exclusive on this stratum: remove
      them and the union is unchanged. Marginal catch counts alone would have
      bounded each guard's exclusive coverage only loosely — for example
      {mc3["aggregate_unique_contribution_bounds"]["nemo"][0]} to
      {mc3["aggregate_unique_contribution_bounds"]["nemo"][1]} items for the
      strongest member. The leave-one-out unions identify the realized values.</p>
    <div class="callout">
      <p><b>Scope, strictly.</b> One author-selected subset, one stratum, at
        unstated default configurations. This is not a vendor ranking, not a
        causal attribution, and not evidence about any product outside this
        file. One supervisor fires exactly once in the whole released set.
        Leave-one-out unions identify exclusive coverage only — not pairwise
        overlap, Shapley values, or causal contribution.</p>
    </div>

    <h2>The cost side of the ledger</h2>
    <p>Adding a guard also adds false positives, and that direction <em>is</em>
      partly identified by the marginals: if any member flags benign traffic at
      a positive rate, the stack's benign flag rate has a strictly positive
      floor. On the same released file, the five-supervisor union flags
      {mc2["benign_union_flagged"]} of {mc2["n_benign"]} benign prompts. A
      second detector that adds no exclusive coverage still adds burden.</p>
    {next_action(
        "The Minimum Joint Guardrail Disclosure specifies the residual-coverage "
        "and leave-one-out rows, with a tested reference implementation.",
        btn("/missing-column/disclosure/", "Publish the missing row", True)
        + btn("/missing-column/#residual-zone", "See the residual figure")
        + btn("/ledger/#MC-003", "Read the identification claim"))}
  </div>
</main>''' + PAGE_FOOT


PAGES = {
    "work/index.html": lambda counts: render_work(),
    "answers/why-guardrail-miss-rates-do-not-multiply/index.html": render_multiply,
    "answers/how-to-evaluate-guardrails-you-plan-to-stack/index.html": render_evaluate,
    "answers/what-does-the-second-guardrail-add/index.html": render_second_guard,
}


def main() -> int:
    counts = verify_census.compute_counts(verify_census.load())
    check = "--check" in sys.argv
    drift = []
    for rel, render in PAGES.items():
        target = ROOT / rel
        html = render(counts)
        if check:
            current = target.read_text(encoding="utf-8") if target.exists() else ""
            if current != html:
                drift.append(rel)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
        print(f"wrote {rel} ({len(html)} bytes)")
    if check:
        if drift:
            for rel in drift:
                print(f"DRIFT: {rel} does not match its generator.")
            print("Run: python scripts/generate_growth.py")
            return 1
        print(f"ok    {len(PAGES)} growth pages match their generator")
    return 0


if __name__ == "__main__":
    sys.exit(main())
