# Receipt protocol

Every outbound post is a receipt or it is not sent. Five parts, in this order,
because a reader who stops after part two must still have been told the boundary.

1. **Claim** — one falsifiable sentence.
2. **Scope boundary** — what the claim is *not*. Stated in the post, not in a reply.
3. **Source** — the pinned artifact, at a commit.
4. **One-command reproduction** — a stranger can reach the number without asking.
5. **Correction route** — where to tell us we are wrong.

No hashtags. No thread-bait. No "🧵". The card carries the numbers; the text
carries the boundary.

---

## Drafted post — MC-004 degeneracy · NOT SENT

> A public 3-guard safety release catches 200/200 harmful images.
> It also flags 250/250 benign images.
>
> Same static OR. One guard blocks every image, so the union blocks every
> image — the other two guards are genuinely good (J = 0.66, 0.78) and cannot
> change the result.
>
> Per-guard metrics obscure it: the release publishes
> detection_recall_image = 1.0 and pools over-refusal across modalities to
> 0.55. Split per modality it is 1.00.
>
> Static OR on released per-item verdicts. Not deployed-route safety.
> 8 pinned files, one command:
> https://cubits11.github.io/missing-column/reproduce/

Card: `assets/img/og-mc004-degeneracy.png` — the two numbers, not the generic
missing-column mark.

### Precision notes that must survive editing

- The **3-guard static OR is our computation** from the released per-item
  verdicts. The release itself publishes 2-guard ensembles; its `lg4_lg3v` row
  reports `detection_recall_image = 1.0` with over-refusal pooled at `0.564`.
  Do not imply the release printed the 3-guard union.
- `250/250 flagged` is over-refusal on benign items, not a detection failure.
  Saying "flagged" rather than "caught" is load-bearing.
- The release also contains a **good** configuration —
  `lg4_sg2_modality_routed`, image recall 0.97 at over-refusal 0.148. The post
  is about a reporting gap, not about bad work. Any framing that reads as
  "this benchmark is bad" is wrong and must be corrected.
- Never write "standard" for the proposed reporting protocol. No adoption is
  recorded.

---

## Reply policy

Targeted computation, not volume. A reply is worth sending only if it carries
one of:

- a number the thread does not have, computed from a source the thread cites;
- a denominator the thread is missing;
- a primary source that settles a disputed claim;
- a counterexample;
- a correction to something we published.

Never: "great point", an unrequested link to the site, or any job ask in a
first interaction.

**Stop rule.** If 12 technical interactions produce no qualified engagement
(defined below), stop replying and move the effort to upstream contributions
and direct author outreach. Attention is not the signal; it is the diagnostic.
