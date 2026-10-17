#!/usr/bin/env python3
"""Does every fact a film's output depends on appear in its receipt's facts_used?

    ~/.venvs/cubits-films/bin/python scripts/films/mutation_completeness.py [--shard i/n] [--out results.json]
    ~/.venvs/cubits-films/bin/python scripts/films/mutation_completeness.py --merge a.json b.json ...

A render receipt binds only the facts its film read (facts_digest.py). That is
safe only if the runtime logs every fact the film reads. This test checks it
by mutation, for every render receipt on disk (primary and secondary cuts)
and every fact in films/data/facts.json:

  serve the film a facts.json in which that one fact's value is mutated, replay
  the whole timeline, and compare its output with the unmutated replay.

  FAIL  output changed, and the fact is not in the receipt's facts_used: the
        film read a fact the log missed, so the subset digest would miss it
  WARN  the fact is in facts_used, and no mutation changed the output: read
        but not visible, so the subset digest is stricter than needed there
  ok    otherwise

Every fact gets two mutations (every leaf changed; then larger changes that
also alter list lengths); a fact counts as unchanged only if both leave the
output alone. Output is observed two ways:

  * the command stream: every CanvasRenderingContext2D method call and state
    assignment, with its arguments, every gradient colour stop and canvas
    resize, digested frame by frame from page load to the last frame. The same
    stream from the same start state draws the same pixels, so an unchanged
    stream is an unchanged render; a changed stream is checked in pixels.
  * pixels: where a stream changed, those frames are captured over CDP as
    render_film.py captures them and compared byte for byte with the
    unmutated capture. Once per cut, every fact outside facts_used is mutated
    at once and the whole timeline is captured; its frames_digest must equal
    the receipt's.

Also per cut, every fact's fields other than value (kind, claim, source) and
every top-level key of facts.json are mutated at once. The subset digest
ignores them, so any output change there is a FAIL.

The watch page text (scripts/generate_film_pages.py) is regenerated for every
mutation twice: with its staleness gate, it must either publish the committed
pages or refuse a film whose primary receipt read the mutated fact; with the
gate disabled, every page must equal the committed page.

This is evidence about these films at this revision. It does not cover a
future film, a font change, or a film that reaches facts by another path.
Exit 1 on any FAIL.
"""

from __future__ import annotations

import argparse
import base64
import copy
import functools
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import facts_digest
import render_film

ROOT, FILMS = render_film.ROOT, render_film.FILMS
FACTS = FILMS / "data" / "facts.json"
DIMS = {"master": (1920, 1080), "vertical": (1080, 1920), "square": (1080, 1080)}
PIXEL_SAMPLE = 8  # changed frames captured first; all changed frames if none of these differ

INSTRUMENT = r"""
(() => {
  let ids = new WeakMap(), next = 1;
  const id = o => { if (!ids.has(o)) ids.set(o, next++); return ids.get(o); };
  let buf = [];
  const ser = v => {
    if (v === null || v === undefined) return String(v);
    const t = typeof v;
    if (t === 'number') return Object.is(v, -0) ? '-0' : String(v);
    if (t === 'string') return JSON.stringify(v);
    if (t === 'boolean' || t === 'bigint') return String(v);
    if (Array.isArray(v) || ArrayBuffer.isView(v)) return '[' + Array.from(v, ser).join(',') + ']';
    if (v instanceof CanvasGradient) return 'gradient#' + id(v);
    if (v instanceof CanvasPattern) return 'pattern#' + id(v);
    if (v instanceof Path2D) return 'path#' + id(v);
    if (v instanceof HTMLCanvasElement) return 'canvas#' + id(v);
    if (v instanceof CanvasRenderingContext2D) return 'ctx#' + id(v);
    if (typeof v === 'function') return 'fn';
    return Object.prototype.toString.call(v) + JSON.stringify(v);
  };
  const wrap = (proto, label) => {
    for (const name of Object.getOwnPropertyNames(proto)) {
      if (name === 'constructor') continue;
      const d = Object.getOwnPropertyDescriptor(proto, name);
      if (typeof d.value === 'function') {
        const f = d.value;
        proto[name] = function (...a) { buf.push(label + id(this) + '.' + name + '(' + a.map(ser).join(',') + ')'); return f.apply(this, a); };
      } else if (d.set) {
        const set = d.set;
        Object.defineProperty(proto, name, { configurable: true, enumerable: d.enumerable, get: d.get,
          set(v) { buf.push(label + id(this) + '.' + name + '=' + ser(v)); return set.call(this, v); } });
      }
    }
  };
  wrap(CanvasRenderingContext2D.prototype, 'ctx#');
  wrap(CanvasGradient.prototype, 'gradient#');
  wrap(Path2D.prototype, 'path#');
  for (const p of ['width', 'height']) {
    const d = Object.getOwnPropertyDescriptor(HTMLCanvasElement.prototype, p);
    Object.defineProperty(HTMLCanvasElement.prototype, p, { configurable: true, enumerable: d.enumerable, get: d.get,
      set(v) { buf.push('canvas#' + id(this) + '.' + p + '=' + ser(v)); return d.set.call(this, v); } });
  }
  // every read of the parsed facts.json, by any path: fact ids touched, fields read, top-level keys read
  let touched = {}, top = new Set(), enumerated = false;
  const json = Response.prototype.json;
  Response.prototype.json = async function () {
    const doc = await json.call(this);
    if (!/\/films\/data\/facts\.json(\?|$)/.test(this.url)) return doc;
    const fact = (fid, f) => new Proxy(f, { get(t, k, r) { touched[fid].add(String(k)); return Reflect.get(t, k, r); } });
    const facts = new Proxy(doc.facts, {
      get(t, k, r) {
        const v = Reflect.get(t, k, r);
        if (typeof k !== 'string') return v;
        touched[k] = touched[k] || new Set();
        return v && typeof v === 'object' ? fact(k, v) : v;
      },
      has(t, k) { touched[k] = touched[k] || new Set(); touched[k].add('(in)'); return Reflect.has(t, k); },
      ownKeys(t) { enumerated = true; return Reflect.ownKeys(t); }
    });
    // resolving the promise this async function returns reads .then of the value: the engine, not the film
    return new Proxy(doc, { get(t, k, r) { if (k !== 'then') top.add(String(k)); return k === 'facts' ? facts : Reflect.get(t, k, r); },
                            ownKeys(t) { enumerated = true; return Reflect.ownKeys(t); } });
  };
  window.__reads = { take() {
    const out = { facts: Object.fromEntries(Object.entries(touched).map(([k, v]) => [k, [...v].sort()])), top: [...top].sort(), enumerated };
    touched = {}; top = new Set(); enumerated = false;
    return out;
  } };
  addEventListener('error', e => { window.__filmError = String(e.message); });
  addEventListener('unhandledrejection', e => { window.__filmError = String(e.reason && e.reason.message || e.reason); });
  window.__stream = {
    take() { const s = buf.join('\n'); buf = []; return s; },
    reset() { buf = []; ids = new WeakMap(); next = 1; }  // a fresh film numbers its objects from 1 again
  };
})();
"""

REPLAY = r"""async ([total, fps]) => {
  const enc = new TextEncoder();
  const hex = b => Array.from(new Uint8Array(b), x => x.toString(16).padStart(2, '0')).join('');
  const dig = async () => hex(await crypto.subtle.digest('SHA-256', enc.encode(window.__stream.take())));
  const frames = [await dig()];  // page load, define(), setup and the initial seek
  for (let i = 0; i < total; i++) {
    try { window.__film.seek(i / fps); } catch (e) { return { error: `frame ${i}: ${e.message}`, frames }; }
    frames.push(await dig());
  }
  return { frames, used: window.__film.factsUsed(), reads: window.__reads.take() };
}"""

# A fresh film without a navigation: a new stage, then film.js and the film's own script evaluated
# again, so the runtime's closure (facts, the fact() log, the canvas) is new. Fonts stay loaded.
REEVAL = r"""async ([filmSrc, inlineSrc]) => {
  window.__filmError = null;
  const old = document.getElementById('stage'); if (old) old.remove();
  const stage = document.createElement('div'); stage.id = 'stage'; document.body.appendChild(stage);
  window.__stream.reset();
  window.__reads.take();
  try {
    (0, eval)(filmSrc);
    (0, eval)('(function () {\n' + inlineSrc + '\n})();');
  } catch (e) { return 'script error: ' + e.message; }
  const t0 = performance.now();
  while (!(window.__film && window.__film.ready) && !window.__filmError) {
    if (performance.now() - t0 > 20000) return 'not ready after 20 s';
    await new Promise(r => setTimeout(r, 2));
  }
  return window.__filmError ? 'page error: ' + window.__filmError : null;
}"""

SEEK_AND_SETTLE = """t => {
    window.__film.seek(t);
    if (window.__stream) window.__stream.take();
    return new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
}"""


# ---- mutations -------------------------------------------------------------

def shift(s: str, k: int) -> str:
    out = []
    for ch in s:
        if ch.isdigit():
            out.append(str((int(ch) + k) % 10))
        elif "a" <= ch <= "z":
            out.append(chr((ord(ch) - 97 + k) % 26 + 97))
        elif "A" <= ch <= "Z":
            out.append(chr((ord(ch) - 65 + k) % 26 + 65))
        else:
            out.append(ch)
    return "".join(out)


def mutate(v, level: int):
    """Level 1 changes every leaf and keeps every shape; level 2 changes leaves more and list lengths too."""
    if isinstance(v, bool):
        return not v
    if isinstance(v, int):
        return v + 1 if level == 1 else v * 2 + 3
    if isinstance(v, float):
        if 0 <= v <= 1:
            if level == 1:
                return round(v + 0.137, 12) if v <= 0.863 else round(v - 0.137, 12)
            return round(v / 2, 12) if v >= 0.2 else round(v + 0.5, 12)
        return v * 1.37 + 1 if level == 1 else v * 3 + 2
    if isinstance(v, str):
        return shift(v, 1) if level == 1 else shift(v, 5)[::-1] + " MUTATED"
    if isinstance(v, list):
        out = [mutate(x, level) for x in v]
        if level == 2:
            out = out[:-1] if len(out) > 1 else out + [copy.deepcopy(out[0]) if out else 1]
        return out
    if isinstance(v, dict):
        out = {k: mutate(x, level) for k, x in v.items()}
        if level == 2:
            out["mutated"] = 1
        return out
    return 1 if level == 1 else "MUTATED"


def mutated_value(v, level: int):
    m = mutate(v, level)
    if facts_digest.canonical(m) == facts_digest.canonical(v):
        m = {"__mutated__": level}
    return m


def with_value(doc: dict, fid: str, value) -> dict:
    """doc with one fact's value replaced; everything else shared, never mutated."""
    return {**doc, "facts": {**doc["facts"], fid: {**doc["facts"][fid], "value": value}}}


def meta_mutation(doc: dict) -> dict:
    """Every field the subset digest ignores, changed at once: fact fields other than value, and top-level keys."""
    out = copy.deepcopy(doc)
    for f in out["facts"].values():
        for key in list(f):
            if key != "value":
                f[key] = mutate(f[key], 1) if not isinstance(f[key], str) else shift(f[key], 1) + " MUTATED"
    for key in list(out):
        if key != "facts":
            out[key] = mutate(out[key], 2)
    return out


# ---- runs ------------------------------------------------------------------

class Cut:
    def __init__(self, receipt_path: Path):
        self.path = receipt_path
        self.receipt = json.loads(receipt_path.read_text())
        self.slug, self.fmt = self.receipt["film"], self.receipt["format"]
        self.name = f"{self.slug} [{self.fmt}]"
        self.W, self.H = DIMS[self.fmt]
        self.fps, self.total = self.receipt["fps"], self.receipt["frames"]
        self.used = set(self.receipt["facts_used"])
        self.primary = (yaml_primary(self.slug) == self.fmt)
        self.film_js = (FILMS / "lib" / "film.js").read_text()
        html = (FILMS / self.slug / "film.html").read_text()
        inline = re.findall(r"<script>(.*?)</script>", html, re.S)
        if len(inline) != 1 or html.count("<script") != 2:
            raise SystemExit(f"{self.name}: expected film.js and one inline script")
        self.inline = inline[0]


def yaml_primary(slug: str) -> str:
    import yaml
    m = yaml.safe_load((FILMS / slug / "manifest.yaml").read_text())
    return (m.get("render") or {}).get("primary", "master")


class Stage:
    """One browser page per cut, serving the film whatever facts.json the run asks for."""

    def __init__(self, browser, port: int, cut: Cut, instrumented: bool):
        self.cut, self.port = cut, port
        self.page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        self.body = b""
        self.loaded = False
        self.errors: list[str] = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        if instrumented:
            self.page.add_init_script(INSTRUMENT)
        self.page.route("**/films/data/facts.json",
                        lambda route: route.fulfill(status=200, content_type="application/json", body=self.body))
        self.cdp = self.page.context.new_cdp_session(self.page)
        self.capture_options = {"format": "png", "optimizeForSpeed": True, "fromSurface": True,
                                "captureBeyondViewport": True,
                                "clip": {"x": 0, "y": 0, "width": cut.W, "height": cut.H, "scale": 1}}

    def load(self, doc: dict) -> str | None:
        """Open the film on these facts; return an error string if it would not start."""
        self.body = json.dumps(doc).encode()
        self.errors.clear()
        url = f"http://127.0.0.1:{self.port}/films/{self.cut.slug}/film.html?capture=1&format={self.cut.fmt}"
        self.page.goto(url, wait_until="load")
        try:
            self.page.wait_for_function("window.__filmError || (window.__film && window.__film.ready)", timeout=20000)
        except Exception as exc:  # noqa: BLE001 — a film that never becomes ready is an output change
            return f"not ready: {exc.__class__.__name__}"
        err = self.page.evaluate("window.__filmError || null")
        if err or self.errors:
            return f"page error: {err or self.errors[0]}"
        # as render_film.py: emulate the format's viewport, then let the compositor settle
        self.page.set_viewport_size({"width": self.cut.W, "height": self.cut.H})
        self.page.wait_for_function("([w,h]) => innerWidth === w && innerHeight === h", arg=[self.cut.W, self.cut.H])
        self.page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
        return None

    def fresh(self, doc: dict) -> str | None:
        """The film again on these facts, without reloading the page (instrumented stages only)."""
        if not self.loaded:
            err = self.load(doc)
            if err:
                return err
            self.loaded = True
        self.body = json.dumps(doc).encode()
        self.errors.clear()
        err = self.page.evaluate(REEVAL, [self.cut.film_js, self.cut.inline])
        return err or (f"page error: {self.errors[0]}" if self.errors else None)

    def replay(self) -> dict:
        r = self.page.evaluate(REPLAY, [self.cut.total, self.cut.fps])
        if self.errors and "error" not in r:
            r["error"] = f"page error: {self.errors[0]}"
        return r

    def pixels(self, i: int) -> str:
        self.page.evaluate(SEEK_AND_SETTLE, i / self.cut.fps)
        data = base64.b64decode(self.cdp.send("Page.captureScreenshot", self.capture_options)["data"])
        render_film.validate_frame_size(data, self.cut.W, self.cut.H)
        return hashlib.sha256(data).hexdigest()

    def frame_hashes(self) -> list[str]:
        self.page.evaluate("window.__film.resetOverflows()")
        return [self.pixels(i) for i in range(self.cut.total)]


def page_text(doc: dict, gated: bool) -> dict | str:
    """The watch pages generate_film_pages.py would write from these facts, or its refusal."""
    import generate_film_pages as gfp
    if not hasattr(gfp.sha, "cache_info"):  # file hashes cannot change during the test; the facts are what vary
        gfp.sha = functools.lru_cache(maxsize=None)(gfp.sha)
    saved = gfp.facts_digest.stale
    if not gated:
        gfp.facts_digest.stale = lambda receipt, facts: None
    try:
        return {str(p.relative_to(ROOT)): text for p, text in gfp.build(facts=doc["facts"]).items()}
    except ValueError as exc:
        return f"refused: {exc}"
    finally:
        gfp.facts_digest.stale = saved


def page_phase(doc: dict, committed: dict) -> dict:
    """Watch pages depend on the facts only through the staleness gate, or they fail here."""
    primary_used = {}
    for m in sorted(FILMS.glob("*/manifest.yaml")):
        slug = m.parent.name
        r = json.loads((m.parent / "renders" / f"{slug}__{yaml_primary(slug)}.receipt.json").read_text())
        primary_used[slug] = set(r["facts_used"])
    res = {"facts": {}, "fail": []}
    variants = [(fid, level) for fid in sorted(doc["facts"]) for level in (1, 2)] + [(None, "non-value")]
    for fid, level in variants:
        if fid is None:
            mdoc = meta_mutation(doc)
        else:
            mdoc = with_value(doc, fid, mutated_value(doc["facts"][fid]["value"], level))
        readers = sorted(s for s, used in primary_used.items() if fid in used)
        gated, open_ = page_text(mdoc, True), page_text(mdoc, False)
        key = f"{fid or 'non-value fields'} [{level}]"
        if isinstance(open_, str) or open_ != committed:
            changed = [k for k in committed if isinstance(open_, str) or open_.get(k) != committed[k]]
            res["fail"].append(f"{key}: page text changed with the staleness gate disabled: {changed}")
        if readers:
            if not (isinstance(gated, str) and any(f"{s}: render is stale" in gated for s in readers)):
                res["fail"].append(f"{key}: read by {readers}, but the page generator did not refuse")
            verdict = "refused (read by a primary render)"
        else:
            if gated != committed:
                res["fail"].append(f"{key}: no primary render reads it, yet the generator gave {str(gated)[:120]}")
            verdict = "unchanged"
        res["facts"][key] = {"readers": readers, "gated": verdict if not isinstance(gated, dict) or not readers else "published"}
    return res


def run_cut(browser, port: int, cut: Cut, doc: dict, full_capture: bool = True) -> dict:
    t0 = time.time()
    facts = doc["facts"]
    res = {"cut": cut.name, "receipt": str(cut.path.relative_to(ROOT)), "facts_used": sorted(cut.used),
           "frames": cut.total, "facts": {}, "fail": [], "warn": []}

    # 1. pixels, the whole timeline, every unused fact mutated at once, uninstrumented and loaded as
    #    render_film.py loads it. Equal to the receipt, its per-frame hashes are the render's own.
    true_px = None
    if full_capture:
        mdoc = copy.deepcopy(doc)
        for fid in facts:
            if fid not in cut.used:
                mdoc["facts"][fid]["value"] = mutated_value(facts[fid]["value"], 1)
        px = Stage(browser, port, cut, instrumented=False)
        err = px.load(mdoc)
        hashes = None if err else px.frame_hashes()
        px.page.close()
        fd = hashlib.sha256("".join(hashes).encode()).hexdigest() if hashes else None
        res["all_unused_mutated"] = {"facts_mutated": len(facts) - len(cut.used), "error": err, "frames_digest": fd,
                                     "receipt_frames_digest": cut.receipt["frames_digest"],
                                     "equal": fd == cut.receipt["frames_digest"]}
        if fd == cut.receipt["frames_digest"]:
            true_px = hashes
        else:
            res["fail"].append(f"frames_digest with every unused fact mutated is {fd}, receipt has {cut.receipt['frames_digest']}")

    t_capture = time.time() - t0
    # 2. the command stream. A loaded film and a re-evaluated one must replay the same stream, twice.
    st = Stage(browser, port, cut, instrumented=True)
    if st.load(doc):
        raise SystemExit(f"{cut.name}: unmutated film would not start")
    st.loaded = True
    loaded = st.replay()
    base = []
    for _ in range(2):
        err = st.fresh(doc)
        if err:
            raise SystemExit(f"{cut.name}: unmutated film would not re-evaluate: {err}")
        base.append(st.replay())
    if not (loaded["frames"] == base[0]["frames"] == base[1]["frames"]):
        res["fail"].append("command stream differs between unmutated replays (loaded, re-evaluated, re-evaluated)")
    if sorted(base[0]["used"]) != sorted(cut.used) or sorted(loaded["used"]) != sorted(cut.used):
        res["fail"].append(f"runtime facts_used {base[0]['used']} differs from the receipt {sorted(cut.used)}")
    for label, r in (("loaded", loaded), ("re-evaluated", base[0])):
        reads = r["reads"]
        if sorted(reads["facts"]) != sorted(cut.used):
            res["fail"].append(f"{label}: facts touched by any path {sorted(reads['facts'])} != facts_used {sorted(cut.used)}")
        beyond = {f: v for f, v in reads["facts"].items() if set(v) - {"value"}}
        if beyond or set(reads["top"]) - {"facts"} or reads["enumerated"]:
            res["fail"].append(f"{label}: reads beyond fact values: fields {beyond}, top-level {reads['top']}, enumerated {reads['enumerated']}")
    res["reads"] = base[0]["reads"]
    ref = base[0]["frames"]
    base_px: dict[int, str] = {}

    def compare(r: dict) -> dict:
        if r.get("error"):
            return {"changed": True, "error": r["error"], "frames_changed": None, "diff": []}
        diff = [i - 1 for i, (a, b) in enumerate(zip(ref, r["frames"])) if a != b]  # -1 = load/setup
        out = {"changed": bool(diff), "frames_changed": len(diff), "first": diff[0] if diff else None, "diff": diff}
        if sorted(r["used"]) != sorted(cut.used):
            out["used_under_mutation"] = r["used"]
        return out

    def pixels_differ(mdoc: dict, frames: list[int]) -> bool:
        need = [i for i in frames if i not in base_px]
        if need:  # the unmutated side, on the same re-evaluated page
            st.fresh(doc)
            for i in need:
                base_px[i] = st.pixels(i)
                if true_px is not None and base_px[i] != true_px[i]:
                    res["fail"].append(f"frame {i}: re-evaluated capture differs from the render's own pixels")
        st.fresh(mdoc)
        return any(st.pixels(i) != base_px[i] for i in frames)

    bound = (cut.receipt.get("facts_subset") or {}).get("sha256") or facts_digest.digest(facts, sorted(cut.used))
    if bound != facts_digest.digest(facts, sorted(cut.used)):
        res["fail"].append("receipt facts_subset does not match the current facts")

    # 3. one fact at a time
    for fid in sorted(facts):
        used = fid in cut.used
        entry = {"used": used, "levels": []}
        for level in (1, 2):
            mdoc = with_value(doc, fid, mutated_value(facts[fid]["value"], level))
            err = st.fresh(mdoc)
            c = {"changed": True, "error": err, "frames_changed": None, "diff": []} if err else compare(st.replay())
            c["level"] = level
            c["subset_stale"] = facts_digest.digest(mdoc["facts"], sorted(cut.used)) != bound
            diff = sorted({max(0, i) for i in c.pop("diff")})
            if c["changed"] and used and not c.get("error"):
                sample = diff if len(diff) <= PIXEL_SAMPLE else \
                    sorted({diff[round(k * (len(diff) - 1) / (PIXEL_SAMPLE - 1))] for k in range(PIXEL_SAMPLE)})
                c["pixel_frames"] = len(sample)
                c["pixels_changed"] = pixels_differ(mdoc, sample)
                if not c["pixels_changed"] and len(sample) < len(diff):
                    c["pixel_frames"] = len(diff)
                    c["pixels_changed"] = pixels_differ(mdoc, diff)
            entry["levels"].append(c)
            if c["changed"] and (not used or c.get("error") or c.get("pixels_changed")):
                break  # visible for a used fact; already a FAIL for an unused one
        changed = any(lv["changed"] for lv in entry["levels"])
        visible = any(lv.get("error") or lv.get("pixels_changed") for lv in entry["levels"])
        entry["verdict"] = "FAIL" if changed and not used else "WARN" if used and not visible else "ok"
        if entry["verdict"] == "FAIL":
            lv = entry["levels"][-1]
            res["fail"].append(f"{fid}: output changed but it is not in facts_used ({lv.get('error') or str(lv['frames_changed']) + ' frames'})")
        elif entry["verdict"] == "WARN":
            res["warn"].append(f"{fid}: in facts_used, but no mutation changed the pixels")
        for lv in entry["levels"]:
            if lv["changed"] and not lv["subset_stale"]:
                res["fail"].append(f"{fid}: output changed but the subset digest did not")
        res["facts"][fid] = entry

    # 4. fields the digest ignores, all at once
    err = st.fresh(meta_mutation(doc))
    c = {"changed": True, "error": err} if err else compare(st.replay())
    c.pop("diff", None)
    res["non_value_fields"] = c
    if c["changed"]:
        res["fail"].append(f"output changed when only non-value fields and top-level keys changed: {c}")
    st.page.close()
    res["seconds"] = round(time.time() - t0, 1)
    res["seconds_full_capture"] = round(t_capture, 1)
    res["pixel_frames_captured"] = len(base_px) + sum(lv.get("pixel_frames", 0) for e in res["facts"].values() for lv in e["levels"])
    return res


def summarize(results: list[dict], pages: dict | None, n_facts: int) -> int:
    print(f"\n{'cut':<44} {'used':>4} {'unused':>6} {'unused changed':>14} {'used visible':>12} {'WARN':>4} {'non-value':>9}  all-unused frames_digest")
    fails = warns = 0
    for r in sorted(results, key=lambda r: r["cut"]):
        used = len(r["facts_used"])
        unused_changed = sum(1 for e in r["facts"].values() if not e["used"] and e["verdict"] == "FAIL")
        vis = sum(1 for e in r["facts"].values() if e["used"] and e["verdict"] == "ok")
        nv = "changed" if r["non_value_fields"]["changed"] else "same"
        fd = "not run" if "all_unused_mutated" not in r else "= receipt" if r["all_unused_mutated"]["equal"] else "DIFFERS"
        print(f"{r['cut']:<44} {used:>4} {len(r['facts']) - used:>6} {unused_changed:>14} {vis:>9}/{used:<2} {len(r['warn']):>4} {nv:>9}  {fd}")
        fails += len(r["fail"])
        warns += len(r["warn"])
    runs = sum(len(e["levels"]) for r in results for e in r["facts"].values())
    print(f"\n{len(results)} cuts × {n_facts} facts: {runs} single-fact mutation replays over "
          f"{sum(r['frames'] for r in results)} frames a sweep; {len(results)} full pixel captures")
    if pages is not None:
        refused = sum(1 for v in pages["facts"].values() if v["readers"])
        print(f"watch pages: {len(pages['facts'])} mutated facts files; {refused} refused by the staleness gate "
              f"(fact read by a primary render), the rest published byte-identical; with the gate disabled every page "
              f"was byte-identical: {'yes' if not any('gate disabled' in f for f in pages['fail']) else 'NO'}")
        fails += len(pages["fail"])
        for f in pages["fail"]:
            print(f"FAIL  watch pages: {f}")
    for r in results:
        for f in r["fail"]:
            print(f"FAIL  {r['cut']}: {f}")
        for w in r["warn"]:
            print(f"WARN  {r['cut']}: {w}")
    print(f"\n{fails} FAIL, {warns} WARN")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shard", default="0/1", help="i/n: run every n-th cut starting at i")
    ap.add_argument("--cuts", nargs="*", help="receipt stems, e.g. parity-cube__master")
    ap.add_argument("--pages", action="store_true", help="run the watch-page phase (no browser)")
    ap.add_argument("--no-full-capture", action="store_true", help="skip the whole-timeline pixel capture (probing only)")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--merge", nargs="*", type=Path)
    args = ap.parse_args()
    doc = json.loads(FACTS.read_text())
    if args.merge:
        parts = [json.loads(p.read_text()) for p in args.merge]
        pages = next((p["pages"] for p in parts if p.get("pages")), None)
        return summarize([r for p in parts for r in p["results"]], pages, len(doc["facts"]))

    sys.path.insert(0, str(ROOT / "scripts"))
    out = {"facts_sha256": hashlib.sha256(FACTS.read_bytes()).hexdigest(), "results": [], "pages": None}
    if args.pages:
        committed = {str(p.relative_to(ROOT)): p.read_text() for p in page_targets()}
        if page_text(doc, True) != committed:
            raise SystemExit("watch pages do not regenerate from the committed facts; fix that first")
        out["pages"] = page_phase(doc, committed)
        if args.out:
            args.out.write_text(json.dumps(out, indent=1) + "\n")
        return summarize([], out["pages"], len(doc["facts"]))
    cuts = [Cut(p) for p in sorted(FILMS.glob("*/renders/*.receipt.json"))]
    if args.cuts:
        cuts = [c for c in cuts if c.path.name.removesuffix(".receipt.json") in args.cuts]
    i, n = map(int, args.shard.split("/"))
    cuts = cuts[i::n]
    from playwright.sync_api import sync_playwright
    srv, port = render_film.serve_root()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="chrome", args=render_film.CHROME_ARGS)
            for cut in cuts:
                print(f"  {cut.name}: {cut.total} frames, {len(cut.used)} facts used", flush=True)
                r = run_cut(browser, port, cut, doc, full_capture=not args.no_full_capture)
                r["chrome"] = browser.version
                fd = r.get("all_unused_mutated", {}).get("equal")
                print(f"    {len(r['fail'])} FAIL, {len(r['warn'])} WARN, all-unused frames_digest "
                      f"{'not run' if fd is None else '= receipt' if fd else 'DIFFERS'} · {r['seconds']}s", flush=True)
                out["results"].append(r)
                if args.out:
                    args.out.write_text(json.dumps(out, indent=1) + "\n")
            browser.close()
    finally:
        srv.shutdown()
    return summarize(out["results"], None, len(doc["facts"]))


def page_targets() -> list[Path]:
    return [FILMS / "index.html", *sorted(p.parent / "index.html" for p in FILMS.glob("*/manifest.yaml"))]


if __name__ == "__main__":
    sys.exit(main())
