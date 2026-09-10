# Why this directory is empty in git

`experiments/e6/run/measure.js` needs the exact kernel bytes that
`anthropic.com/institute/econ-scenarios` shipped on 2026-09-10. Those bytes are
a third-party artifact carrying no declared licence, so this repository pins
them by digest and does not redistribute them. `freeze/sources.json` records
`"redistributed_here": false`, and the `.gitignore` here is what keeps that
statement true.

To reproduce E6 you need the bytes locally:

```bash
curl -sL -o experiments/e6/freeze/cache/bundle-chunk.js \
  https://www.anthropic.com/_next/static/chunks/0obtknnye5e24.js
shasum -a 256 experiments/e6/freeze/cache/bundle-chunk.js
# must be 0a75763f2ca4479bd88b240a7264307802b2ea6829d8db0c8efb5f515b8920f6
```

`measure.js` checks that digest itself and **exits 2** if the file is absent or
the hash differs. Exit 2 is not a pass and not a refutation: it means the check
could not be evaluated.

That URL is a build-hashed asset path and **will** change when the site
redeploys. When it does, the bytes are still identified by the digest above and
can be retrieved from a web archive. Re-pinning against a then-current kernel is
allowed but it is a different kernel, and `sources.json` must say so rather than
quietly carrying the old digest's numbers forward.

Nothing in this directory is needed to check E6's arithmetic.
`scripts/verify_e6.py` re-derives all 34 registered quantities from the 243
committed rows alone, with no network and no re-run of the model.
