# cubits11.github.io

Personal site of **Pranav Bhave** — cloud security × AI-safety infrastructure.
Live at [cubits11.github.io](https://cubits11.github.io/).

## Stack

None, on purpose. Hand-written HTML and CSS, ~2 KB of vanilla JavaScript
(theme toggle, scroll reveals, copy-email). No framework, no build step, no
analytics, no cookies. Fonts (Fraunces, Instrument Sans, Fragment Mono) are
self-hosted latin-subset woff2. The color system is sampled from the hero
photograph — see `DESIGN.md` for every decision and its rationale.

## Run locally

```bash
python3 -m http.server 4173
```

Then open http://localhost:4173.

## Deploy

Push to `main`. GitHub Pages serves the repository root (`.nojekyll` disables
Jekyll processing). No pipeline, nothing to break.

## Layout

```
index.html          the site (styles and script inline)
404.html            not-found page
assets/fonts/       self-hosted woff2 (latin subsets)
assets/img/         portrait derivatives (metadata stripped), OG image, icons
DESIGN.md           design-decision ledger: choices, rationale, verification
```

Content © Pranav Bhave. Code (HTML/CSS/JS) may be reused with attribution.
