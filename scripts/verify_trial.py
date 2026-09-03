#!/usr/bin/env python3
"""Verify Trial IV (THE NECROMANCER) without a browser, and freeze its pilot.

    python3 scripts/verify_trial.py            # verify; exit 1 on any failure
    python3 scripts/verify_trial.py --freeze   # write trials/necromancer/pilot/freeze.json

What protects the experiment, and nothing else:

  * the manifest — the trained case has eight moves, split 3/3/2, one per
    template, no two adjacent moves sharing a key, the first not a rescue;
    every template's rule names a repository file and a phrase that is still
    in it; every mythic object carries an operation and a deletion test; the
    falsifier and non-claims exist;
  * the bare cases — pre and cold each carry eight moves and four evidence
    bullets, and neither the case file nor the page carries a key for them;
    the withheld key file, wherever it sits, hashes to the frozen digest and
    is itself well-formed (3/3/2, adjacency, first-not-rescue);
  * the arm table — recomputed from the frozen seed, five and five, equal to
    the table embedded in the page;
  * the text — every string the manifest declares appears in the page or the
    runtime; the runtime reads its strings from the page;
  * runtime hygiene — no network transport, no storage, no Math.random; the
    live region, the reduced-motion query, the receipt path;
  * the decision rule — the scorer's constants equal the manifest's;
  * the pilot freeze — every hashed input is unchanged since the freeze, and
    the QA receipt is fresh against the page, runtime and manifest, with every
    declared state captured for both arms and no console errors.

Exit 1 on any failure; exit 0 prints one summary line.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import generate_trial as gen  # noqa: E402

TR = ROOT / "trials" / "necromancer"
MANIFEST, CASES, PAGE, RUNTIME = TR / "manifest.yaml", TR / "cases.json", TR / "index.html", TR / "trial.js"
PILOT = TR / "pilot"
FREEZE, PILOT_MD, RECEIPT = PILOT / "freeze.json", PILOT / "PILOT.md", PILOT / "qa" / "receipt.json"
SCORER = ROOT / "scripts" / "trial_score.py"
KEY_LOCATIONS = (ROOT / "_private" / "necromancer" / "keys.json", PILOT / "keys.json")
FROZEN_INPUTS = ("trials/necromancer/manifest.yaml", "trials/necromancer/cases.json", "trials/necromancer/index.html",
                 "trials/necromancer/trial.js", "trials/necromancer/pilot/PILOT.md", "scripts/trial_score.py", "scripts/generate_trial.py")
KEYS = ("rescue", "correction", "surrender")
failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL  {msg}")


def ok(msg: str) -> None:
    print(f"ok    {msg}")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def key_file() -> Path | None:
    for p in KEY_LOCATIONS:
        if p.exists():
            return p
    return None


def check_manifest(m: dict) -> None:
    try:
        gen.check_moves("trained", m["trained"]["moves"], keyed=True)
    except AssertionError as e:
        fail(str(e))
    tpl = {x["id"]: x for x in m["templates"]}
    if len(tpl) != 8 or {x["key"] for x in m["templates"]} != set(KEYS):
        fail("eight templates across the three keys are required")
    for x in m["templates"]:
        for s in x["sources"]:
            p = ROOT / s["path"]
            if not p.exists():
                fail(f"template {x['id']}: source {s['path']} missing")
            elif s["quote"] not in p.read_text(encoding="utf-8"):
                fail(f"template {x['id']}: quoted rule drifted out of {s['path']}: {s['quote']!r}")
    for mo in m["mythic_objects"]:
        if not (mo.get("operation") and mo.get("deletion_test")):
            fail(f"mythic object {mo.get('object')!r} has no operation or deletion test — delete it or justify it")
    if not m.get("falsifier") or not m.get("non_claims"):
        fail("manifest must carry a falsifier and non_claims")
    dr = m["pilot"]["decision_rule"]
    for k in ("continue_if", "narrow_if", "kill_if", "conclude_only_if"):
        if not dr.get(k):
            fail(f"decision rule lacks {k}")
    if not failures:
        ok(f"manifest: trained case 3/3/2 across {len(tpl)} templates; {sum(len(x['sources']) for x in m['templates'])} rule sources still say what the page quotes; {len(m['mythic_objects'])} mythic objects justified")


def check_cases(cases: dict, html: str, freeze: dict | None) -> None:
    for c in cases["cases"]:
        try:
            gen.check_moves(c["id"], c["moves"], keyed=False)
        except AssertionError as e:
            fail(str(e))
    data = page_data(html)
    if data:
        for cid in ("pre", "cold"):
            for mv in data["cases"][cid]["moves"]:
                if set(mv) != {"id", "text"}:
                    fail(f"page leaks a field on bare case {cid} move {mv['id']}: {sorted(mv)}")
    kf = key_file()
    if kf is None:
        print("note  no key file present locally; the frozen digest stands unverified here")
    else:
        keys = json.loads(kf.read_text(encoding="utf-8"))
        for cid in ("pre", "cold"):
            k = keys["cases"].get(cid, {})
            seq = [k[f"m{i}"]["key"] for i in range(1, 9) if f"m{i}" in k]
            if len(seq) != 8:
                fail(f"key file: {cid} does not key eight moves")
                continue
            if {x: seq.count(x) for x in KEYS} != gen.SPLIT:
                fail(f"key file: {cid} is not 3/3/2")
            if any(a == b for a, b in zip(seq, seq[1:])) or seq[0] == "rescue":
                fail(f"key file: {cid} violates the adjacency or first-move rule")
            if len({k[f'm{i}']['template'] for i in range(1, 9)}) != 8:
                fail(f"key file: {cid} templates repeat")
        if freeze and freeze.get("keys_sha256") != sha256_file(kf):
            fail(f"key file {kf.relative_to(ROOT)} does not hash to the frozen digest")
    if not failures:
        ok("bare cases: pre and cold carry eight moves each; no key in the case file or the page" + ("; key file matches the frozen digest" if kf and freeze else ""))


def page_data(html: str) -> dict | None:
    mt = re.search(r'<script type="application/json" id="tr-data">(.*?)</script>', html, re.S)
    if not mt:
        fail("page carries no #tr-data block")
        return None
    return json.loads(mt.group(1).replace("<\\/", "</"))


def check_arms(m: dict, data: dict) -> None:
    p = m["pilot"]
    table = gen.arm_table(p["seed"], int(p["slots"]))
    if data["pilot"]["arms"] != table:
        fail("the embedded arm table is not the seeded one")
    if list(table.values()).count("A") != p["slots"] // 2:
        fail("arms are not balanced")
    if data["instrument"] != gen.instrument_hash():
        fail("the embedded instrument hash is not sha256(manifest + cases)")
    ok(f"arms: seed {p['seed']} → {''.join(table[str(s)] for s in range(1, p['slots'] + 1))}; instrument {data['instrument'][:12]}…")


def check_text(m: dict, html: str, js: str, data: dict) -> None:
    text = html + "\n" + js
    for key, s in m["strings"].items():
        probe = s.split("{")[0].strip() if "{" in s else s
        if probe and probe not in text and gen.esc(probe) not in text:
            fail(f"declared string {key!r} ({s[:40]!r}) appears nowhere in the page or runtime")
    if data["strings"] != m["strings"]:
        fail("the runtime's strings block is not the manifest's")
    for nc in m["non_claims"]:
        if gen.esc(nc) not in html and nc not in html:
            fail(f"non-claim missing from the page: {nc[:50]!r}")
    if gen.esc(m["governing_rule"]) not in html and m["governing_rule"] not in html:
        fail("the governing rule is not on the page")
    if not failures:
        ok(f"text: {len(m['strings'])} declared strings present; non-claims and the governing rule rendered from the manifest")


def check_runtime(js: str, html: str) -> None:
    for needle in ("fetch(", "XMLHttpRequest", "sendBeacon(", "localStorage", "sessionStorage", "indexedDB", "Math.random", "https://", "http://"):
        if needle in js:
            fail(f"runtime contains {needle!r} — the instrument stores nothing, sends nothing, and is deterministic")
    for needle, what in (("prefers-reduced-motion", "the reduced-motion query"), ("announce(", "announcements"),
                         ("JSON.parse(dataEl.textContent)", "reading the embedded data"), ("instrument_hash", "the receipt's instrument hash"),
                         ("D.pilot.arms[String(v)]", "the arm lookup"), ("crypto.subtle.digest", "the seal digest")):
        if needle not in js:
            fail(f"runtime lost {what} ({needle!r})")
    for needle, what in (('aria-live="polite"', "the live region"), ('class="tr-static"', "the JavaScript-off protocol"), ('id="tr-receipt"', "the receipt")):
        if needle not in html:
            fail(f"page lost {what} ({needle!r})")
    if html.count("<h1 ") != 1:
        fail("page must carry exactly one h1")
    if "trial.js" not in html:
        fail("page does not load the runtime")
    if not failures:
        ok("runtime: no transport, no storage, no randomness; live region, seal digest, arm lookup and receipt present")


def check_scorer(m: dict) -> None:
    try:
        import trial_score  # noqa: WPS433
    except Exception as e:  # pragma: no cover
        fail(f"scorer unavailable: {e}")
        return
    p = m["pilot"]
    if trial_score.N_MIN != p["n_min_to_conclude"] or trial_score.PER_ARM != (p["per_arm_min"], p["per_arm_max"]):
        fail("scorer constants disagree with the manifest's pilot block")
    if trial_score.CONTINUE_AT != 2 or trial_score.NARROW_AT != 1:
        fail("scorer thresholds are not the frozen 2 / 1")
    r = trial_score.selftest()
    if r:
        fail(f"scorer self-test: {r}")
    else:
        ok("scorer: constants equal the manifest; self-test cases decide CONTINUE, NARROW, KILL and UNDETERMINED as frozen")


def freeze_record(m: dict) -> dict:
    kf = key_file()
    return {
        "instrument": "necromancer", "experiment": m["experiment"],
        "frozen": "2026-09-02",
        "rule": "Nothing under inputs changes after a human answers. An edit to any of them after that voids the affected result under the manifest's forbidden_rescues.",
        "seed": m["pilot"]["seed"],
        "arms": gen.arm_table(m["pilot"]["seed"], int(m["pilot"]["slots"])),
        "instrument_hash": gen.instrument_hash(),
        "keys_sha256": sha256_file(kf) if kf else None,
        "keys_note": "sha256 of the withheld key file (pre and cold cases). The file is committed to this directory only after every response is in.",
        "decision_rule": m["pilot"]["decision_rule"],
        "primary_outcome": m["pilot"]["primary_outcome"],
        "inputs": {rel: sha256_file(ROOT / rel) for rel in FROZEN_INPUTS},
    }


def check_freeze(m: dict) -> dict | None:
    if not FREEZE.exists():
        fail("trials/necromancer/pilot/freeze.json missing — run scripts/verify_trial.py --freeze")
        return None
    f = json.loads(FREEZE.read_text(encoding="utf-8"))
    for rel, digest in f["inputs"].items():
        p = ROOT / rel
        if not p.exists():
            fail(f"frozen input {rel} missing")
        elif sha256_file(p) != digest:
            fail(f"frozen input {rel} changed since the freeze — if a human has answered, this is a forbidden rescue; otherwise re-freeze")
    if f.get("arms") != gen.arm_table(m["pilot"]["seed"], int(m["pilot"]["slots"])):
        fail("frozen arm table is not the seeded one")
    if f.get("instrument_hash") != gen.instrument_hash():
        fail("frozen instrument hash does not match manifest + cases")
    if f.get("decision_rule") != m["pilot"]["decision_rule"]:
        fail("the decision rule moved since the freeze")
    if not f.get("keys_sha256"):
        fail("the freeze carries no key digest")
    if not failures:
        ok(f"freeze: {len(f['inputs'])} inputs unchanged since {f['frozen']}; key digest {str(f['keys_sha256'])[:12]}…")
    return f


def check_receipt(m: dict) -> None:
    if not RECEIPT.exists():
        fail(f"{RECEIPT.relative_to(ROOT)} missing — run scripts/trial_qa.py (Chrome + the render venv)")
        return
    r = json.loads(RECEIPT.read_text(encoding="utf-8"))
    for rel, digest in r["inputs"].items():
        p = ROOT / rel
        if not p.exists() or sha256_file(p) != digest:
            fail(f"QA receipt is stale — {rel} changed since the capture (re-run scripts/trial_qa.py)")
    runs = {x["arm"]: x for x in r.get("runs", [])}
    for arm in ("A", "B"):
        run = runs.get(arm)
        if not run:
            fail(f"no QA run for arm {arm}")
            continue
        phases = [p["id"] for p in run["phases"]]
        expected = ["enrol", "pre", "claim", "seal", "evidence", "sort", "debrief", "update", "cold", "receipt"] if arm == "A" else \
                   ["enrol", "pre", "claim", "evidence", "seal", "sort", "debrief", "update", "cold", "receipt"]
        if phases != expected:
            fail(f"arm {arm}: phases {phases} != {expected}")
        bad = [k for k, v in run["assertions"].items() if v is not True]
        if bad:
            fail(f"arm {arm}: assertions failed at capture: {bad}")
        rec = run.get("receipt") or {}
        if rec.get("instrument_hash") != gen.instrument_hash():
            fail(f"arm {arm}: the captured receipt does not carry the current instrument hash")
        if rec.get("arm") != arm or len(rec.get("cold", {})) != 8 or len(rec.get("pre", {})) != 8 or len(rec.get("trained", {})) != 8:
            fail(f"arm {arm}: the captured receipt is incomplete")
        if (rec.get("seal") or {}).get("before_evidence") is not (arm == "A"):
            fail(f"arm {arm}: the seal's before_evidence flag disagrees with the arm")
    if r.get("console_errors") or r.get("page_errors"):
        fail(f"errors at capture: {(r.get('console_errors') or r.get('page_errors'))[:2]}")
    b = m["performance_budget"]
    perf = r.get("performance", {})
    if perf.get("html_bytes", 0) > b["html_bytes_max"] or perf.get("js_bytes", 0) > b["js_bytes_max"]:
        fail(f"budget: html {perf.get('html_bytes')} B / js {perf.get('js_bytes')} B over {b['html_bytes_max']} / {b['js_bytes_max']}")
    if perf.get("third_party_requests", 0) != 0:
        fail(f"{perf.get('third_party_requests')} third-party requests")
    if not failures:
        ok(f"QA receipt fresh: both arms ran end to end through every phase with every assertion true; html {perf.get('html_bytes')} B, js {perf.get('js_bytes')} B")


def main() -> int:
    m = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    if "--freeze" in sys.argv:
        FREEZE.write_text(json.dumps(freeze_record(m), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {FREEZE.relative_to(ROOT)}")
        return 0
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    if not PAGE.exists() or not RUNTIME.exists():
        fail("trials/necromancer/index.html or trial.js missing")
        return 1
    html = PAGE.read_text(encoding="utf-8")
    js = RUNTIME.read_text(encoding="utf-8")
    check_manifest(m)
    data = page_data(html)
    if data is None:
        return 1
    freeze = check_freeze(m)
    check_cases(cases, html, freeze)
    check_arms(m, data)
    check_text(m, html, js, data)
    check_runtime(js, html)
    check_scorer(m)
    check_receipt(m)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("ok    TRIAL IV verified: manifest, bare cases, arms, text, runtime hygiene, scorer, freeze, QA receipt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
