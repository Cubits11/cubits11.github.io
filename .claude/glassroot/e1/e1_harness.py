#!/usr/bin/env python3
"""E1 - deterministic representation ablation over the GLASSROOT case corpus.

Usage: e1_harness.py <repo> <kernel_repo> <base_repo> <python> <blueprint_content_py>

  repo          a checkout with the full object store (origin refs fetched)
  kernel_repo   f2249c1 plus the falsifier_assessment series (representation B)
  base_repo     f2249c1 without it (representation A)
  python        the interpreter the repository's scripts run under

Every fact that can be computed is computed here, from git objects and the repository's own
scripts. Observations that cannot (an HTTP fetch, a GitHub ruleset, a Drive record) are read
from time-stamped files in fixtures/. The harness refuses to run if e1_predeclared.json differs
from the sha256 recorded when it was written. It writes e1_results.json and e1_matrix.md.
"""
import copy, hashlib, importlib.util, itertools, json, re, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
YES, NO, UND = "YES", "NO", "UNDECIDED"
PASS, FAIL, UNEV = "PASS", "FAIL", "UNEVALUABLE"


def sh(cmd, cwd, check=False):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(Path(path).parent))
    spec.loader.exec_module(mod)
    sys.path.pop(0)
    return mod


# ------------------------------------------------------------------ facts
def facts(repo: Path, kernel_repo: Path, base_repo: Path, py: str, blueprint: Path) -> dict:
    F: dict = {}
    tmp = Path(tempfile.mkdtemp(prefix="wt-", dir=HERE))
    made = []

    def wt(name, rev):
        p = tmp / name
        sh(["git", "worktree", "add", "-q", "--detach", str(p), rev], repo, check=True)
        made.append(p)
        return p

    def tree(p):
        return sh(["git", "rev-parse", "HEAD^{tree}"], p).stdout.strip()

    try:
        # P1 / P1b: T6's acceptance command at the run commit
        mod = sh(["git", "show", "2174358:scripts/verify_room_atom_map.py"], repo, check=True).stdout
        w0, wu, w1 = wt("p1_w0", "32f0e3a"), wt("p1_wu", "32f0e3a"), wt("p1_w1", "32f0e3a")
        (wu / "scripts/verify_room_atom_map.py").write_text(mod)
        (w1 / "scripts/verify_room_atom_map.py").write_text(mod)
        sh(["git", "add", "scripts/verify_room_atom_map.py"], w1, check=True)
        sh(["git", "-c", "user.name=e1", "-c", "user.email=e1@localhost", "commit", "-qm", "counterfactual"], w1, check=True)
        cmd = [py, "scripts/generate_foundations.py", "--check"]
        F["p1"] = {
            "clean_rc": sh(cmd, w0).returncode, "clean_tree": tree(w0),
            "untracked_rc": sh(cmd, wu).returncode, "untracked_head_tree": tree(wu),
            "untracked_files": len(sh(["git", "status", "--porcelain"], wu).stdout.splitlines()),
            "committed_rc": sh(cmd, w1).returncode, "committed_tree": tree(w1),
            "command": "python3 scripts/generate_foundations.py --check",
        }
        # P3a: flagship source map
        s0, s1 = wt("p3_w0", "15e9b9d"), wt("p3_w1", "15e9b9d")
        (s0 / "films/flagship/source-map.json").write_text(
            sh(["git", "show", "94a1cb5:films/flagship/source-map.json"], repo, check=True).stdout)
        fcmd = [py, "scripts/films/build_flagship.py", "--check"]
        F["p3a"] = {"stale_rc": sh(fcmd, s0).returncode, "current_rc": sh(fcmd, s1).returncode,
                    "command": "python3 scripts/films/build_flagship.py --check",
                    "stale_map_from": "94a1cb5", "sources_at": "15e9b9d"}
    finally:
        for p in made:
            sh(["git", "worktree", "remove", "--force", str(p)], repo)
        sh(["git", "worktree", "prune"], repo)
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    # P3b: REL-001 review window, the predicate at verify_claims.py
    import datetime as dt
    import yaml
    vc_src = (base_repo / "scripts/verify_claims.py").read_text()
    pred = "elif (today - reviewed).days > window:"
    assert pred in vc_src, "verify_claims.py review predicate moved"
    rel = next(c for c in yaml.safe_load((base_repo / "claims.yaml").read_text())["claims"] if c["id"] == "REL-001")
    reviewed = dt.date.fromisoformat(str(rel["last_reviewed"]))
    window = int(rel["review_window_days"])
    due = lambda day: (dt.date.fromisoformat(day) - reviewed).days > window
    F["p3b"] = {"last_reviewed": str(reviewed), "window_days": window, "line": pred,
                "2026-09-23_due": due("2026-09-23"), "2026-09-24_due": due("2026-09-24")}

    # P3c: AF-001's support URL, as the registry reported it
    reg = (HERE / "fixtures/registry_af001_rel001.txt").read_text()
    F["p3c"] = {"af001_unknown_line": next(l for l in reg.splitlines() if l.startswith("UNKNOWN  AF-001")),
                "source": json.loads((HERE / "fixtures/registry_af001_rel001.meta.json").read_text())}

    # P4: the blueprint block and the main ruleset
    src = blueprint.read_text()
    m = re.search(r"MERGE = f'''(.*?)'''", src, re.S)
    lines = [l.strip() for l in m.group(1).splitlines() if l.strip() and not l.strip().startswith("#") and not l.strip().startswith("{")]
    steps = []
    for l in lines:
        if l.startswith("git push origin main"):
            steps.append({"kind": "push", "subject": "branch:main"})
        elif l.startswith("git push"):
            steps.append({"kind": "push", "subject": "branch:other"})
        elif l.startswith("git "):
            steps.append({"kind": "git-local", "subject": "local"})
        elif "verification_manifest.py" in l:
            steps.append({"kind": "run-checks", "subject": "local"})
    rules = json.loads((HERE / "fixtures/ruleset_main.json").read_text())
    F["p4"] = {"block_lines": lines, "steps": steps,
               "push_follows_manifest_ungated": any("verification_manifest.py" in a and not a.rstrip().endswith("&&") for a in lines)
               and "git push origin main" in lines,
               "ruleset_rule_types": [r["type"] for r in rules],
               "ruleset_meta": json.loads((HERE / "fixtures/ruleset_main.meta.json").read_text()),
               "bypass_actors": "not readable without admin access"}

    # P5b / P5c: approvals, drafts and receipts through distribute.py itself
    dist = load_module("e1_distribute", base_repo / "scripts/distribute.py")
    posts = {p["id"]: p for p in dist.draft()}
    approved = "8318df5ab8fdfcfd87dc94649ee392c1de9e7daa75955080cae74b09398c8dfc"
    pubs = dist.records("publications.json")
    F["p5"] = {"approved_revision": approved,
               "approval_for_approved": dist.approval_for({"id": "try-a", "revision": approved}) is not None,
               "current_revision": posts["try-a"]["revision"],
               "approval_for_current": dist.approval_for(posts["try-a"]) is not None,
               "receipt_for_approved": any(r["draft_revision"] == approved for r in pubs),
               "receipt_published_at": next((r["published_at"] for r in pubs if r["draft_revision"] == approved), None),
               "other_receipts": sum(1 for r in pubs if r["draft_revision"] != approved),
               "recheck_site": "distribute.py dispatch_preconditions: approval_for(post) on the draft's revision computed at publish time",
               "current_drafts_without_approval": sorted(pid for pid, p in posts.items() if dist.approval_for(p) is None)}

    # P5a: D4
    d4 = (HERE / "fixtures/drive10_D4.txt").read_text()
    d4_section = d4[d4.find("## D4"):]
    F["p5a"] = {"issuer": "delegate (Claude Cowork session under owner delegation)" if "under explicit owner delegation" in d4 else "unknown",
                "names_grantee": bool(re.search(r"grantee|assigned to|session_[0-9A-Za-z]{6,}", d4_section)),
                "authorized_content": "exactly two falsifier_assessment entries" in d4_section,
                "merge_is_owner_action": "The merge is the owner's action" in d4_section}

    # P6: the 13.12 key
    key = ".claude/readiness-calibration/suite_key.json"
    refs = [r for r in sh(["git", "for-each-ref", "--format=%(refname)", "refs/remotes/origin"], repo).stdout.split() if not r.endswith("/HEAD")]
    carrying = [r for r in refs if sh(["git", "cat-file", "-e", f"{r}:{key}"], repo).returncode == 0]
    F["p6"] = {"pushed_refs_carrying_key": [r.replace("refs/remotes/origin/", "") for r in carrying],
               "http_observation": json.loads((HERE / "fixtures/suite_key_public_fetch.meta.json").read_text())}

    # P7a / P7b: the kernel relation, with and without the assessment kind
    kB = load_module("e1_kernel_B", kernel_repo / "scripts/claims_history.py")
    kA = load_module("e1_kernel_A", base_repo / "scripts/claims_history.py")
    hist = yaml.safe_load((kernel_repo / "claims_history.yaml").read_text())
    known = kB.commitments_by_digest(hist)
    t49 = hist["entries"][49]
    pred49 = kB.predecessor_commitment(t49, known)
    rel = {}
    for val in (None, "NOT_FIRED", "FIRED"):
        h = copy.deepcopy(hist)
        if val:
            e = {"kind": kB.ASSESSMENT, "subject_transition_digest": t49["digest"], "falsifier_assessment": val,
                 "recorded_at": "2026-09-27", "evidence_refs": ["e1"], "reason": "e1", "previous_transition_digest": kB.tip_digest(h)}
            e["digest"] = kB.entry_digest(e)
            h["entries"].append(e)
        rel[str(val)] = kB.falsifier_relation(h, t49, pred49)
    audit = json.loads((base_repo / "distribution/research-2026-09-10/audit-results.json").read_text())
    F["p7"] = {"subject": t49["digest"], "claim": t49["claim_id"], "predecessor_consequence": pred49["falsifier"]["consequence"],
               "relation_committed": rel["None"], "relation_NOT_FIRED": rel["NOT_FIRED"], "relation_FIRED": rel["FIRED"],
               "A_has_relation": hasattr(kA, "falsifier_relation"),
               "e7b_changed_thresholds": audit["e7b"]["changed_thresholds"],
               "evidence_test": "tests/test_correction_dispositions.py test_audit_demonstrates_both_failures asserts changed_thresholds == 1"}

    # R8: executor identity
    run = ["32f0e3a", "14ca608", "62bfbbc"]
    F["r8"] = {"commits": {c: {"author": sh(["git", "log", "-1", "--format=%an", c], repo).stdout.strip(),
                               "author_date": sh(["git", "log", "-1", "--format=%aI", c], repo).stdout.strip(),
                               "trailers": sh(["git", "log", "-1", "--format=%(trailers:only,unfold)", c], repo).stdout.strip()}
                           for c in run},
               "brief_rules": [l for l in sh(["git", "grep", "-n", "-i", "no co-author trailers", "f2249c1", "--", "docs/foundations"], repo).stdout.splitlines()],
               "claude_trailered_in_last_200_main": sum(1 for b in sh(["git", "log", "-200", "--format=%(trailers:only,unfold)%x01", "origin/main"], repo).stdout.split("\x01")
                                                     if re.search(r"Claude-Session|Co-Authored-By: Claude", b)),
               "this_session_commit_trailer": "Claude-Session" in sh(["git", "log", "-1", "--format=%(trailers:only,unfold)", "d49480e"], repo).stdout,
               "owner_side_receipt_columns": json.loads((HERE / "fixtures/p1305_receipt_columns.json").read_text())}

    # R9: brief versus dispatch
    def brief(c):
        return sh(["git", "show", f"{c}:docs/foundations/ASTRA-BRIEF.md"], repo, check=True).stdout

    def scored_text(text, task):
        L = text.split("\n")
        a0 = next(i for i, l in enumerate(L) if l.startswith("## §A"))
        b0 = next(i for i, l in enumerate(L) if l.startswith("## §B"))
        row = next(l for l in L if re.match(rf"^\|\s*\*\*{task}\*\*", l))
        return "\n".join(L[a0:b0]) + "\n" + row

    def all_rows_text(text):
        L = text.split("\n")
        a0 = next(i for i, l in enumerate(L) if l.startswith("## §A"))
        b0 = next(i for i, l in enumerate(L) if l.startswith("## §B"))
        rows = [l for l in L if re.match(r"^\|\s*\*\*T\d\*\*", l)]
        return "\n".join(L[a0:b0]) + "\n" + "\n".join(rows)

    h256 = lambda s: hashlib.sha256(s.encode()).hexdigest()
    scores = json.loads(sh(["git", "show", "d49480e:.claude/readiness-calibration/preoutcome_scores.json"], repo, check=True).stdout)
    scored_blob = scores["sources"]["ASTRA-BRIEF"]["git_blob"]
    dispatch_commit = sh(["git", "log", "-1", "--format=%h", "32f0e3a", "--", "docs/foundations/ASTRA-BRIEF.md"], repo).stdout.strip()
    scored_commit = sh(["git", "log", "-1", "--format=%h", "f2249c1", "--", "docs/foundations/ASTRA-BRIEF.md"], repo).stdout.strip()
    blob_of = lambda c: sh(["git", "rev-parse", f"{c}:docs/foundations/ASTRA-BRIEF.md"], repo).stdout.strip()
    F["r9"] = {"scored_blob": scored_blob, "scored_commit": scored_commit, "scored_commit_blob": blob_of(scored_commit),
               "dispatch_time_commit": dispatch_commit, "dispatch_time_blob": blob_of(dispatch_commit),
               "sectionA_T6_scored": h256(scored_text(brief(scored_commit), "T6")),
               "sectionA_T6_dispatch_time": h256(scored_text(brief(dispatch_commit), "T6")),
               "sectionA_all_rows_dispatch_time": h256(all_rows_text(brief(dispatch_commit))),
               "prompt_field_is_prose": scores["rows"][[r["id"] for r in scores["rows"]].index("RETRO-ASTRA-T6")]["prompt"][:60],
               "dispatch_record_in_repo": None}

    # P2: readiness and dispatch
    row = next(r for r in scores["rows"] if r["id"] == "CLAUDE-2026-09-26-01")
    F["p2"] = {"decision": row["decision"], "hard_vetoes": row["hard_vetoes"], "gate_reads_readiness": False,
               "gate_search": sh(["git", "grep", "-l", "preoutcome_scores", "f2249c1", "--", "scripts"], repo).stdout.strip() or "no script reads preoutcome_scores.json",
               "dispatch_record": "session record; commits carry the Claude-Session trailer (d49480e)"}
    return F


# ------------------------------------------------------------------ the contract's decision rule (K), with masks
def covers(g, step, W, M):
    if "g.grantee" not in M:
        if g.get("grantee") is None:
            return False  # a grant that names no recipient covers no principal
        if g["grantee"] == "credential-holder":
            if not W["conditions"].get("credentials"):
                return False
        elif g["grantee"] != W["principal"]:
            return False
    if "g.actions" not in M and step["kind"] not in g["actions"]:
        return False
    if "g.subject_selector" not in M:
        sel = g["subject_selector"]
        where = W["admitted"] if "recheck_at_execution" in M else W["current"]
        cur = where.get(step["subject"], step["subject"])
        if isinstance(sel, dict):
            if not isinstance(cur, dict) or any(cur.get(k) != v for k, v in sel.items()):
                return False
        elif sel != "*" and sel != cur:
            return False
    if "g.conditions" not in M:
        for c in g.get("conditions", []):
            if c == "not_already_executed":
                if "Rc" in M:
                    continue
                cur = (W["admitted"] if "recheck_at_execution" in M else W["current"]).get(step["subject"], {})
                if any(("r.action" in M or r["action"] == step["kind"]) and ("r.subject_digest" in M or r["subject_digest"] == cur)
                       for r in W["receipts"]):
                    return False
            elif not W["conditions"].get(c):
                return False
    if "g.issuer" not in M and g.get("issuer") not in ("owner", "owner-delegate", "platform-for-owner"):
        return False
    if "g.not_before" not in M and g.get("not_before") and W["now"] < g["not_before"]:
        return False
    if "g.expires" not in M and g.get("expires") and W["now"] >= g["expires"]:
        return False
    if "g.policy_digest" not in M and g.get("policy_digest") and g["policy_digest"] != W.get("policy"):
        return False
    return True


def req_met(req, W, M):
    if "V" in M:
        return True  # verifications absent: requirements ignored
    subj = W["current"].get(req["subject"])
    if "req_per_check" in M:
        agg = W["aggregate"]
        if agg is None:  # no unrelated check recorded: the aggregate is the combination of the derived results
            vals = list(W["derived"].values())
            agg = FAIL if FAIL in vals else UNEV if UNEV in vals else PASS if vals else None
        results = [agg]
    elif "derive_now" not in M:
        derived = W["derived"]
        results = list(derived.values()) if "v.check" in M else ([derived[req["check"]]] if req["check"] in derived else [])
    else:
        results = [v["result"] for v in W["stored"]
                   if ("v.check" in M or v["check"] == req["check"])
                   and ("v.subject_digest" in M or v["subject_digest"] == subj)
                   and ("v.policy_digest" in M or v.get("policy_digest") == req.get("policy"))
                   and ("v.environment" in M or not req.get("env") or v.get("environment") == req["env"])
                   and ("v.verifier" in M or not req.get("verifier_not") or v.get("verifier") != req["verifier_not"])]
    if "v.result" in M:
        return bool(results)
    if "fail_closed" in M:
        return not any(r == FAIL for r in results)  # only FAIL blocks: UNEVALUATED, STALE and UNEVALUABLE admit
    return any(r == PASS for r in results)


def decide_K(q, W, M=frozenset()):
    if q == "adm":
        if "veto" not in M and any(v in [s["kind"] + "@" + s["subject"] for s in W["steps"]] for v in W.get("vetoes", [])):
            return NO
        if "G" not in M and "default_deny" not in M:
            for s in W["steps"]:
                if not any(covers(g, s, W, M) for g in W["grants"]):
                    return NO
        return YES if all(req_met(r, W, M) for r in W.get("reqs", [])) else NO
    if q == "req":
        return YES if all(req_met(r, W, M) for r in W["reqs"]) else NO
    if q == "fired":
        if "T" in M or "FA" in M:
            return UND
        a = W["assessments"].get(W["subject_transition"])
        return UND if a is None else (YES if a == "FIRED" else NO)
    if q == "epi_record":
        if "T" in M:
            return NO  # no transition record type: a correction cannot be recorded at all
        authorized = "G" in M or "default_deny" in M or any(covers(g, s, W, M) for g in W["grants"] for s in W["steps"])
        evidence = "epi_evidence" in M or "V" in M or (
            bool(W["evidence"]) if "v.result" in M else any(r == FAIL for r in W["evidence"]))
        return YES if authorized and W["kernel_valid"] and evidence else NO
    if q == "attr_exec":
        if "Rc" in M or "r.executor" in M:
            return UND
        ex = W["receipt"].get("executor") if W.get("receipt") else None
        return UND if ex is None else (YES if ex == W["claimed_executor"] else NO)
    if q == "attr_subject":
        if "Rc" in M or "V" in M or "r.subject_digest" in M or "v.subject_digest" in M:
            return UND
        r, v = W.get("receipt"), W.get("score")
        if not r or not v or r.get("subject_digest") is None or v.get("subject_digest") is None:
            return UND
        return YES if r["subject_digest"] == v["subject_digest"] else NO
    raise ValueError(q)


# ------------------------------------------------------------------ Gemini's 8-tuple under its Delta
RANK = {None: -1, "A0": 0, "A1": 1, "A2": 2, "A3": 3, "A4": 4}


def decide_C(q, S, M=frozenset()):
    bound = "Ia" not in M
    vc = None if "Vc" in M else (S.get("Vc") if bound else S.get("Vc_unbound", S.get("Vc")))
    fe = None if "Fe" in M else (S.get("Fe") if bound or S.get("Fe_kind") == "time" else "CURRENT")  # without Ia a file-change refresh cannot fire; a time window still can
    ok_v = "Vc" in M or vc != FAIL
    ok_f = "Fe" in M or fe == "CURRENT"
    if q in ("adm", "epi_record"):
        ok_a = "Ac" in M or RANK[S.get("Ac")] >= RANK[S["req_rank"]]
        return YES if ok_a and ok_v and ok_f else NO
    if q == "req":
        ok_e = "Es" in M or "Es" not in S or S["Es"] in ("OBSERVED", "DERIVED")
        return YES if ok_v and ok_f and ok_e else NO
    if q == "fired":
        return UND if "Fa" in M or S.get("Fa") in (None, "UNASSESSED") else (YES if S["Fa"] == "FIRED" else NO)
    if q == "attr_exec":
        return UND if "Ie" in M or S.get("Ie") is None else (YES if S["Ie"] == S["claimed_executor"] else NO)
    if q == "attr_subject":
        return UND  # no field of the tuple names the text that was dispatched
    raise ValueError(q)


# ------------------------------------------------------------------ worlds
def worlds(F):
    """K-worlds (the full contract, CAPACITY) and C-states for every pair. Each world cites its grounding."""
    P = {}
    base = {"principal": "S", "now": "2026-09-27", "conditions": {}, "grants": [], "reqs": [], "stored": [],
            "derived": {}, "aggregate": None, "receipts": [], "current": {}, "admitted": {}, "steps": [], "vetoes": []}

    def W(**kw):
        w = copy.deepcopy(base)
        w.update(kw)
        if not kw.get("admitted"):
            w["admitted"] = copy.deepcopy(w["current"])
        return w

    rc = lambda c: PASS if c == 0 else FAIL
    p1 = F["p1"]
    req_t6 = {"check": "t6-acceptance", "subject": "run_commit", "policy": "ASTRA-BRIEF T6", "env": "clean-checkout"}
    for pid, agg in (("P1", None), ("P1b", FAIL)):
        w0 = W(current={"run_commit": p1["clean_tree"]}, reqs=[req_t6],
               derived={"t6-acceptance": rc(p1["clean_rc"]), **({"claim-registry": FAIL, "other-82-checks": PASS} if agg else {})},
               aggregate=FAIL,
               stored=[{"verifier": "executor", "check": "t6-acceptance", "subject_digest": p1["untracked_head_tree"],
                        "policy_digest": "ASTRA-BRIEF T6", "environment": "worktree-with-untracked", "result": rc(p1["untracked_rc"])}])
        w1 = W(current={"run_commit": p1["committed_tree"]}, reqs=[req_t6],
               derived={"t6-acceptance": rc(p1["committed_rc"]), **({"claim-registry": FAIL, "other-82-checks": PASS} if agg else {})},
               aggregate=FAIL if agg else PASS,
               stored=[{"verifier": "executor", "check": "t6-acceptance", "subject_digest": p1["committed_tree"],
                        "policy_digest": "ASTRA-BRIEF T6", "environment": "clean-checkout", "result": rc(p1["committed_rc"])}])
        c0 = {"Ia": p1["clean_tree"], "Vc": rc(p1["clean_rc"]), "Vc_unbound": rc(p1["untracked_rc"]), "Fe": "CURRENT",
              "So": "COMPLETED", "req_rank": "A2", "Ac": "A4"}
        c1 = {"Ia": p1["committed_tree"], "Vc": rc(p1["committed_rc"]), "Vc_unbound": PASS, "Fe": "CURRENT",
              "So": "COMPLETED", "req_rank": "A2", "Ac": "A4"}
        if agg:  # one controller verdict per state: the aggregate over every check on the PR head
            c0["Vc"] = c1["Vc"] = FAIL
        P[pid] = ("req", w0, w1, c0, c1)

    dispatch = {"id": "session", "issuer": "owner", "grantee": "S", "actions": ["execute-task"], "subject_selector": "*",
                "conditions": []}
    readiness = lambda d: {"verifier": "rater", "check": "readiness-13.04", "subject_digest": "prompt",
                           "result": PASS if d == "READY" else FAIL}
    step = [{"kind": "execute-task", "subject": "repo"}]
    P["P2"] = ("adm", W(steps=step, grants=[dispatch], stored=[readiness("HOLD")]), W(steps=step, stored=[readiness("HOLD")]),
               {"Ac": "A3", "req_rank": "A3", "Vc": None, "Fe": "CURRENT"}, {"Ac": None, "req_rank": "A3", "Vc": None, "Fe": "CURRENT"})
    P["P2c"] = ("adm", W(steps=step, stored=[readiness("READY")]), W(steps=step, stored=[readiness("HOLD")]),
                {"Ac": None, "req_rank": "A3", "Vc": None, "Fe": "CURRENT"}, {"Ac": None, "req_rank": "A3", "Vc": None, "Fe": "CURRENT"})

    p3a = F["p3a"]
    req_map = {"check": "flagship-source-map", "subject": "sources", "policy": "build_flagship.py", "env": "clean-checkout"}
    P["P3a"] = ("req",
                W(current={"sources": "sources@15e9b9d"}, reqs=[req_map], derived={"flagship-source-map": rc(p3a["stale_rc"])},
                  stored=[{"verifier": "generator", "check": "flagship-source-map", "subject_digest": "sources@94a1cb5",
                           "policy_digest": "build_flagship.py", "environment": "clean-checkout", "result": PASS}]),
                W(current={"sources": "sources@15e9b9d"}, reqs=[req_map], derived={"flagship-source-map": rc(p3a["current_rc"])},
                  stored=[{"verifier": "generator", "check": "flagship-source-map", "subject_digest": "sources@15e9b9d",
                           "policy_digest": "build_flagship.py", "environment": "clean-checkout", "result": PASS}]),
                {"Ia": "source-map", "Vc": PASS, "Fe": "EXPIRED", "req_rank": "A2", "Ac": "A4"},
                {"Ia": "source-map", "Vc": PASS, "Fe": "CURRENT", "req_rank": "A2", "Ac": "A4"})

    p3b = F["p3b"]
    req_rev = {"check": "review-window", "subject": "REL-001", "policy": "30d"}
    rev_stored = [{"verifier": "owner", "check": "review-window", "subject_digest": "REL-001@commitment", "policy_digest": "30d",
                   "environment": None, "result": PASS}]
    P["P3b"] = ("req",
                W(now="2026-09-23", current={"REL-001": "REL-001@commitment"}, reqs=[req_rev], stored=rev_stored,
                  derived={"review-window": FAIL if p3b["2026-09-23_due"] else PASS}),
                W(now="2026-09-24", current={"REL-001": "REL-001@commitment"}, reqs=[req_rev], stored=rev_stored,
                  derived={"review-window": FAIL if p3b["2026-09-24_due"] else PASS}),
                {"Ia": "REL-001", "Vc": PASS, "Fe": "CURRENT", "Fe_kind": "time", "req_rank": "A2", "Ac": "A4"},
                {"Ia": "REL-001", "Vc": PASS, "Fe": "EXPIRED", "Fe_kind": "time", "req_rank": "A2", "Ac": "A4"})

    req_url = {"check": "support-url", "subject": "AF-001", "policy": "claims.yaml"}
    P["P3c"] = ("req",
                W(current={"AF-001": "AF-001@commitment"}, reqs=[req_url], derived={"support-url": UNEV}),
                W(current={"AF-001": "AF-001@commitment"}, reqs=[req_url], derived={"support-url": PASS}),
                {"Ia": "AF-001", "Vc": "UNEVALUATED", "Fe": "CURRENT", "req_rank": "A2", "Ac": "A4"},
                {"Ia": "AF-001", "Vc": PASS, "Fe": "CURRENT", "req_rank": "A2", "Ac": "A4"})

    p4 = F["p4"]
    branch_grant = {"id": "designated-branch", "issuer": "platform-for-owner", "grantee": "S",
                    "actions": ["git-local", "run-checks", "push"], "subject_selector": "*", "conditions": []}
    push_grant = {"id": "designated-branch-push", "issuer": "platform-for-owner", "grantee": "S", "actions": ["push"],
                  "subject_selector": "branch:claude/lucid-franklin-jloow0", "conditions": []}
    local_grant = {"id": "local-work", "issuer": "platform-for-owner", "grantee": "S", "actions": ["git-local", "run-checks"],
                   "subject_selector": "*", "conditions": []}
    steps0 = p4["steps"]
    steps1 = [s for s in steps0 if not (s["kind"] == "push" and s["subject"] == "branch:main")]
    veto = ["push@branch:main", "push@branch:other"]
    P["P4"] = ("adm", W(steps=steps0, grants=[local_grant, push_grant], vetoes=veto),
               W(steps=steps1, grants=[local_grant, push_grant], vetoes=veto),
               {"Ac": "A3", "req_rank": "A4", "Vc": None, "Fe": "CURRENT"}, {"Ac": "A3", "req_rank": "A2", "Vc": None, "Fe": "CURRENT"})

    d4 = {"id": "D4", "issuer": "owner-delegate", "grantee": None, "actions": ["append-falsifier-assessment"],
          "subject_selector": "*", "conditions": []}
    instr_generic = {"id": "instruction", "issuer": "owner", "grantee": "S", "actions": ["audit", "prepare-branch-change"],
                     "subject_selector": "*", "conditions": []}
    instr_named = dict(instr_generic, actions=["audit", "prepare-branch-change", "append-falsifier-assessment"])
    st = [{"kind": "append-falsifier-assessment", "subject": "claims_history"}]
    P["P5a"] = ("adm", W(steps=st, grants=[d4, instr_generic]), W(steps=st, grants=[d4, instr_named]),
                {"Ac": None, "req_rank": "A2", "Vc": None, "Fe": "CURRENT"}, {"Ac": "A3", "req_rank": "A2", "Vc": None, "Fe": "CURRENT"})

    p5 = F["p5"]
    appr = {"id": "approval-try-a", "issuer": "owner", "grantee": "credential-holder", "actions": ["publish"],
            "subject_selector": {"draft": "try-a", "revision": p5["approved_revision"]},
            "conditions": ["clean_tree", "head_pushed", "credentials", "not_already_executed"]}
    conds = {"clean_tree": True, "head_pushed": True, "credentials": True}
    pub = [{"kind": "publish", "subject": "try-a"}]
    cur_ok = {"try-a": {"draft": "try-a", "revision": p5["approved_revision"]}}
    cur_new = {"try-a": {"draft": "try-a", "revision": p5["current_revision"]}}
    receipt = {"action": "publish", "executor": "S", "subject_digest": cur_ok["try-a"]}
    P["P5b"] = ("adm", W(steps=pub, grants=[appr], conditions=conds, current=cur_ok),
                W(steps=pub, grants=[appr], conditions=conds, current=cur_new, admitted=cur_ok),
                {"Ac": None, "req_rank": "A4", "Vc": None, "Fe": "CURRENT"}, {"Ac": None, "req_rank": "A4", "Vc": None, "Fe": "CURRENT"})
    P["P5c"] = ("adm", W(steps=pub, grants=[appr], conditions=conds, current=cur_ok),
                W(steps=pub, grants=[appr], conditions=conds, current=cur_ok, receipts=[receipt]),
                {"Ac": None, "req_rank": "A4", "Vc": None, "Fe": "CURRENT"}, {"Ac": None, "req_rank": "A4", "Vc": None, "Fe": "CURRENT"})

    req_blind = {"check": "key-unreachable", "subject": "suite_key"}
    self_report = [{"verifier": "rater", "check": "not-exposed-by-report", "subject_digest": "13.10-rows", "result": PASS}]
    P["P6"] = ("req",
               W(current={"suite_key": "02e3cc11"}, reqs=[req_blind], stored=self_report,
                 derived={"key-unreachable": FAIL if F["p6"]["pushed_refs_carrying_key"] else PASS}),
               W(current={"suite_key": "02e3cc11"}, reqs=[req_blind], stored=self_report, derived={"key-unreachable": PASS}),
               {"Ia": "suite_key", "Vc": FAIL, "Vc_unbound": PASS, "Es": "CONFLICTED", "Fe": "CURRENT", "req_rank": "A2", "Ac": "A4"},
               {"Ia": "suite_key", "Vc": PASS, "Vc_unbound": PASS, "Es": "DERIVED", "Fe": "CURRENT", "req_rank": "A2", "Ac": "A4"})

    p7 = F["p7"]
    P["P7a"] = ("fired",
                W(subject_transition=p7["subject"], assessments={p7["subject"]: "NOT_FIRED"}),
                W(subject_transition=p7["subject"], assessments={p7["subject"]: "FIRED"}),
                {"Fa": "NOT_FIRED"}, {"Fa": "FIRED"})
    owner_corr = {"id": "correction-campaign", "issuer": "owner", "grantee": "S", "actions": ["record-correction"],
                  "subject_selector": "*", "conditions": []}
    stc = [{"kind": "record-correction", "subject": "claims_history"}]
    P["P7b"] = ("epi_record",
                W(steps=stc, grants=[owner_corr], kernel_valid=True, evidence=[FAIL if p7["e7b_changed_thresholds"] >= 1 else PASS]),
                W(steps=stc, grants=[owner_corr], kernel_valid=True, evidence=[PASS]),
                {"Ac": "A4", "req_rank": "A2", "Vc": FAIL, "Fe": "CURRENT"}, {"Ac": "A4", "req_rank": "A2", "Vc": PASS, "Fe": "CURRENT"})

    P["R8"] = ("attr_exec",
               W(receipt={"action": "run T1-T6", "executor": "astra", "subject_digest": "32f0e3a"}, claimed_executor="astra"),
               W(receipt={"action": "run T1-T6", "executor": "owner", "subject_digest": "32f0e3a"}, claimed_executor="astra"),
               {"Ie": "astra", "claimed_executor": "astra"}, {"Ie": "owner", "claimed_executor": "astra"})

    r9 = F["r9"]
    score_exact = {"check": "readiness-13.04", "subject_digest": r9["sectionA_T6_scored"]}
    P["R9a"] = ("attr_subject",
                W(score=score_exact, receipt={"action": "dispatch", "executor": "owner", "subject_digest": r9["sectionA_T6_dispatch_time"]}),
                W(score=score_exact, receipt={"action": "dispatch", "executor": "owner", "subject_digest": r9["sectionA_all_rows_dispatch_time"]}),
                {}, {})
    P["R9b"] = ("attr_subject",
                W(score={"check": "readiness-13.04", "subject_digest": r9["sectionA_T6_scored"]},
                  receipt={"action": "dispatch", "executor": "owner", "subject_digest": r9["sectionA_T6_dispatch_time"]}),
                W(score={"check": "readiness-13.04", "subject_digest": r9["sectionA_T6_dispatch_time"]},
                  receipt={"action": "dispatch", "executor": "owner", "subject_digest": r9["sectionA_T6_dispatch_time"]}),
                {}, {})
    return P


def realize(pid, w, which, rep, regime, F):
    """Repository realization of a K-world: what A or B actually carries, per regime."""
    w = copy.deepcopy(w)
    if pid == "R9a" and not rep.endswith("+13.05"):
        w["receipt"] = None  # no repository record type holds the text sent to an external executor
    if regime == "RECORDED":
        if pid == "P7a":
            w["assessments"] = {}  # the two transcriptions are owner-gated and not appended
        if pid == "R8" and not rep.endswith("+13.05"):
            w["receipt"]["executor"] = None  # the briefs forbid trailers; no 13.05 row
        if pid == "R8" and rep.endswith("+13.05"):
            w["receipt"]["executor"] = None  # the 13.05 'Execution Receipts' tab has no rows
        if pid == "R9a" and rep.endswith("+13.05"):
            w["receipt"] = None
        if pid == "R9b":  # the score records a file blob, and git gives the dispatch-time file blob
            w["score"]["subject_digest"] = F["r9"]["scored_blob"] if which == 0 else F["r9"]["dispatch_time_blob"]
            w["receipt"]["subject_digest"] = F["r9"]["dispatch_time_blob"]
    return w


# ------------------------------------------------------------------ evaluation
def main() -> int:
    repo, kernel_repo, base_repo = (Path(a).resolve() for a in sys.argv[1:4])
    py, blueprint = sys.argv[4], Path(sys.argv[5])
    pre_path = HERE / "e1_predeclared.json"
    recorded = (HERE / "e1_predeclared.sha256").read_text().split()[0]
    actual = hashlib.sha256(pre_path.read_bytes()).hexdigest()
    if actual != recorded:
        print(f"predeclaration changed: {actual} != {recorded}")
        return 1
    pre = json.loads(pre_path.read_text())
    pairs = {p["id"]: p for p in pre["pairs"]}
    F = facts(repo, kernel_repo, base_repo, py, blueprint)
    P = worlds(F)
    assert set(P) == set(pairs), (set(P) ^ set(pairs))

    def expected(pid):
        p = pairs[pid]
        return (p["D"], p["D"]) if p["kind"] == "control" else (p["D0"], p["D1"])

    def verdict(pid, d0, d1):
        e0, e1 = expected(pid)
        return d0 == e0 and d1 == e1 and UND not in (d0, d1)

    reps = {}
    for rep, regime in (("A", "RECORDED"), ("A", "CAPACITY"), ("B", "RECORDED"), ("B", "CAPACITY"),
                        ("B+13.05", "RECORDED"), ("B+13.05", "CAPACITY")):
        M = frozenset({"FA"}) if rep == "A" else frozenset()
        cells = {}
        for pid, (q, w0, w1, c0, c1) in P.items():
            d0 = decide_K(q, realize(pid, w0, 0, rep, regime, F), M)
            d1 = decide_K(q, realize(pid, w1, 1, rep, regime, F), M)
            cells[pid] = {"W0": d0, "W1": d1, "ok": verdict(pid, d0, d1)}
        reps[f"{rep}/{regime}"] = cells
    cells = {}
    for pid, (q, w0, w1, c0, c1) in P.items():
        d0, d1 = decide_C(q, c0), decide_C(q, c1)
        cells[pid] = {"W0": d0, "W1": d1, "ok": verdict(pid, d0, d1)}
    reps["C"] = cells
    cells = {}
    for pid, (q, w0, w1, c0, c1) in P.items():
        d0, d1 = decide_K(q, w0), decide_K(q, w1)
        cells[pid] = {"W0": d0, "W1": d1, "ok": verdict(pid, d0, d1)}
    reps["K"] = cells
    assert all(c["ok"] for c in reps["K"].values()), "the full contract must pass every pair before ablation"

    comp = pre["components"]
    k_components = comp["records"] + comp["grant_fields"] + comp["verification_fields"] + comp["receipt_fields"] + comp["rules"]

    def k_fails(M):
        return sorted(pid for pid, (q, w0, w1, c0, c1) in P.items() if not verdict(pid, decide_K(q, w0, M), decide_K(q, w1, M)))

    single_K = {c: k_fails(frozenset({c})) for c in k_components}
    removed, kept = set(), []
    for c in k_components:
        if not k_fails(frozenset(removed | {c})):
            removed.add(c)
        else:
            kept.append(c)
    redundancy = []
    unearned = [c for c in k_components if not single_K[c]]
    for a, b in itertools.combinations(unearned, 2):
        f = k_fails(frozenset({a, b}))
        if f:
            redundancy.append({"pair": [a, b], "jointly_collapse": f})

    c_full_ok = {pid for pid, c in reps["C"].items() if c["ok"]}

    def c_loses(M):
        return sorted(pid for pid, (q, w0, w1, c0, c1) in P.items()
                      if pid in c_full_ok and not verdict(pid, decide_C(q, c0, M), decide_C(q, c1, M)))

    single_C = {c: c_loses(frozenset({c})) for c in comp["gemini_fields"]}

    primaries = [pid for pid in P if pairs[pid]["kind"] == "primary"]
    controls = [pid for pid in P if pairs[pid]["kind"] == "control"]
    fails = {k: sorted(pid for pid, c in v.items() if not c["ok"]) for k, v in reps.items()}
    exp = pre["expected"]
    comparison = {
        "A/CAPACITY": {"expected_fail": exp["A"]["CAPACITY_fail"], "actual_fail": fails["A/CAPACITY"]},
        "A/RECORDED": {"expected_fail": exp["A"]["RECORDED_fail"], "actual_fail": fails["A/RECORDED"]},
        "B/CAPACITY": {"expected_fail": exp["B"]["CAPACITY_fail"], "actual_fail": fails["B/CAPACITY"]},
        "B/RECORDED": {"expected_fail": exp["B"]["RECORDED_fail"], "actual_fail": fails["B/RECORDED"]},
        "C": {"expected_fail": exp["C"]["fail"], "actual_fail": fails["C"]},
        "K_single_removal_earned": {"expected": sorted(exp["K_single_removal_earned"]), "actual": sorted(c for c, f in single_K.items() if f)},
        "K_single_removal_unearned": {"expected": sorted(exp["K_single_removal_unearned"]), "actual": sorted(c for c, f in single_K.items() if not f)},
        "C_single_removal_unearned": {"expected": sorted(exp["C_single_removal_unearned"]), "actual": sorted(c for c, f in single_C.items() if not f)},
    }
    for v in comparison.values():
        a, b = (v.get("expected_fail", v.get("expected")), v.get("actual_fail", v.get("actual")))
        v["match"] = sorted(a) == sorted(b)
    b_cap_primary_fail = [p for p in fails["B/CAPACITY"] if p in primaries]
    b_cap_control_fail = [p for p in fails["B/CAPACITY"] if p in controls]
    out = {"predeclaration_sha256": actual,
           "post_run_harness_changes": ["run 1 read preoutcome_scores.json from f2249c1, where it does not exist; it is read from d49480e",
                                        "run 2 left the aggregate unset for single-requirement pairs, so masking req_per_check also collapsed P3a, P3b, P3c and P6; the aggregate now defaults to the combination of the derived results. No verdict and no earned/unearned classification changed."],
           "facts": F, "matrix": reps, "fails": fails,
           "K_single_removal": single_K, "K_backward_elimination": {"order": k_components, "irreducible": kept, "removed": sorted(removed)},
           "K_redundancy_among_unearned": redundancy, "C_single_removal": single_C, "comparison": comparison,
           "stop_rule": {"B_capacity_primary_fail": b_cap_primary_fail, "B_capacity_control_fail": b_cap_control_fail,
                         "B_plus_owner_side_capacity_fail": fails["B+13.05/CAPACITY"],
                         "STOP": not b_cap_primary_fail}}
    (HERE / "e1_results.json").write_text(json.dumps(out, indent=1, default=str) + "\n")

    # markdown matrix
    cols = ["A/RECORDED", "A/CAPACITY", "B/RECORDED", "B/CAPACITY", "B+13.05/CAPACITY", "C", "K"]
    L = ["# E1 matrix", "", f"Predeclaration sha256 `{actual}`. A cell is `W0/W1` decisions; ✓ = correct and, for a primary pair, different.", "",
         "| pair | kind | query | expected | " + " | ".join(cols) + " |", "|" + "---|" * (4 + len(cols))]
    for pid in P:
        e0, e1 = expected(pid)
        row = [pid, pairs[pid]["kind"], pairs[pid]["query"], f"{e0}/{e1}"]
        for c in cols:
            cell = reps[c][pid]
            row.append(f"{'✓' if cell['ok'] else '✗'} {cell['W0']}/{cell['W1']}")
        L.append("| " + " | ".join(row) + " |")
    L += ["", "## K single-component removal", "", "| component | pairs that collapse |", "|---|---|"]
    L += [f"| `{c}` | {', '.join(f) if f else '— (unearned)'} |" for c, f in single_K.items()]
    L += ["", f"Backward elimination, listed order, irreducible set: {', '.join('`'+c+'`' for c in kept)}", ""]
    L += ["## C single-field removal (pairs C already passes that it loses)", "", "| field | pairs lost |", "|---|---|"]
    L += [f"| `{c}` | {', '.join(f) if f else '— (unearned)'} |" for c, f in single_C.items()]
    L += ["", "## Expected versus actual", ""]
    L += [f"- {k}: {'match' if v['match'] else 'DIFFERS'} — expected {v.get('expected_fail', v.get('expected'))}, actual {v.get('actual_fail', v.get('actual'))}" for k, v in comparison.items()]
    L += ["", f"STOP rule: B/CAPACITY primary failures {b_cap_primary_fail or 'none'}; controls {b_cap_control_fail or 'none'}; with the owner-side 13.05 record type: {fails['B+13.05/CAPACITY'] or 'none'}."]
    (HERE / "e1_matrix.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
