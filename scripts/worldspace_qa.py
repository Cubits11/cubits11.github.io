#!/usr/bin/env python3
"""Capture WORLDSPACE's critical states through real input and write a receipt.

    ~/.venvs/cubits-films/bin/python scripts/worldspace_qa.py [--poster-only]

Serves the repository root over localhost, opens /worldspace/ in the installed
Chrome (Playwright, channel=chrome), and drives the page the way a visitor
would: types a prediction, commits, drags a ring with the mouse, presses the
stepper, uses the range input from the keyboard, opens the field, flips the
assumption switch, continues to the exit. At every declared critical state it
asserts the DOM invariants (both score readouts read 10; BOTH MISS reads the
expected count; the witness stamps at the endpoints; the independence marker;
no horizontal overflow; no halt), screenshots the viewport, and records the
state. Runs every declared viewport with and without prefers-reduced-motion,
a keyboard-only pass, a light-theme pass, a determinism check (two runs, same
inputs, same state), a performance measurement over the local server, and the
1200×630 poster. The receipt names the sha256 of every input so
scripts/verify_worldspace.py can refuse a stale capture.

Nothing here is a test of comprehension. It proves what was rendered.
"""

from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
QA = ROOT / "worldspace" / "qa"
MANIFEST = ROOT / "worldspace" / "manifest.yaml"
INPUTS = ("worldspace/index.html", "worldspace/worldspace.js", "worldspace/manifest.yaml")
MANIFEST_DOC = yaml.safe_load(MANIFEST.read_text())


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git_head() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve() -> tuple[socketserver.TCPServer, int]:
    handler = lambda *a, **kw: Quiet(*a, directory=str(ROOT), **kw)  # noqa: E731
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def state(page) -> dict:
    return page.evaluate("window.__ws.state()")


def readouts(page) -> dict:
    return page.evaluate("""() => ({
      a: document.querySelector('[data-readout="a"]').textContent,
      b: document.querySelector('[data-readout="b"]').textContent,
      both: document.querySelector('[data-readout="both"]').textContent,
      act: document.getElementById('ws').getAttribute('data-act'),
      stamp: (function(s){return s.hidden ? null : s.textContent})(document.getElementById('ws-stamp')),
      invariant: !document.getElementById('ws-invariant').hidden,
      indep: !document.getElementById('ws-mark-ind').hidden,
      predTxt: (function(m){return m.hidden ? null : document.getElementById('ws-pred-txt').textContent})(document.getElementById('ws-mark-pred')),
      assumeChecked: document.getElementById('ws-assume').getAttribute('aria-checked'),
      exitVisible: getComputedStyle(document.getElementById('exit')).display !== 'none',
      overflow: document.scrollingElement.scrollWidth <= window.innerWidth + 1,
      halted: !!document.querySelector('.ws-halt'),
      js: document.documentElement.classList.contains('ws-js'),
      staticHidden: getComputedStyle(document.getElementById('ws-static')).display === 'none'
    })""")


def base_assertions(r: dict, expect_both: int | None, act: str) -> dict:
    a = {
        "readout_a_is_10": r["a"] == "10",
        "readout_b_is_10": r["b"] == "10",
        "act": r["act"] == act,
        "no_horizontal_overflow": r["overflow"],
        "not_halted": not r["halted"],
        "js_active": r["js"],
        "static_proof_hidden_when_js": r["staticHidden"],
    }
    if expect_both is not None:
        a["both_reads_expected"] = r["both"] == str(expect_both)
    return a


def drag_ring(page, ring_index: int, target_cell: int, side: int = 10) -> None:
    ring = page.locator(f'.ws-ring[data-ring="{ring_index}"]')
    box = ring.bounding_box()
    sheet = page.locator("#ws-sheet").bounding_box()
    cell = sheet["width"] / side
    tx = sheet["x"] + (target_cell % side) * cell + cell / 2
    ty = sheet["y"] + (target_cell // side) * cell + cell / 2
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] / 2 + 8, box["y"] + box["height"] / 2 + 8, steps=3)
    page.mouse.move(tx, ty, steps=12)
    page.mouse.up()


def wait_settled(page, timeout_ms: int = 6000) -> None:
    page.wait_for_function("window.__ws.state().settled && window.__ws.state().indep", timeout=timeout_ms)


def run_pass(pw, port: int, name: str, vp: tuple[int, int], reduced: bool, captures: list, shots: bool,
             color_scheme: str = "dark", keyboard_only: bool = False, theme: str | None = None,
             console_errors: list | None = None, page_errors: list | None = None) -> dict:
    browser = pw.chromium.launch(channel="chrome", args=["--force-color-profile=srgb", "--font-render-hinting=none", "--hide-scrollbars", "--disable-lcd-text"])
    ctx = browser.new_context(viewport={"width": vp[0], "height": vp[1]}, device_scale_factor=1,
                              reduced_motion="reduce" if reduced else "no-preference", color_scheme=color_scheme,
                              is_mobile=vp[0] < 600, has_touch=vp[0] < 600)
    if theme:
        ctx.add_init_script(f"try{{localStorage.setItem('theme','{theme}')}}catch(e){{}}")
    page = ctx.new_page()
    if console_errors is not None:
        page.on("console", lambda m: console_errors.append(f"{name}: {m.text}") if m.type == "error" and "favicon" not in m.text else None)
    if page_errors is not None:
        page.on("pageerror", lambda e: page_errors.append(f"{name}: {e}"))
    page.goto(f"http://127.0.0.1:{port}/worldspace/", wait_until="load")
    page.wait_for_function("document.documentElement.classList.contains('ws-js')", timeout=15000)
    page.wait_for_function("document.fonts.status === 'loaded'", timeout=15000)
    tag = f"{name}{'-rm' if reduced else ''}"
    A = page.evaluate("window.__ws.state().a")

    def shot(state_id: str, expect_both, act: str, extra: dict | None = None) -> None:
        if state_id != "exit":
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(60)
        r = readouts(page)
        asserts = base_assertions(r, expect_both, act)
        if extra:
            asserts.update(extra)
        st = state(page)
        file = f"{state_id}__{tag}.jpg"
        declared = any(cs["id"] == state_id and name in cs["viewports"] and reduced in [bool(x) for x in cs["reduced_motion"]]
                       for cs in MANIFEST_DOC["critical_states"]) or (name == "desktop-light" and state_id == "field")
        if shots and declared:
            page.screenshot(path=str(QA / file), type="jpeg", quality=82, full_page=False)
        elif not declared:
            file = None
        captures.append({"state": state_id, "viewport": name, "reduced_motion": reduced, "file": file, "act": r["act"],
                         "both": r["both"], "a": r["a"], "b": r["b"], "stamp": r["stamp"], "assertions": asserts,
                         "prediction": st["prediction"], "visited": st["visited"], "assume": st["assume"]})
        bad = [k for k, v in asserts.items() if v is not True]
        print(f"  {state_id:10s} @ {tag:16s} both={r['both']:>2s} a={r['a']} b={r['b']} {'OK' if not bad else 'FAIL ' + str(bad)}")

    # ---- predict
    shot("predict", None, "predict", {"both_hidden": page.locator("#ro-both").is_hidden(), "question_visible": page.locator("#q-h").is_visible()})
    if keyboard_only:
        page.keyboard.press("Tab")
        while page.evaluate("document.activeElement && document.activeElement.id") != "ws-guess":
            page.keyboard.press("Tab")
        page.keyboard.type("1")
        page.keyboard.press("Enter")
    else:
        page.fill("#ws-guess", "1")
        page.click("#ws-commit")
    page.wait_for_function("window.__ws.state().act === 'touch'")
    # ---- touch-0: the lower endpoint witness is the opening state
    r = readouts(page)
    shot("touch-0", 0, "touch", {"lower_witness_stamped": r["stamp"] == "LOWER ENDPOINT · WITNESS", "invariant_hidden_before_change": not r["invariant"]})
    # ---- one ring onto a disc, by drag (or by keyboard hop)
    if keyboard_only:
        page.focus('.ws-ring[data-ring="0"]')
        page.keyboard.press("Enter")
    else:
        drag_ring(page, 0, A[0])
    page.wait_for_function("window.__ws.state().q === 1")
    r = readouts(page)
    asserts_after_one = {"invariant_shown_after_change": r["invariant"], "scores_unchanged_after_change": r["a"] == "10" and r["b"] == "10"}
    # ---- to 5 with the stepper (or the keyboard on the range)
    if keyboard_only:
        page.focus("#ws-range")
        for _ in range(4):
            page.keyboard.press("ArrowRight")
    else:
        for _ in range(4):
            page.click("#ws-plus")
    page.wait_for_function("window.__ws.state().q === 5")
    shot("touch-5", 5, "touch", dict(asserts_after_one, **{"no_stamp_midway": readouts(page)["stamp"] is None, "name_visible": page.locator("#ws-name").is_visible()}))
    # ---- to 10 with the range (keyboard End)
    page.focus("#ws-range")
    page.keyboard.press("End")
    page.wait_for_function("window.__ws.state().q === 10")
    r = readouts(page)
    shot("touch-10", 10, "touch", {"upper_witness_stamped": r["stamp"] == "UPPER ENDPOINT · WITNESS", "open_visible": page.locator("#ws-open").is_visible()})
    # ---- back to 3 so the visitor's world sits away from the independence column in the field
    page.focus("#ws-range")
    page.keyboard.press("Home")
    page.wait_for_function("window.__ws.state().q === 0")
    for _ in range(3):
        page.keyboard.press("ArrowRight")
    page.wait_for_function("window.__ws.state().q === 3")
    # ---- open the field
    page.click("#ws-open")
    wait_settled(page)
    page.wait_for_timeout(120 if reduced else 650)
    r = readouts(page)
    shot("field", 3, "field", {"canvas_visible": page.locator("#ws-canvas").is_visible(), "independence_marker": r["indep"],
                               "prediction_marker": r["predTxt"] == "YOU PREDICTED 1 · the point independence selects",
                               "your_world_marker": page.locator("#ws-mark-world .txt").is_visible(), "field_title": page.locator("#field-h").is_visible(),
                               "count_line": page.locator("#ws-count").is_visible(), "switch_visible": page.locator("#ws-assume").is_visible()})
    # ---- move the world with the field range (keyboard)
    page.focus("#ws-range2")
    page.keyboard.press("ArrowRight")
    page.wait_for_function("window.__ws.state().q === 4")
    r = readouts(page)
    moved_ok = r["both"] == "4" and r["a"] == "10" and r["b"] == "10"
    page.keyboard.press("ArrowLeft")
    page.wait_for_function("window.__ws.state().q === 3")
    # ---- assume independence
    page.click("#ws-assume")
    page.wait_for_function("window.__ws.state().assume === true")
    page.wait_for_timeout(50 if reduced else 520)
    r = readouts(page)
    shot("assume", 3, "field", {"switch_on": r["assumeChecked"] == "true", "axis_collapsed": page.evaluate("document.getElementById('ws-axis').classList.contains('collapsed')"),
                                "assume_text": page.locator("#ws-assume-text").is_visible(), "world_moved_in_field": moved_ok,
                                "excluded_named": "EXCLUDED BY THE ASSUMPTION" in page.locator("#ws-assume-text").inner_text()})
    page.click("#ws-assume")
    page.wait_for_function("window.__ws.state().assume === false")
    reopened = page.evaluate("!document.getElementById('ws-axis').classList.contains('collapsed') && document.getElementById('ws-assume-text').hidden")
    # ---- inspector
    page.click("#ws-inspect")
    inspector_ok = page.locator("#ws-inspector").is_visible() and "BOTH 3 / 100" in page.locator("#ws-spec-cap").inner_text()
    page.click("#ws-back")
    # ---- exit
    page.click("#ws-continue")
    page.wait_for_timeout(100 if reduced else 700)
    page.wait_for_function("getComputedStyle(document.getElementById('exit')).display !== 'none'")
    page.evaluate("document.getElementById('exit').scrollIntoView({behavior:'auto', block:'start'})")
    page.wait_for_timeout(80)
    r = readouts(page)
    shot("exit", 3, "field", {"exit_visible": r["exitVisible"], "reopened_after_release": reopened, "inspector": inspector_ok,
                              "primary_route": page.locator('a[href="/try/#try-a"]').count() >= 1,
                              "final_line_present": "MATCH  TRY-A" in page.content() or "MATCH TRY-A" in page.locator("#exit").inner_text(),
                              "boundaries_present": page.locator("details.ws-bound").count() == 1})
    final_state = state(page)
    ctx.close()
    browser.close()
    return final_state


def measure_performance(pw, port: int) -> dict:
    browser = pw.chromium.launch(channel="chrome")
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    reqs: list[dict] = []

    def on_response(resp):
        try:
            body = resp.body()
            reqs.append({"url": resp.url, "type": resp.request.resource_type, "bytes": len(body)})
        except Exception:
            reqs.append({"url": resp.url, "type": resp.request.resource_type, "bytes": None})
    page.on("response", on_response)
    t0 = time.time()
    page.goto(f"http://127.0.0.1:{port}/worldspace/", wait_until="load")
    page.wait_for_function("document.documentElement.classList.contains('ws-js')")
    page.wait_for_timeout(300)
    paint = page.evaluate("(performance.getEntriesByType('paint').find(e=>e.name==='first-contentful-paint')||{}).startTime || null")
    dcl = page.evaluate("performance.timing.domContentLoadedEventEnd - performance.timing.navigationStart")
    fonts = [r for r in reqs if r["type"] == "font" or r["url"].endswith(".woff2")]
    third = [r for r in reqs if "127.0.0.1" not in r["url"]]
    images = [r for r in reqs if r["type"] == "image" and "favicon" not in r["url"]]
    html_bytes = len((ROOT / "worldspace" / "index.html").read_bytes())
    js_bytes = len((ROOT / "worldspace" / "worldspace.js").read_bytes())
    total = sum(r["bytes"] or 0 for r in reqs)
    ctx.close()
    browser.close()
    return {"html_bytes": html_bytes, "js_bytes": js_bytes, "total_transfer_bytes_local": total,
            "requests": len(reqs), "font_files_loaded": len(fonts), "new_font_files": 0,
            "third_party_requests": len(third), "images_fetched_on_load": len(images),
            "first_contentful_paint_ms": paint, "dom_content_loaded_ms": dcl, "wall_ms": round((time.time() - t0) * 1000)}


def poster(pw, port: int) -> None:
    browser = pw.chromium.launch(channel="chrome", args=["--force-color-profile=srgb", "--font-render-hinting=none", "--hide-scrollbars"])
    ctx = browser.new_context(viewport={"width": 1200, "height": 630}, device_scale_factor=1, reduced_motion="reduce", color_scheme="dark")
    page = ctx.new_page()
    page.goto(f"http://127.0.0.1:{port}/worldspace/", wait_until="load")
    page.wait_for_function("document.documentElement.classList.contains('ws-js')")
    page.wait_for_function("document.fonts.status === 'loaded'")
    page.fill("#ws-guess", "1")
    page.click("#ws-commit")
    page.evaluate("window.__ws.setBoth(3)")
    page.click("#ws-open")
    wait_settled(page)
    page.evaluate("document.querySelector('.site-head').style.display='none'; window.__ws.poster(); window.scrollTo(0,0)")
    page.wait_for_timeout(150)
    page.screenshot(path=str(QA / "poster-1200x630.png"), type="png", clip={"x": 0, "y": 0, "width": 1200, "height": 630})
    ctx.close()
    browser.close()
    print("  poster-1200x630.png written")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--poster-only", action="store_true")
    ap.add_argument("--no-shots", action="store_true", help="assert only; do not overwrite screenshots")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright
    m = yaml.safe_load(MANIFEST.read_text())
    QA.mkdir(parents=True, exist_ok=True)
    if not args.poster_only and not args.no_shots:
        for old_shot in QA.glob("*.jpg"):
            old_shot.unlink()
    srv, port = serve()
    console_errors: list[str] = []
    page_errors: list[str] = []
    captures: list[dict] = []
    t_start = time.time()
    try:
        with sync_playwright() as pw:
            if args.poster_only:
                poster(pw, port)
                return 0
            for name, vp in m["viewports"].items():
                for reduced in (False, True):
                    # only viewports the manifest asks for in reduced motion get a second pass
                    wanted = any(name in cs["viewports"] and reduced in [bool(x) for x in cs["reduced_motion"]] for cs in m["critical_states"])
                    if not wanted:
                        continue
                    print(f"pass {name} {vp} reduced_motion={reduced}")
                    run_pass(pw, port, name, tuple(vp), reduced, captures, not args.no_shots,
                             console_errors=console_errors, page_errors=page_errors)
            print("pass keyboard-only @ desktop")
            kb_caps: list[dict] = []
            run_pass(pw, port, "desktop", tuple(m["viewports"]["desktop"]), False, kb_caps, False, keyboard_only=True,
                     console_errors=console_errors, page_errors=page_errors)
            keyboard_ok = all(all(v is True for v in c["assertions"].values()) for c in kb_caps)
            print("pass light theme @ desktop")
            light_caps: list[dict] = []
            run_pass(pw, port, "desktop-light", tuple(m["viewports"]["desktop"]), False, light_caps, not args.no_shots, color_scheme="light", theme="light",
                     console_errors=console_errors, page_errors=page_errors)
            print("determinism: two identical desktop runs")
            s1 = run_pass(pw, port, "desktop", tuple(m["viewports"]["desktop"]), True, [], False, console_errors=console_errors, page_errors=page_errors)
            s2 = run_pass(pw, port, "desktop", tuple(m["viewports"]["desktop"]), True, [], False, console_errors=console_errors, page_errors=page_errors)
            for s in (s1, s2):
                s.pop("reduced", None)
            print("performance over the local server")
            perf = measure_performance(pw, port)
            poster(pw, port)
    finally:
        srv.shutdown()
    receipt = {
        "instrument": "worldspace", "captured": time.strftime("%Y-%m-%d"), "git_head": git_head(),
        "inputs": {rel: sha256_file(ROOT / rel) for rel in INPUTS},
        "captures": captures + light_caps,
        "keyboard_only_pass": keyboard_ok,
        "determinism": {"identical": s1 == s2, "state": s1},
        "performance": perf, "console_errors": console_errors, "page_errors": page_errors,
        "wall_seconds": round(time.time() - t_start, 1),
    }
    (QA / "receipt.json").write_text(json.dumps(receipt, indent=1) + "\n")
    bad = [c for c in captures if any(v is not True for v in c["assertions"].values())]
    print(f"\nreceipt written: {len(captures)} captures, keyboard-only {'ok' if keyboard_ok else 'FAILED'}, "
          f"determinism {'ok' if s1 == s2 else 'FAILED'}, console errors {len(console_errors)}, page errors {len(page_errors)}, "
          f"html {perf['html_bytes']} B, js {perf['js_bytes']} B, FCP {perf['first_contentful_paint_ms']} ms")
    if bad or page_errors or not keyboard_ok or s1 != s2:
        print("QA FAILED")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
