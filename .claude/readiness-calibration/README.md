# readiness-calibration

Data for the Drive-side Prompt Readiness Engine (GLASSROOT 13.xx). No doctrine
lives here; the engine's documents stay in Drive. Nothing here is wired into
`scripts/verification_manifest.py`, and nothing here counts toward
`scripts/cadence.py`.

| file | what it is |
|---|---|
| `preoutcome_scores.json` | readiness scores for 10 real prompts, written before any outcome was looked up; byte-identical to Drive file `13.10 — FROZEN …json`, whose server `createdTime` is 2026-09-26T14:00:47.656Z |
| `retro_outcomes.json` | what those runs produced, re-checked at each run's own commit |
| `suite_cases.json` | the 16 prompts published unscored in Drive `13.12`; the sheet prints the hash of their canonical JSON, `d09cad3115cfb7e17c3ff90c49344f022338d87f4e9d1a10b170c317001aff0f` |
| `suite_key.json` | sealed expected dispositions for `13.12` |

```
eb4b4059a0daeffa0ee69a4bae7bbc5a0cf3ed202a29f79db8e073ff89a08462  preoutcome_scores.json
107814772309484435834df92b74b8c65a580c14f835ef04cc607d9086bdca61  retro_outcomes.json
1a97a485a63f44b574846605ad4326d34a59d6b5f2e910c7c7e2ba70e10db9fd  suite_cases.json
02e3cc11f3444f9f74577d57c92239d3839f95d35b516fce513373906eb67478  suite_key.json
```

`suite_key.json` is here, and not in Drive, so the scorer can work without
seeing it. Do not open it until every row of `13.12` is scored. After scoring,
hash it and compare with the value printed in the sheet; a different hash means
the key changed after the sheet was published.

The key is one rater's pre-registered judgment. It is not ground truth.
