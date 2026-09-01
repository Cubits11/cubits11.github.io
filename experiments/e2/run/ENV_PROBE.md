# E2 environment probe — install recipe proven on arm64 macOS

Dated 2026-09-01. Box-absent work (runbook steps 1–2 and 5 only): no
weight downloaded, no credential touched, no frozen item scored. This
probe answers one question the box session would otherwise answer the
slow way: does the exact install recipe resolve on Apple silicon, and
on which Python?

## Result — it resolves

Host: Apple M1 (8 GB — NOT the authorized box; probe only).
Python 3.14.6 (venv) · `pip install torch transformers mlx-lm`:

| package | version | status |
|---|---|---|
| torch | 2.13.0 | imports; `torch.backends.mps.is_available()` → True |
| transformers | 5.16.1 | imports |
| mlx_lm | 0.31.3 | imports |

Same-date reruns at this HEAD, all green: `check_freeze.py` (freeze
holds), `calibrate.py --synthetic` (sweep exact at 0.0500), and
`test_instrument.py` (nine properties, every planted violation caught).

Addendum 2026-09-01 (gap named in review, closed): the probe venv lives
in a session scratchpad and will vanish; the durable receipt is the
committed lockfile `env-probe.freeze.txt` beside this file (`pip freeze`,
40 packages, including mlx 0.32.2 pulled by mlx-lm). The box reproduces
the environment from that file, not from this prose.

## What the box still does (this probe replaces none of it)

`huggingface-cli login` (owner's account), authenticated downloads at
the three pinned SHAs, LICENSE hashes + commercial_reuse into
LICENSES.md, LG4 8-bit local conversion with recorded hashes,
`E2_ON_AUTHORIZED_BOX=1`, on-box synthetic shakeout, then the first
real token: `calibrate.py --guard sg2b`, calibration half only, stop
after `e2_config.json`. Do not score harmful outcomes the same day
thresholds are frozen.
