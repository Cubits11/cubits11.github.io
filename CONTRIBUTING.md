# Contributing

The shortest useful contribution is a result, not a compliment.

| You have… | Do this |
|---|---|
| a reproduction that matched | [File it](https://github.com/Cubits11/cubits11.github.io/issues/new?template=reproduction.yml) — it becomes the claim's independent-reproduction record |
| a reproduction that did **not** match | [File it](https://github.com/Cubits11/cubits11.github.io/issues/new?template=reproduction.yml) — a mismatch is a correction, handled the same day, credited beside the claim |
| a counterexample, a benchmark the census missed, a row that misreads its source, or joint outcomes you can provide | [Bring it](https://github.com/Cubits11/cubits11.github.io/issues/new?template=counterexample.yml) |
| a patch | Open a pull request; the template is three lines |

Start at [/try/](https://cubits11.github.io/try/): three experiments (60 seconds, 3 minutes, 15 minutes), each with its command, expected result, falsifier and non-claim printed before you run anything.

**What happens to what you send.** Every qualified outcome — an independent reproduction, a source correction, a paired-outcome release, an accepted upstream contribution, a cold run of the protocol — is recorded in `distribution/outcomes.yaml`, which is validated in CI and rendered on `/try/`. A disagreement is recorded with at least the prominence of the claim it disagrees with. Attention (views, likes, follows, issues opened) is recorded separately as a diagnostic and is never counted as an outcome. The procedure is in `distribution/EXTERNAL_EVENTS.md`.

**Ground rules.** Claims live in `claims.yaml`; census rows in `census.yaml`; generated pages are never edited by hand (`python3 scripts/verification_manifest.py` regenerates and checks everything). Numbers on public pages are bound to those registries by `scripts/verify_facts.py`; a number typed into HTML fails the build.
