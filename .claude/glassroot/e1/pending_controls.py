"""Mutation controls for the closed, shrinking LEGACY_UNASSESSED exemption.
Usage: pending_controls.py <repo_dir>. Each control builds a temporary ROOT holding a mutated
claims_history.yaml and correction record, points the test module at it, and runs the one test."""
import copy, datetime as dt, importlib, json, shutil, sys, tempfile, unittest
from pathlib import Path
import yaml
repo = Path(sys.argv[1]).resolve()
alt = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None
sys.path[:0] = [str(alt.parent if alt else repo / "tests"), str(repo / "scripts")]
H = importlib.import_module("claims_history")
T = importlib.import_module(alt.stem if alt else "test_correction_dispositions")
hist0 = yaml.safe_load((repo / "claims_history.yaml").read_text())
rec0 = json.loads((repo / "corrections/records/2026-09-10.json").read_text())
LIST0 = T.LEGACY_UNASSESSED
E6, E7B = hist0["entries"][48]["digest"], hist0["entries"][49]["digest"]
MC3 = hist0["entries"][28]["digest"]
today = dt.date(2026, 9, 27).isoformat()

def assess(h, subject, value):
    e = {"kind": H.ASSESSMENT, "subject_transition_digest": subject, "falsifier_assessment": value,
         "recorded_at": today, "evidence_refs": ["test:control"], "reason": "control",
         "previous_transition_digest": H.tip_digest(h)}
    e["digest"] = H.entry_digest(e); h["entries"].append(e); return e

def new_correction(h, cid):
    prev = [e for e in h["entries"] if e.get("claim_id") == cid][-1]
    to_c = copy.deepcopy(prev["to_commitment"]); to_c["non_claims"] = list(to_c.get("non_claims") or []) + ["control"]
    e = {"kind": "transition", "claim_id": cid, "from_digest": prev["to_digest"], "to_digest": H.digest(to_c),
         "to_commitment": to_c, "transition_type": "CORRECT", "event_at": today, "recorded_at": today,
         "provenance_class": "CONTEMPORANEOUS", "direction_basis": "DECLARED_HUMAN_JUDGMENT",
         "evidence_refs": ["test:control"], "reason": "control", "previous_transition_digest": H.tip_digest(h)}
    e["digest"] = H.entry_digest(e); h["entries"].append(e); return e

def run(name, expect_pass, mutate, expect_msg=None):
    h, r = copy.deepcopy(hist0), copy.deepcopy(rec0); lst = set(LIST0)
    res = mutate(h, r, lst)
    lst = lst if res is None else set(res)
    tmp = Path(tempfile.mkdtemp())
    try:
        (tmp / "corrections/records").mkdir(parents=True)
        (tmp / "claims_history.yaml").write_text(yaml.safe_dump(h, sort_keys=False))
        (tmp / "corrections/records/2026-09-10.json").write_text(json.dumps(r))
        T.ROOT, T.LEGACY_UNASSESSED = tmp, frozenset(lst)
        res = unittest.TestResult()
        T.Corrections("test_disposition_follows_falsifier_only_when_it_fired").run(res)
        errs = res.failures + res.errors
        passed = not errs
        tb = errs[0][1] if errs else ""
        msg = " ".join(tb[tb.rfind("AssertionError:"):].split()) if errs else "passed"
        ok = passed == expect_pass and (expect_msg is None or expect_msg in msg)
        return {"control": name, "expected": "pass" if expect_pass else "fail", "actual": "pass" if passed else "fail",
                "behaved": ok, "message": msg[:200]}
    finally:
        shutil.rmtree(tmp); T.ROOT, T.LEGACY_UNASSESSED = repo, LIST0

def set_disp(r, cid, d):
    next(x for x in r["records"] if x["claim_id"] == cid)["disposition"] = d

out = [
 run("P0 committed state", True, lambda h, r, l: None),
 run("P1 E6 assessed, list unchanged", False, lambda h, r, l: assess(h, E6, "NOT_FIRED") and None, "exactly the legacy"),
 run("P2 E6 assessed and removed: the set shrinks", True, lambda h, r, l: (assess(h, E6, "NOT_FIRED"), l - {E6})[1]),
 run("P3 both assessed and removed: empty set fails", False,
     lambda h, r, l: (assess(h, E6, "NOT_FIRED"), assess(h, E7B, "FIRED"), set())[2], "the exemption is empty"),
 run("P4 member removed without an assessment", False, lambda h, r, l: l - {E6}, "exactly the legacy"),
 run("P5 legacy MC-003 entries[28] added", False, lambda h, r, l: l | {MC3}, "exactly the legacy"),
 run("P6 new E6 correction (entries[50]) unassessed", False, lambda h, r, l: new_correction(h, "E6-001") and None,
     "needs a falsifier assessment"),
 run("P7 new E6 correction listed in place of the old one", False,
     lambda h, r, l: (l - {E6}) | {new_correction(h, "E6-001")["digest"]}, "needs a falsifier assessment"),
 run("P8 legacy entry digest altered (the kernel also fails this)", False,
     lambda h, r, l: h["entries"][49].__setitem__("digest", "0" * 64)),
 run("P9 E7B FIRED, disposition NARROW (mismatch)", False,
     lambda h, r, l: (assess(h, E7B, "FIRED"), set_disp(r, "E7B-001", "NARROW"), l - {E7B})[2], "'NARROW' != 'REJECT'"),
 run("P10 E7B FIRED, disposition REJECT (match)", True, lambda h, r, l: (assess(h, E7B, "FIRED"), l - {E7B})[1]),
 run("P11 E6 NOT_FIRED, disposition NARROW: no relation asserted", True,
     lambda h, r, l: (assess(h, E6, "NOT_FIRED"), set_disp(r, "E6-001", "NARROW"), l - {E6})[2]),
 run("P12 E6 UNDETERMINED and removed: an assessment, not an exemption", True,
     lambda h, r, l: (assess(h, E6, "UNDETERMINED"), l - {E6})[1]),
]
for o in out: print(("ok   " if o["behaved"] else "BAD  ") + f'{o["control"]:<58} expected {o["expected"]:<4} actual {o["actual"]:<4} | {o["message"][:110]}')
print(f'{sum(o["behaved"] for o in out)}/{len(out)} behaved')
json.dump(out, open(Path(__file__).with_suffix(".json") if not alt else alt.with_suffix(".controls.json"), "w"), indent=1)
sys.exit(0 if all(o["behaved"] for o in out) else 1)
