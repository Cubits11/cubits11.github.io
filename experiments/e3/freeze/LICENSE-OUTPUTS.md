# E3 output licence — declared before any row exists

E3's observation rows are a derivative of third-party data and third-party
model weights. This file declares what the outputs are under, and it is written
**before** any row is produced so it cannot be chosen to suit a result.

## What flows in

| input | licence | evidence |
|---|---|---|
| OR-Bench `or-bench-toxic.csv` (harmful, 400 drawn of 655) | **CC-BY-4.0** | dataset card metadata at revision `e36d8b80`; the repository carries no `LICENSE` file |
| OR-Bench `or-bench-80k.csv` (benign, 800 drawn) | **CC-BY-4.0** | same |
| `protectai/deberta-v3-base-prompt-injection-v2` @ `90c9989b` | **Apache-2.0** | `LICENSE` file at the pinned revision, 10,172 bytes, sha256 `59899c6091b5…` |
| `dcarpintero/pangolin-guard-base` @ `eb220d9f` | **Apache-2.0, declared only** | **no `LICENSE` file exists at the pinned revision.** Recorded as a card declaration, not as hashed bytes. This is a gap and it is written down rather than smoothed. |

## What flows out

Per-item rows of the shape `(item_id, text_sha256, guard, threshold, flag)`,
plus the aggregates `q_obs`, `q_ind`, `Δ`, the Fréchet interval and a bootstrap CI.

**Released under CC-BY-4.0**, the strictest inbound term, with attribution to
the OR-Bench authors. Chosen to be inbound-compatible rather than convenient.

**No prompt text is redistributed.** Rows carry `sha256` of the text and the
row index, never the prompt. The pools stay where their authors put them; a
reader reconstructs the items from the pinned revision. This is the same rule
`MC-002` follows for BELLS — cite and hash, never redistribute.

## Attribution, to travel with any release

> Harmful and benign items drawn from OR-Bench (`bench-llm/or-bench`, revision
> `e36d8b80e81837c8a8f264bbb2a49f1b32c7e272`, configs `or-bench-toxic` and
> `or-bench-80k`), CC-BY-4.0. Guard verdicts produced by
> `protectai/deberta-v3-base-prompt-injection-v2` and
> `dcarpintero/pangolin-guard-base`, both Apache-2.0.

## Non-claims

- A declared licence is not a legal opinion, and nobody qualified has reviewed this.
- Apache-2.0 for G2 rests on a card field with no licence bytes to hash. If that
  matters to a downstream user, it is their gap to close too, and this file is
  where they will find it.
- Nothing here licenses redistribution of OR-Bench prompt text, which this
  repository does not do.
