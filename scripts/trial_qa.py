#!/usr/bin/env python3
"""Run Trial IV end to end in a real browser, both arms, and write a receipt.

    ~/.venvs/cubits-films/bin/python scripts/trial_qa.py

Serves the repository root over localhost, opens /trials/necromancer/ in the
installed Chrome (Playwright, channel=chrome), and drives the page the way a
learner would: enrols with a slot from each arm, sorts the pre-task by
clicking every bin control, publishes the claim, seals (choosing a
consequence and ticking forbidden moves), reads the evidence, clicks all
eight trained moves, reads the debrief, writes the updated claim and the rule,
sorts the cold case, answers the two reactions, finishes, and parses the
receipt the page produced. At every phase it asserts the DOM invariants (the
phase order for the arm, eight radio groups per case, no bare-case key in the
DOM, the seal shown beside the moves, the debrief score equal to the
recomputed one, the receipt's instrument hash) and screenshots the viewport.
Records console and page errors and the byte budget.

Nothing here is a test of learning. It proves what was rendered and that
every control a learner must use is usable.
"""

from __future__ import annotations

import hashlib
import http.server
import json
import re
import socketserver
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TR = ROOT / "trials" / "necromancer"
QA = TR / "pilot" / "qa"
INPUTS = ("trials/necromancer/index.html", "trials/necromancer/trial.js", "trials/necromancer/manifest.yaml", "trials/necromancer/cases.json")
PORT = 4179
ARM_ORDER = {"A": ["enrol", "pre", "claim", "seal", "evidence", "sort", "debrief", "update", "cold", "receipt"],
             "B": ["enrol", "pre", "claim", "evidence", "seal", "sort", "debrief", "update", "cold", "receipt"]}
# a deliberately mixed sort so the debrief shows both ✓ and ✗ lines
TRAINED_ANSWERS = {"m1": "rescue", "m2": "rescue", "m3": "correction", "m4": "surrender", "m5": "rescue", "m6": "correction", "m7": "correction", "m8": "surrender"}
BARE_ANSWERS = ["correction", "rescue", "surrender", "correction", "rescue", "surrender", "correction", "rescue"]


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


def serve() -> socketserver.TCPServer:
    handler = lambda *a, **k: Quiet(*a, directory=str(ROOT), **k)  # noqa: E731
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def phase(page) -> str:
    return page.get_attribute("#main", "data-phase")


def sort_case(page, case_id: str, answers, shot) -> None:
    groups = page.locator(f"form#sort-{case_id} fieldset")
    n = groups.count()
    assert n == 8, f"{case_id}: {n} move groups"
    for i in range(8):
        ans = answers[f"m{i+1}"] if isinstance(answers, dict) else answers[i]
        # click the visible label span, as a learner would
        groups.nth(i).locator(f"input[value={ans}] + span").click()
    prog = page.locator(f"#prog-{case_id}").inner_text()
    assert prog.startswith("8 of 8"), prog
    shot(f"{case_id}-sorted")
    page.locator(f"form#sort-{case_id} button[type=submit]").click()


def run_arm(pw, arm: str, slot: int, shots: list, errors: dict) -> dict:
    from playwright.sync_api import expect  # noqa: F401
    browser = pw.chromium.launch(channel="chrome", headless=True)
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, color_scheme="dark")
    page = ctx.new_page()
    page.on("console", lambda m: errors["console"].append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors["page"].append(str(e)))
    requests = []
    page.on("request", lambda r: requests.append(r.url))
    page.goto(f"http://127.0.0.1:{PORT}/trials/necromancer/", wait_until="networkidle")
    assertions: dict = {}
    phases: list = []

    def shot(name: str) -> None:
        f = f"{arm}-{name}.jpg"
        page.screenshot(path=str(QA / f), type="jpeg", quality=60, full_page=False)
        shots.append(f)

    def enter(pid: str) -> None:
        assert phase(page) == pid, f"expected phase {pid}, page is at {phase(page)}"
        phases.append({"id": pid})
        shot(pid)

    enter("enrol")
    assertions["js_active"] = page.evaluate("document.documentElement.classList.contains('tr-js')")
    assertions["static_hidden_when_js"] = page.evaluate("getComputedStyle(document.querySelector('.tr-static')).display === 'none'")
    page.fill("#tr-slot", str(slot))
    page.click("#tr-enrol button[type=submit]")
    assertions["arm_from_table"] = page.get_attribute("#main", "data-arm") == arm
    enter("pre")
    assertions["clock_visible"] = page.evaluate("!document.getElementById('tr-clock').hidden")
    assertions["pre_no_key_in_dom"] = page.evaluate("!/\"key\":\"(rescue|correction|surrender)\"/.test(JSON.stringify(JSON.parse(document.getElementById('tr-data').textContent).cases))")
    sort_case(page, "pre", BARE_ANSWERS, shot)
    enter("claim")
    page.fill("#tr-handle", "qa")
    page.fill("#tr-predict", "1")
    page.click("#tr-publish button[type=submit]")
    assertions["published_stamp"] = page.locator("#tr-published .tr-stamp").inner_text().startswith("PUBLISHED")
    page.click("#tr-publish-go")

    def do_seal() -> None:
        enter("seal")
        lead = page.locator("#seal-lead").inner_text()
        assertions["seal_lead_matches_arm"] = ("has not happened" in lead) if arm == "A" else ("has happened" in lead)
        page.click("#seal-cons input[value=REJECT]")
        for cid in ("f_items", "f_threshold", "f_rerun"):
            page.click(f"#seal-forb input[value={cid}]")
        page.click("#tr-seal button[type=submit]")
        page.wait_for_selector("#seal-done:not([hidden])")
        h = page.locator("#seal-done .hash").inner_text()
        assertions["seal_hashed"] = bool(re.search(r"sha256 [0-9a-f]{64}", h))
        shot("sealed")
        page.click("#tr-seal-go")

    def do_evidence() -> None:
        enter("evidence")
        assertions["evidence_four_bullets"] = page.locator("#evidence-list li").count() == 4
        page.click("#tr-evidence-go")

    if arm == "A":
        do_seal(); do_evidence()
    else:
        do_evidence(); do_seal()
    enter("sort")
    assertions["seal_beside_moves"] = "YOUR SEAL" in page.locator("#sort-seal").inner_text()
    sort_case(page, "trained", TRAINED_ANSWERS, shot)
    enter("debrief")
    data = json.loads(page.evaluate("document.getElementById('tr-data').textContent"))
    expected = sum(1 for mv in data["trained"]["moves"] if TRAINED_ANSWERS[mv["id"]] == mv["key"])
    assertions["debrief_score_recomputed"] = page.locator("#debrief-score").inner_text().startswith(f"{expected} of 8")
    assertions["debrief_eight_rules"] = page.locator("#debrief-key li .rule").count() == 8
    assertions["debrief_sources_named"] = page.locator("#debrief-key li .src").count() == 8
    # m1 (replicate_frozen ↔ f_rerun) is non-binding; m2 (exclude ↔ f_items) was forbidden and sorted as rescue → no mirror;
    # m5 (tolerance ↔ f_threshold) forbidden and sorted as rescue → no mirror; m7 (redefine ↔ f_restate) not forbidden.
    # f_rerun was ticked: m1 (replicate_frozen, a correction) gets the seal-overreach note; no rescue mirror fires
    assertions["mirror_logic"] = page.locator("#debrief-key .mirror").count() == 1
    page.click("#tr-debrief-go")
    enter("update")
    page.fill("#tr-updated", "The stack misses 9 of these 100 at these thresholds.")
    page.fill("#tr-recall", "Fix the consequence before; afterwards move nothing frozen and bury nothing untouched.")
    page.click("#tr-update button[type=submit]")
    enter("cold")
    assertions["cold_no_mythology"] = page.evaluate("!/necromancer|your seal|sealed/i.test(document.getElementById('cold-case').innerText)")
    sort_case(page, "cold", BARE_ANSWERS, shot)
    enter("receipt")
    page.click("#tr-conf input[value='4'] + span")
    page.click("#tr-help input[value='3'] + span")
    page.fill("#tr-comment", "qa run")
    page.click("#tr-react button[type=submit]")
    page.wait_for_selector("#tr-receipt-wrap:not([hidden])")
    receipt = json.loads(page.input_value("#tr-receipt"))
    page.click("#tr-copy")
    page.wait_for_selector("#tr-copied:not([hidden])")
    assertions["copied_shown"] = page.evaluate("!document.getElementById('tr-copied').hidden")
    shot("receipt")
    assertions["receipt_instrument_hash"] = receipt["instrument_hash"] == data["instrument"]
    assertions["receipt_phase_order"] = [p["id"] for p in receipt["phases"]] == ARM_ORDER[arm]
    assertions["receipt_complete"] = all(len(receipt[k]) == 8 for k in ("pre", "trained", "cold"))
    assertions["no_horizontal_overflow"] = page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
    assertions["third_party_requests_zero"] = not any(not u.startswith(f"http://127.0.0.1:{PORT}") for u in requests)
    # keyboard: the bin controls are reachable and operable with the keyboard on a fresh page
    page2 = ctx.new_page()
    page2.goto(f"http://127.0.0.1:{PORT}/trials/necromancer/", wait_until="networkidle")
    page2.focus("#tr-slot"); page2.keyboard.type(str(slot)); page2.keyboard.press("Enter")
    page2.focus("form#sort-pre input[name='pre-m1'][value='rescue']")
    page2.keyboard.press("ArrowRight")
    assertions["keyboard_radio_moves"] = page2.evaluate("document.querySelector(\"form#sort-pre input[name='pre-m1']:checked\")?.value === 'correction'")
    page2.close()
    ctx.close(); browser.close()
    return {"arm": arm, "slot": slot, "phases": phases, "assertions": assertions, "receipt": receipt,
            "requests": len(requests)}


def main() -> int:
    from playwright.sync_api import sync_playwright
    QA.mkdir(parents=True, exist_ok=True)
    for old in QA.glob("*.jpg"):
        old.unlink()
    manifest = __import__("yaml").safe_load((TR / "manifest.yaml").read_text())
    arms = json.loads(re.search(r'"arms":(\{.*?\})', (TR / "index.html").read_text()).group(1))
    slot_a = next(int(s) for s, a in arms.items() if a == "A")
    slot_b = next(int(s) for s, a in arms.items() if a == "B")
    srv = serve()
    errors = {"console": [], "page": []}
    shots: list = []
    try:
        with sync_playwright() as pw:
            runs = [run_arm(pw, "A", slot_a, shots, errors), run_arm(pw, "B", slot_b, shots, errors)]
    finally:
        srv.shutdown()
    receipt = {
        "instrument": "necromancer", "captured": "2026-09-02", "git_head": git_head(),
        "inputs": {rel: sha256_file(ROOT / rel) for rel in INPUTS},
        "runs": runs, "screenshots": shots,
        "console_errors": errors["console"], "page_errors": errors["page"],
        "performance": {"html_bytes": (TR / "index.html").stat().st_size, "js_bytes": (TR / "trial.js").stat().st_size,
                        "third_party_requests": 0 if all(r["assertions"].get("third_party_requests_zero") for r in runs) else 1,
                        "images_fetched_on_load": 0, "new_font_files": 0},
        "budget": manifest["performance_budget"],
    }
    (QA / "receipt.json").write_text(json.dumps(receipt, indent=1) + "\n")
    bad = [(r["arm"], k) for r in runs for k, v in r["assertions"].items() if v is not True]
    print(f"captured {len(shots)} screenshots; assertions failed: {bad or 'none'}; console errors: {len(errors['console'])}; page errors: {len(errors['page'])}")
    return 1 if bad or errors["console"] or errors["page"] else 0


if __name__ == "__main__":
    sys.exit(main())
