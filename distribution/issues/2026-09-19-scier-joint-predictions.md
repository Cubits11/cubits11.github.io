# Upstream ask — SciER per-item predictions

Status: **PREPARED, not sent.** Source: `distribution/dossiers/scier-2024.md`,
the ask verbatim, plus one pinned link. Sender: the owner. This is an upstream
tracker, so none of this repository's templates apply; the URL prefills title
and body.

This is the **only** one of the twenty-five Temple contacts researched on
2026-09-19 whose public artifact supports this programme's canonical ask. The
reasoning, and the four that do not, are in
`distribution/TEMPLE-2026-09-19.md`.

One click opens the new-issue form on `TUDMLab/SciER` with the message below:

https://github.com/TUDMLab/SciER/issues/new?title=Per-item%20predictions%20for%20PURE%20%2F%20PL-Marker%20%2F%20HGERE%20on%20the%20released%20test%20split&body=Thank%20you%20for%20releasing%20SciER%20as%20full-text%20annotations%20rather%20than%20a%20sampled%20subset.%0A%0AAt%20commit%20%60db347813de379eb200e0813bbfee350d67e7c701%60%2C%20%60SciER%2FLLM%2Ftest.jsonl%60%20holds%20854%20sentences%20across%2010%20documents%20with%202%2C948%20entity%20mentions%20%28Method%201%2C890%2C%20Task%20688%2C%20Dataset%20370%29%2C%20and%20%60test_ood.jsonl%60%20holds%20580%20sentences%20across%206%20documents%20with%201%2C295%20mentions.%20This%20script%20downloads%20both%20files%20at%20that%20commit%2C%20checks%20their%20SHA-256%2C%20and%20recomputes%20the%20counts%3A%20https%3A%2F%2Fgithub.com%2FCubits11%2Fcubits11.github.io%2Fblob%2F723ec1bd0851ed89e08420362c0482c2e61507d1%2Fscripts%2Freanalyze_scier_testset.py%0A%0AThe%20paper%20reports%20PURE%2C%20PL-Marker%20and%20HGERE%20on%20these%20splits.%20From%20three%20per-model%20scores%20alone%2C%20the%20number%20of%20entity%20mentions%20that%20all%20three%20missed%20is%20bounded%20but%20not%20determined.%20It%20is%20a%20different%20quantity%20from%20any%20of%20the%20three%2C%20and%20it%20is%20the%20one%20that%20says%20how%20much%20headroom%20an%20ensemble%20of%20them%20actually%20has.%0A%0AWere%20the%20per-item%20predictions%20retained%3F%20Three%20id-keyed%20prediction%20files%20over%20the%20released%20test%20split%20would%20make%20that%20count%20exact%2C%20and%20would%20need%20spans%20only%20%E2%80%94%20no%20scores%2C%20no%20weights.%20If%20re-running%20is%20not%20worth%20it%2C%20the%20smallest%20useful%20answer%20is%20one%20integer%3A%20of%20the%202%2C948%20mentions%20in%20%60test.jsonl%60%2C%20how%20many%20were%20recalled%20by%20none%20of%20the%20three.%0A%0AI%20report%20the%20counts%20above%20only%20as%20counts%20on%20these%20released%20files%2C%20not%20as%20an%20evaluation%20of%20any%20extractor%20and%20not%20as%20an%20estimate%20for%20any%20other%20corpus.%20If%20I%20have%20misread%20what%20the%20repository%20publishes%2C%20a%20correction%20is%20just%20as%20useful.

## Gate

- **Budget.** This spends 1 of the 8 technical interactions remaining under
  `distribution/outcomes.yaml` → `stop_rule` (4 of 12 spent, 0 qualified). It
  is the same *kind* of ask as the four already spent — a maintainer who holds
  per-item outcomes is asked to release or compute the joint — so it does not
  change a second variable before the rule fires.
- **Scope.** SciER is scientific information extraction, not a guardrail
  stack. Sending this does **not** by itself add a census row; adding one is a
  separate owner decision recorded in `distribution/TEMPLE-2026-09-19.md`.
- **Duplicate check: OUTSTANDING.** `github.com` HTML was not reachable for
  out-of-scope repositories from the session that prepared this (403 at the
  egress proxy), so the tracker's existing issues were never inspected. Read
  them in the browser before sending, as the GuardBench draft's check was
  done.
- **Repository conventions.** Check for contributing guidelines or an issue
  template at send time and follow them over this draft.
- Re-derive every numeral at the dispatch commit
  (`python3 scripts/reanalyze_scier_testset.py` exits 0 first).
- After sending, record the permalink and UTC time in
  `distribution/dispatch-log.yaml`, and add the interaction to
  `distribution/outcomes.yaml` → `technical_interaction_log`, as the BELLS
  entry does. Never invent a dispatch date.

## Adjudication, declared before sending

- On a substantive response: verify the integer or the released predictions
  against the pinned split before any outcome credit. A release is
  `paired_outcome_releases`; a correction to the dossier's reading is
  `source_corrections`. Neither is credited until inspected under
  `distribution/EXTERNAL_EVENTS.md`.
- On silence: retain `NO_OBSERVED_RESPONSE`. Do not duplicate the issue and do
  not nudge before T+14d.
- At most one follow-up, and only the one-integer sentence.

## Message as prefilled

Title: Per-item predictions for PURE / PL-Marker / HGERE on the released test split

```
Thank you for releasing SciER as full-text annotations rather than a sampled subset.

At commit `db347813de379eb200e0813bbfee350d67e7c701`, `SciER/LLM/test.jsonl` holds 854 sentences across 10 documents with 2,948 entity mentions (Method 1,890, Task 688, Dataset 370), and `test_ood.jsonl` holds 580 sentences across 6 documents with 1,295 mentions. This script downloads both files at that commit, checks their SHA-256, and recomputes the counts: https://github.com/Cubits11/cubits11.github.io/blob/723ec1bd0851ed89e08420362c0482c2e61507d1/scripts/reanalyze_scier_testset.py

The paper reports PURE, PL-Marker and HGERE on these splits. From three per-model scores alone, the number of entity mentions that all three missed is bounded but not determined. It is a different quantity from any of the three, and it is the one that says how much headroom an ensemble of them actually has.

Were the per-item predictions retained? Three id-keyed prediction files over the released test split would make that count exact, and would need spans only — no scores, no weights. If re-running is not worth it, the smallest useful answer is one integer: of the 2,948 mentions in `test.jsonl`, how many were recalled by none of the three.

I report the counts above only as counts on these released files, not as an evaluation of any extractor and not as an estimate for any other corpus. If I have misread what the repository publishes, a correction is just as useful.
```

## What this is not

- Not sent. Nothing here dispatches anything; the owner's browser does.
- Not a claim. No entry in `claims.yaml` binds these counts, and no census row
  exists for SciER.
- Not a measurement of composition. No prediction file exists to measure; the
  script counts denominators and names the integer it cannot compute.
- Not an evaluation of any extractor, and not an estimate for any other
  corpus.
- A reply, release or merge is a qualified outcome only after inspection.
