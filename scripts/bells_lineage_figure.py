#!/usr/bin/env python3
"""Render the BELLS denominator lineage as one static SVG.

Every bar is a population that a published BELLS number sits on, drawn to one
common scale so the eye cannot be fooled by a ratio: the paper's described 990,
the two pool files in upstream history, the leaderboard aggregate's population
(derived: pool minus Miscellaneous), and the two playground subsets, one of
which is the file MC-002 binds. Counts come from `scripts/bells_denominators.py
--json` — hash-asserted upstream bytes — never from this file.

Encoding, stated so it cannot be misread:
  * segment lightness + fixed order + a count inside every segment = stratum
    (harmful, benign, borderline). Identity is never colour alone.
  * a small tag and rule at the left of each row = evidential state, in the
    site's semantic colours AND in words: hash-verified file / derived /
    text only. State is never colour alone either.
  * no rate, ratio, or axis of percent appears. These are counts.

Run:  python3 scripts/bells_lineage_figure.py [--cache DIR] [--out PATH] [--theme auto|light|dark]
Default output: ARTIFACTS/2026-09-05-bells-denominator-lineage.svg
"""

import argparse
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "ARTIFACTS" / "2026-09-05-bells-denominator-lineage.svg"

# Site tokens (index.html). Light first; dark redefined in the <style>.
LIGHT = dict(bg="#F1EDE2", surface="#F8F5EC", ink="#14170F", muted="#565E4E",
             line="#DCD5C2", strong="#C2BAA2", evidence="#175F6B",
             review="#7E4E12", invalid="#993127", gold="#755A2C")
DARK = dict(bg="#0B0F0A", surface="#11150F", ink="#EDE8DA", muted="#9AA391",
            line="#232A20", strong="#39422F", evidence="#7FC4CF",
            review="#E9A23B", invalid="#E4796F", gold="#C9A15E")

W, H = 1440, 880
PLOT_X0, PLOT_X1 = 48, 1250
BAR_H = 22
GAP = 2
ROW_H = 110
TOP = 118
SUB_WRAP = 150  # characters per sub-line at 11px mono (~6.6px/char) inside W
STRATA = ("harmful", "benign", "borderline")


def wrap(text: str, width: int = SUB_WRAP) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}" if cur else w
    if cur:
        lines.append(cur)
    return lines


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def load_report(cache: str | None) -> dict:
    cmd = [sys.executable, str(ROOT / "scripts" / "bells_denominators.py"), "--json"]
    if cache:
        cmd += ["--cache", cache]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def rows_from(report: dict) -> list[dict]:
    items = report["items"]
    ident = report["aggregate_identification"]
    sha = {f"{p['commit']}:{pathlib.Path(p['path']).name}": p["sha256"][:12] for p in report["pins"]}

    def item(key: str) -> dict:
        return items[key]["by_harm_level"]

    rem, rm = ident["remaining_rows"], ident["removed_rows"]
    return [
        dict(name="Paper, arXiv 2507.06282 — non-adversarial set as described",
             sub="§3 and App. 0.B.2: “990 prompts … 330 benign / 330 borderline / 330 harmful”. "
                 "No released file has this composition.",
             counts={"harmful": 330, "benign": 330, "borderline": 330},
             state="text", locator="arXiv 2507.06282 (text only)"),
        dict(name="Pool v0 · non_adversarial_prompts.csv @ 0fc3d6d3 · 2025-02-18",
             sub="12 harm categories incl. Miscellaneous. Prompt Guard and LangKit columns are constant 1 — placeholders, not verdicts.",
             counts=item("0fc3d6d3:non_adversarial_prompts.csv"),
             state="file", locator=f"sha256 {sha['0fc3d6d3:non_adversarial_prompts.csv']}…"),
        dict(name="Pool · non_adversarial_prompts.csv @ d6ebd0e5 · 2025-02-18",
             sub="Same pool, 3 rows fewer. Lakera, NeMo and LLM Guard columns carry real verdicts; the other two are still placeholders.",
             counts=item("d6ebd0e5:non_adversarial_prompts.csv"),
             state="file", locator=f"sha256 {sha['d6ebd0e5:non_adversarial_prompts.csv']}…"),
        dict(name="Leaderboard aggregate population · safeguard_evaluation_results.csv @ dde32a3d → 507566c5",
             sub=f"= pool d6ebd0e5 minus its {rm['harmful'] + rm['benign'] + rm['borderline']} Miscellaneous rows "
                 f"({rm['harmful']} harmful · {rm['benign']} benign). Numerators match {ident['testable_matches']} "
                 f"for Lakera, NeMo, LLM Guard; untestable for Prompt Guard and LangKit.",
             counts=rem, state="derived",
             locator="denominators inferred from the aggregate’s fractions; sha256 6935166c5663…"),
        dict(name="Playground subset · non_adversarial_prompts.csv @ 077555d9 · 2025-02-19",
             sub="Commit subject “smaller dataset for playground”. SELECTION RULE: UNKNOWN. Superseded.",
             counts=item("077555d9:non_adversarial_prompts.csv"),
             state="file", locator=f"sha256 {sha['077555d9:non_adversarial_prompts.csv']}…"),
        dict(name="Playground subset · non_adversarial_prompts.csv @ b20aeed5 = 507566c5 (head) · 2025-03-22",
             sub="The file MC-002 binds. A fresh draw from the d6ebd0e5 pool (170/170 present), sharing only 74–76 questions "
                 "with the 174. SELECTION RULE: UNKNOWN.",
             counts=item("507566c5:non_adversarial_prompts.csv"),
             state="file", locator=f"sha256 {sha['507566c5:non_adversarial_prompts.csv']}…"),
    ]


def render(rows: list[dict], theme: str = "auto") -> str:
    scale_max = max(sum(r["counts"][s] for s in STRATA) for r in rows)
    px = (PLOT_X1 - PLOT_X0) / scale_max
    state_word = {"file": "hash-verified file", "derived": "derived", "text": "text only"}
    state_glyph = {"file": "●", "derived": "◐", "text": "○"}
    state_cls = {"file": "evidence", "derived": "review", "text": "invalid"}
    seg_cls = {"harmful": "seg-harmful", "benign": "seg-benign", "borderline": "seg-borderline"}
    txt_cls = {"harmful": "in-dark", "benign": "in-dark", "borderline": "in-light"}

    out = []
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
               f'role="img" aria-labelledby="t d">')
    out.append('<title id="t">Where the BELLS denominators sit</title>')
    out.append('<desc id="d">Six populations drawn to one scale: the paper’s described 990; the 1080 and 1077-row '
               'pool files in upstream history; the leaderboard aggregate’s 1041 (pool minus Miscellaneous); '
               'the 174 and 170-row playground subsets. Counts only.</desc>')
    L, D = LIGHT, DARK

    def tokens(t: dict) -> str:
        return (f"--bg:{t['bg']};--surface:{t['surface']};--ink:{t['ink']};--muted:{t['muted']};"
                f"--line:{t['line']};--strong:{t['strong']};--evidence:{t['evidence']};"
                f"--review:{t['review']};--invalid:{t['invalid']};--gold:{t['gold']}")

    if theme == "dark":
        palette = f":root{{{tokens(D)}}}"
    elif theme == "light":
        palette = f":root{{{tokens(L)}}}"
    else:
        palette = (f":root{{{tokens(L)}}}\n"
                   f"@media (prefers-color-scheme: dark){{:root{{{tokens(D)}}}}}")
    out.append(f"""<style>
{palette}
.bg{{fill:var(--surface)}}
text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;fill:var(--ink)}}
.title{{font-family:Georgia,"Times New Roman",serif;font-size:26px;fill:var(--ink)}}
.sub{{font-size:12.5px;fill:var(--muted)}}
.eyebrow{{font-size:10.5px;letter-spacing:.08em;fill:var(--gold)}}
.rowname{{font-size:13px;fill:var(--ink)}}
.rowsub{{font-size:11px;fill:var(--muted)}}
.total{{font-size:12px;fill:var(--ink)}}
.count{{font-size:11px}}
.in-dark{{fill:var(--surface)}}
.in-light{{fill:var(--ink)}}
.seg-harmful{{fill:var(--ink)}}
.seg-benign{{fill:var(--muted)}}
.seg-borderline{{fill:var(--strong)}}
.seg-text{{fill:none;stroke:var(--invalid);stroke-width:1.2;stroke-dasharray:4 3}}
.tag{{font-size:10px;letter-spacing:.06em}}
.tag.evidence,.rule.evidence{{fill:var(--evidence)}}
.tag.review,.rule.review{{fill:var(--review)}}
.tag.invalid,.rule.invalid{{fill:var(--invalid)}}
.axis{{stroke:var(--line);stroke-width:1}}
.tick{{font-size:10px;fill:var(--muted)}}
.legend{{font-size:11px;fill:var(--muted)}}
.foot{{font-size:10px;fill:var(--muted)}}
</style>""")
    out.append(f'<rect class="bg" x="0" y="0" width="{W}" height="{H}"/>')
    # Header
    out.append(f'<text class="eyebrow" x="{PLOT_X0}" y="34">BELLS 2025 · MISUSE DETECTION · OBSERVATION CUT 0 · 2026-09-05</text>')
    out.append(f'<text class="title" x="{PLOT_X0}" y="66">Where the BELLS denominators sit</text>')
    out.append(f'<text class="sub" x="{PLOT_X0}" y="88">Six populations on one scale. Every bar is a count of prompts; '
               f'no bar is a rate.</text>')
    # Light scale ticks at the top of the plot
    y_axis = TOP - 14
    for v in (0, 250, 500, 750, 1000):
        x = PLOT_X0 + v * px
        out.append(f'<line class="axis" x1="{x:.1f}" y1="{y_axis}" x2="{x:.1f}" y2="{y_axis + 5}"/>')
        out.append(f'<text class="tick" x="{x:.1f}" y="{y_axis - 4}" text-anchor="middle">{v:,}</text>')
    out.append(f'<line class="axis" x1="{PLOT_X0}" y1="{y_axis}" x2="{PLOT_X1}" y2="{y_axis}"/>')

    for i, r in enumerate(rows):
        y = TOP + i * ROW_H
        cls = state_cls[r["state"]]
        out.append(f'<g class="row" data-state="{r["state"]}">')
        out.append(f'<rect class="rule {cls}" x="{PLOT_X0 - 14}" y="{y}" width="3" height="{ROW_H - 26}"/>')
        out.append(f'<text class="tag {cls}" x="{PLOT_X0}" y="{y + 10}">{state_glyph[r["state"]]} '
                   f'{esc(state_word[r["state"]].upper())}</text>')
        out.append(f'<text class="rowname" x="{PLOT_X0}" y="{y + 27}">{esc(r["name"])}</text>')
        sub_lines = wrap(r["sub"])
        for k, line in enumerate(sub_lines):
            out.append(f'<text class="rowsub" x="{PLOT_X0}" y="{y + 42 + 14 * k}">{esc(line)}</text>')
        by = y + 50 + 14 * (len(sub_lines) - 1)
        x = PLOT_X0
        total = sum(r["counts"][s] for s in STRATA)
        for j, s in enumerate(STRATA):
            n = r["counts"][s]
            w = n * px - (GAP if j < len(STRATA) - 1 else 0)
            last = j == len(STRATA) - 1
            tip = f'{s} {n} of {total} — {r["locator"]}'
            if r["state"] == "text":
                out.append(f'<rect class="seg-text" x="{x:.1f}" y="{by}" width="{w:.1f}" height="{BAR_H}" '
                           f'rx="{4 if last else 0}"><title>{esc(tip)}</title></rect>')
                out.append(f'<text class="count in-light" x="{x + 6:.1f}" y="{by + 15}">{n}</text>')
            else:
                if last:
                    # 4px rounded data-end on the right only; square at the baseline.
                    p = (f'M{x:.1f},{by} H{x + w - 4:.1f} a4,4 0 0 1 4,4 V{by + BAR_H - 4} '
                         f'a4,4 0 0 1 -4,4 H{x:.1f} Z')
                    out.append(f'<path class="{seg_cls[s]}" d="{p}"><title>{esc(tip)}</title></path>')
                else:
                    out.append(f'<rect class="{seg_cls[s]}" x="{x:.1f}" y="{by}" width="{w:.1f}" height="{BAR_H}">'
                               f'<title>{esc(tip)}</title></rect>')
                if w >= 26:
                    out.append(f'<text class="count {txt_cls[s]}" x="{x + 6:.1f}" y="{by + 15}">{n}</text>')
            x += n * px
        out.append(f'<text class="total" x="{x + 10:.1f}" y="{by + 15}">= {total:,}</text>')
        out.append('</g>')

    # Legend: strata (fill lightness, fixed order) and states (word + glyph)
    ly = TOP + len(rows) * ROW_H - 10
    lx = PLOT_X0
    for s in STRATA:
        out.append(f'<rect class="{seg_cls[s]}" x="{lx}" y="{ly - 9}" width="14" height="10" rx="2"/>')
        out.append(f'<text class="legend" x="{lx + 20}" y="{ly}">{s}</text>')
        lx += 22 + 8 * len(s) + 26
    out.append(f'<rect class="seg-text" x="{lx}" y="{ly - 9}" width="14" height="10"/>')
    out.append(f'<text class="legend" x="{lx + 20}" y="{ly}">described in text, no file</text>')
    lx += 22 + 8 * 26 + 10
    out.append(f'<text class="legend" x="{lx}" y="{ly}">left tag = evidential state, in words: '
               f'● hash-verified file · ◐ derived · ○ text only</text>')
    out.append(f'<text class="foot" x="{PLOT_X0}" y="{ly + 24}">Source: python3 scripts/bells_denominators.py --json '
               f'(CentreSecuriteIA/bells_leaderboard, pinned by commit and sha256). '
               f'Packet: ARTIFACTS/2026-09-05-FABLE-5.1-OBS-CUT.md.</text>')
    out.append(f'<text class="foot" x="{PLOT_X0}" y="{ly + 38}">Counts describe released files at their released labels, '
               f'not any system’s true rate. Selection rule for the playground subsets: UNKNOWN.</text>')
    out.append('</svg>')
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--theme", choices=("auto", "light", "dark"), default="auto",
                    help="auto follows prefers-color-scheme; light/dark fix the tokens (for rasters)")
    args = ap.parse_args()
    report = load_report(args.cache)
    svg = render(rows_from(report), theme=args.theme)
    pathlib.Path(args.out).write_text(svg, encoding="utf-8")
    print(f"wrote {args.out} ({len(svg)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
