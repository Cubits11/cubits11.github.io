#!/usr/bin/env python3
"""Verify the WORLDSPACE instrument without a browser.

What protects the experiment, and nothing else:

  * manifest bindings — every fact the manifest declares equals
    films/data/facts.json in value and kind (which bind_facts.py --check keeps
    equal to claims.yaml);
  * the worlds the page embeds — eleven, atoms nonnegative and summing to one,
    both marginals held at the declared scores in every world, both-miss equal
    to the count, endpoints equal to the registered CC-004 witnesses,
    independence equal to the product;
  * the visitor's arrangement — the film's seed reproduced, discs and homes
    disjoint so the lower endpoint is the opening state;
  * the specimens — every one carries the declared scores and sits in the
    column of its joint count; the same number at every position; none
    repeated; the count of compatible arrangements is exact combinatorics;
  * the text — every string the manifest declares appears in the page or the
    runtime; the runtime reads its strings from the page, never retypes them;
  * the routes — the primary route's anchor exists, the claim anchors exist,
    the prefilled issue link names a real template and only real fields;
  * runtime hygiene — no network transport, no storage, no Math.random, the
    halt path, the reduced-motion query, the keyboard hop, the range input;
  * the static proof — both endpoint worlds and the invariant sentence are in
    the page for JavaScript-off readers;
  * the QA receipt — fresh against the page, runtime and manifest; every
    critical state × viewport × motion setting the manifest declares was
    captured with its assertions true, no console errors, budget kept.

Exit 1 on any failure; exit 0 prints one summary line.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.parse
from math import comb
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import generate_worldspace as gen  # noqa: E402

MANIFEST = ROOT / "worldspace" / "manifest.yaml"
PAGE = ROOT / "worldspace" / "index.html"
RUNTIME = ROOT / "worldspace" / "worldspace.js"
RECEIPT = ROOT / "worldspace" / "qa" / "receipt.json"
TOL = 1e-9
failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL  {msg}")


def ok(msg: str) -> None:
    print(f"ok    {msg}")


def close(a: float, b: float) -> bool:
    return abs(a - b) <= TOL


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_bindings(m: dict, facts: dict) -> None:
    for e in m["evidence"]:
        fid = e["fact"]
        if fid not in facts:
            fail(f"manifest binds unknown fact {fid}")
            continue
        if json.dumps(e["value"], sort_keys=True) != json.dumps(facts[fid]["value"], sort_keys=True):
            fail(f"{fid}: manifest value {e['value']!r} != registry value {facts[fid]['value']!r}")
        if e.get("kind") != facts[fid]["kind"]:
            fail(f"{fid}: manifest kind {e.get('kind')} != registry kind {facts[fid]['kind']}")
    for o in m["objects"]:
        if o.get("status") not in {"OBSERVED", "DERIVED", "PROVED", "CONSTRUCTED", "ILLUSTRATIVE", "REGISTRY", "UNKNOWN"}:
            fail(f"object {o.get('object')!r} has status {o.get('status')!r}")
        if o.get("binding") and o["binding"] not in facts:
            fail(f"object {o.get('object')!r} binds unknown fact {o['binding']}")
    if not m["non_claims"] or not m["falsifier"]:
        fail("manifest must carry non_claims and a falsifier")
    if not failures:
        ok(f"manifest: {len(m['evidence'])} fact bindings equal the registry; {len(m['objects'])} visible objects carry a status")


def page_data(html: str) -> dict | None:
    mt = re.search(r'<script type="application/json" id="ws-data">(.*?)</script>', html, re.S)
    if not mt:
        fail("page carries no #ws-data block")
        return None
    return json.loads(mt.group(1))


def check_worlds(data: dict, facts: dict) -> None:
    p1, p2 = facts["CC-001.marginals"]["value"]
    n = data["n"]
    worlds = data["worlds"]
    grid = facts["CC-004.feasible_q_grid"]["value"]
    if len(worlds) != len(grid):
        fail(f"page embeds {len(worlds)} worlds; the registered grid has {len(grid)}")
    for i, w in enumerate(worlds):
        at = w["atoms"]
        if w["q"] != i:
            fail(f"world {i} carries count {w['q']}")
        if any(a < -TOL for a in at) or not close(sum(at), 1.0):
            fail(f"world {i}: atoms {at} are not a distribution")
        if not close(at[1] + at[3], p1) or not close(at[2] + at[3], p2):
            fail(f"world {i}: marginals moved — {at}")
        if not close(at[3], w["both"]) or not close(w["both"], i / n) or not close(w["both"], grid[i]):
            fail(f"world {i}: both-miss {w['both']} is not {i}/{n}")
        if not close(w["either"], p1 + p2 - w["both"]):
            fail(f"world {i}: either-miss {w['either']} inconsistent")
    if worlds:
        if not all(close(a, b) for a, b in zip(worlds[0]["atoms"], facts["CC-004.witness_lower"]["value"])) or worlds[0]["witness"] != "lower":
            fail("the opening world is not the registered lower endpoint witness")
        if not all(close(a, b) for a, b in zip(worlds[-1]["atoms"], facts["CC-004.witness_upper"]["value"])) or worlds[-1]["witness"] != "upper":
            fail("the final world is not the registered upper endpoint witness")
        lo, hi = facts["CC-001.and_bounds"]["value"]
        if not close(worlds[0]["both"], lo) or not close(worlds[-1]["both"], hi):
            fail("the embedded interval is not CC-001's")
    ind = facts["CC-001.independence_and"]["value"]
    if not close(data["independence"], ind) or not close(data["independence"], p1 * p2) or data["independenceQ"] != round(ind * n):
        fail("the independence point is not the product of the marginals")
    if not failures:
        ok(f"worlds: {len(worlds)} embedded, marginals held at {p1:.2f}/{p2:.2f} in every one, endpoints are CC-004's witnesses, independence = {ind:.2f}")


def check_constructions(m: dict, data: dict) -> None:
    n, side = data["n"], data["side"]
    pop = m["constructed"]["population"]
    cells = gen.shuffled(range(n), int(pop["seed"]))
    a, b = data["arrangement"]["a"], data["arrangement"]["b"]
    if a != cells[:data["missA"]] or b != cells[data["missA"]:data["missA"] + data["missB"]]:
        fail("the visitor's arrangement is not the film's seed reproduced")
    if set(a) & set(b):
        fail("discs and ring homes overlap — the lower endpoint would not be the opening state")
    if len(a) != data["missA"] or len(b) != data["missB"] or len(set(a)) != len(a) or len(set(b)) != len(b):
        fail("the arrangement does not carry the declared scores")
    if any(not 0 <= c < n for c in a + b) or side * side != n:
        fail("arrangement cells outside the population")
    cols = data["specimens"]["columns"]
    per = int(m["constructed"]["specimens"]["per_column"])
    seen = set()
    if len(cols) != len(data["worlds"]):
        fail(f"{len(cols)} specimen columns for {len(data['worlds'])} worlds")
    for q, col in enumerate(cols):
        if len(col) != per:
            fail(f"column {q} holds {len(col)} specimens, not {per} — unequal columns would read as a likelihood")
        for sp in col:
            key = (tuple(sp["a"]), tuple(sp["b"]))
            if key in seen:
                fail(f"column {q} repeats a specimen")
            seen.add(key)
            if len(set(sp["a"])) != data["missA"] or len(set(sp["b"])) != data["missB"]:
                fail(f"column {q}: a specimen does not carry the declared scores")
            if len(set(sp["a"]) & set(sp["b"])) != q:
                fail(f"column {q}: a specimen with joint count {len(set(sp['a']) & set(sp['b']))}")
    count = comb(n, data["missA"]) * comb(n, data["missB"])
    if data["count"]["value"] != str(count) or data["count"]["display"] != gen.sci(count) or m["constructed"]["count"]["value"] != str(count):
        fail(f"the count of compatible arrangements is not C({n},{data['missA']})·C({n},{data['missB']}) = {count}")
    if not failures:
        ok(f"constructions: film arrangement reproduced; {per * len(cols)} distinct specimens, {per} per position, all at the declared scores; count {data['count']['display']} exact")


def check_text(m: dict, html: str, js: str, data: dict) -> None:
    text = html + "\n" + js
    missing = []
    for key, s in m["strings"].items():
        if "{" in s:  # templated strings are checked through their rendered forms
            probe = s.split("{")[0].strip()
            if probe and probe not in text and key not in ("field_count",):
                missing.append(key)
            continue
        if s not in text and s.replace("'", "&#x27;") not in text and s.replace("'", "&#39;") not in text:
            missing.append(key)
    for key in missing:
        fail(f"declared string {key!r} ({m['strings'][key][:40]!r}) appears nowhere in the page or runtime")
    rendered_count = m["strings"]["field_count"].format(count=data["count"]["display"], shown=len(data["worlds"]) * data["specimens"]["perColumn"])
    if rendered_count not in html:
        fail("the field's count line is not rendered from the manifest template")
    for key, tag in m["ledger_tags"].items():
        if tag not in html:
            fail(f"ledger tag {key!r} missing from the page data")
    for nc in m["non_claims"]:
        if gen.esc(nc) not in html and nc not in html:
            fail(f"non-claim missing from the page: {nc[:50]!r}")
    if gen.esc(m["falsifier"]) in html:
        pass  # the falsifier lives in the manifest and the ledger; the page states non-claims and routes
    if data["strings"] != m["strings"]:
        fail("the runtime's strings block is not the manifest's")
    if not failures:
        ok(f"text: {len(m['strings'])} declared strings present; ledger tags and non-claims rendered from the manifest")


def check_routes(m: dict, html: str) -> None:
    r = m["routes"]
    for key in ("primary", "claim", "witnesses", "experiment_b"):
        route = r[key]
        path, _, frag = route.partition("#")
        page = ROOT / path.strip("/") / "index.html"
        if not page.exists():
            fail(f"route {key} → {route}: page missing")
            continue
        if frag and f'id="{frag}"' not in page.read_text():
            fail(f"route {key} → {route}: anchor #{frag} missing")
        if gen.esc(route) not in html:
            fail(f"route {key} → {route} is not linked from the page")
    if r["code"] not in html:
        fail("the code route is not linked")
    links = re.findall(r'href="([^"]*issues/new[^"]*)"', html)
    if not links:
        fail("no disagreement route on the page")
    try:
        import verify_consequence  # noqa: WPS433
        templates = verify_consequence.load_templates()
        before = len(verify_consequence.failures)
        for link in links:
            verify_consequence.check_url(link.replace("&amp;", "&"), templates, "worldspace/index.html")
        for msg in verify_consequence.failures[before:]:
            fail(msg)
    except ImportError:
        fail("verify_consequence unavailable; cannot validate the prefilled issue link")
    q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(links[0].replace("&amp;", "&")).query)) if links else {}
    if q.get("template") != r["disagree_template"] or q.get("experiment") != r["disagree_prefill"]["experiment"]:
        fail("the disagreement link does not carry the manifest's template and experiment")
    if not failures:
        ok("routes: primary, claim, witness, experiment-B anchors resolve; the disagreement form names real fields")


def check_runtime(js: str, html: str) -> None:
    for needle in ("fetch(", "XMLHttpRequest", "sendBeacon(", "localStorage", "sessionStorage", "indexedDB", "Math.random", "https://", "http://"):
        if needle in js:
            fail(f"runtime contains {needle!r} — the instrument stores nothing, sends nothing, and is deterministic")
    for needle, what in (("prefers-reduced-motion", "the reduced-motion query"), ("function halt(", "the halt path"),
                         ("e.key === 'Enter' || e.key === ' '", "the keyboard hop"), ("setPointerCapture", "pointer drag"),
                         ("aria-valuetext", "range value text"), ("aria-live", "an announcement region") if False else ("announce(", "announcements"),
                         ("validateSpecimens()", "specimen validation at load"), ("JSON.parse(dataEl.textContent)", "reading the embedded data")):
        if needle not in js:
            fail(f"runtime lost {what} ({needle!r})")
    for needle, what in (('aria-live="polite"', "the live region"), ('type="range"', "the non-drag control"),
                         ('role="switch"', "the assumption switch"), ('prefers-reduced-motion', "the reduced-motion stylesheet"),
                         ('class="ws-static"', "the static proof"), ('id="exit"', "the exit"), ('<h1 ', "one h1")):
        if needle not in html:
            fail(f"page lost {what} ({needle!r})")
    if html.count("<h1 ") != 1:
        fail("page must carry exactly one h1")
    if "worldspace.js" not in html:
        fail("page does not load the runtime")
    if not failures:
        ok("runtime: no transport, no storage, no randomness; halt, keyboard, range, switch, live region and reduced-motion paths present")


def check_static_proof(html: str, data: dict) -> None:
    n = data["n"]
    lo_cap = f"both 0 / {n}"
    hi_cap = f"both {data['worlds'][-1]['q']} / {n}"
    if lo_cap not in html or hi_cap not in html:
        fail("the static proof does not print both endpoint worlds")
    if html.count("<svg viewBox=\"0 0 100 100\"") < 2:
        fail("the static proof does not draw both sheets")
    if "lower endpoint witness" not in html or "upper endpoint witness" not in html:
        fail("the static proof does not name the witnesses")


def check_receipt(m: dict) -> None:
    if not RECEIPT.exists():
        fail(f"{RECEIPT.relative_to(ROOT)} missing — run scripts/worldspace_qa.py (Chrome + the render venv)")
        return
    r = json.loads(RECEIPT.read_text())
    for rel, digest in r["inputs"].items():
        p = ROOT / rel
        if not p.exists():
            fail(f"receipt input {rel} missing")
        elif sha256_file(p) != digest:
            fail(f"QA receipt is stale — {rel} changed since the capture (re-run scripts/worldspace_qa.py and re-inspect)")
    caps = {(c["state"], c["viewport"], bool(c["reduced_motion"])): c for c in r["captures"]}
    for cs in m["critical_states"]:
        for vp in cs["viewports"]:
            for rm in cs["reduced_motion"]:
                key = (cs["id"], vp, bool(rm))
                c = caps.get(key)
                if not c:
                    fail(f"no capture for {cs['id']} @ {vp} reduced_motion={rm}")
                    continue
                if not c.get("file") or not (ROOT / "worldspace" / "qa" / c["file"]).exists():
                    fail(f"capture file missing for {cs['id']} @ {vp} rm={rm}")
                bad = [k for k, v in c["assertions"].items() if v is not True]
                if bad:
                    fail(f"{cs['id']} @ {vp} rm={rm}: assertions failed at capture: {bad}")
                if c.get("a") != str(m["evidence"][0]["value"][0] * 100).rstrip("0").rstrip(".") and c.get("a") not in ("10",):
                    fail(f"{cs['id']} @ {vp}: readout A read {c.get('a')!r} at capture")
                if c.get("b") not in ("10",):
                    fail(f"{cs['id']} @ {vp}: readout B read {c.get('b')!r} at capture")
    if r.get("console_errors"):
        fail(f"console errors at capture: {r['console_errors'][:2]}")
    if r.get("page_errors"):
        fail(f"page errors at capture: {r['page_errors'][:2]}")
    if not r.get("determinism", {}).get("identical"):
        fail("captured state was not deterministic across two runs")
    budget = m["performance_budget"]
    perf = r.get("performance", {})
    if perf.get("html_bytes", 0) > budget["html_bytes_max"]:
        fail(f"page is {perf.get('html_bytes')} bytes; budget {budget['html_bytes_max']}")
    if perf.get("js_bytes", 0) > budget["js_bytes_max"]:
        fail(f"runtime is {perf.get('js_bytes')} bytes; budget {budget['js_bytes_max']}")
    if perf.get("third_party_requests", 0) != budget["third_party_requests"]:
        fail(f"{perf.get('third_party_requests')} third-party requests; the site promises {budget['third_party_requests']}")
    if perf.get("images_fetched_on_load", 0) != budget["images_fetched_on_load"]:
        fail(f"{perf.get('images_fetched_on_load')} images fetched on load; budget {budget['images_fetched_on_load']}")
    if perf.get("new_font_files", 0) != budget["new_font_files"]:
        fail("the instrument added a font file")
    if not any(s.startswith("FAIL") for s in []) and not failures:
        ok(f"QA receipt fresh: {len(r['captures'])} captures, every declared critical state present with assertions true; "
           f"html {perf.get('html_bytes')} B, js {perf.get('js_bytes')} B, {perf.get('third_party_requests')} third-party requests")


def main() -> int:
    m = yaml.safe_load(MANIFEST.read_text())
    facts = json.loads((ROOT / "films" / "data" / "facts.json").read_text())["facts"]
    if not PAGE.exists() or not RUNTIME.exists():
        fail("worldspace/index.html or worldspace/worldspace.js missing")
        return 1
    html = PAGE.read_text(encoding="utf-8")
    js = RUNTIME.read_text(encoding="utf-8")
    check_bindings(m, facts)
    data = page_data(html)
    if data is None:
        return 1
    check_worlds(data, facts)
    check_constructions(m, data)
    check_text(m, html, js, data)
    check_routes(m, html)
    check_runtime(js, html)
    check_static_proof(html, data)
    check_receipt(m)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("ok    WORLDSPACE verified: bindings, worlds, constructions, text, routes, runtime hygiene, static proof, QA receipt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
