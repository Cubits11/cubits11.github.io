#!/usr/bin/env python3
"""The repository's dependency and evidence graph, derived, never hand-drawn.

    python3 scripts/repo_graph.py            # write docs/graph/repo-graph.{json,mmd}
    python3 scripts/repo_graph.py --check    # drift gate: fail if the written graph is stale
    python3 scripts/repo_graph.py --orient   # cold-entry briefing: state, drift, windows, contradictions
    python3 scripts/repo_graph.py --tasks    # the next actions the detectors imply, one per line

What it reads (and only this):
  claims.yaml                     claims, local sha pins, review windows
  scripts/verification_manifest.py the CHECKS tuple — the trunk every gate hangs from
  scripts/**/*.py                 static path references, classified read / write
  experiments/*/                  governing documents present, result rows, freeze ordering in git
  git                             branches, ancestry against origin/main, last commit per experiment file
  distribution/outcomes.yaml      qualified external outcomes

Every edge carries `basis`: STATIC_REF (a path literal seen in the script), PIN (a
sha256 the registry binds), MANIFEST (the check tuple), or GIT (commit ancestry).
An inferred edge is labelled inferred; nothing here is promoted to a fact.

Detectors (each is a failure the repository's own rules name):
  D1 count-speech      a numeral in CLAUDE.md / README.md about the check count that is not the count
  D2 generated drift   a generator whose --check fails
  D3 review window     a claim within 14 days of, or past, its review window
  D4 branch topology   a local or remote branch not reachable from origin/main, with ahead/behind
  D5 post-outcome edit a commit touching an experiment's PREREG / freeze / config after its results first existed
  D6 seed mismatch     an experiment config whose seed string differs from its draw script's
  D7 duplicate freeze  byte-identical freeze files held twice
  D8 untracked test    a test file no manifest check and no CI job runs

The graph and the briefing are the same computation; the briefing is the graph read aloud.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "graph"
OUT_JSON = OUT_DIR / "repo-graph.json"
OUT_MMD = OUT_DIR / "repo-graph.mmd"
sys.path.insert(0, str(ROOT / "scripts"))

PATH_RE = re.compile(r'"([A-Za-z0-9_./\-*]+\.(?:ya?ml|json|jsonl|html|csv|md|py|txt|xml|cff|cjs|js|blend|mp4|png|jpg))"')
CHAIN_RE = re.compile(r'(?:ROOT|FILMS|PILOT|HERE|BASE|REPO|DOCS|EXP)\s*/\s*"([^"]+)"(?:\s*/\s*"([^"]+)")*')
WRITE_HINTS = ("write_text", "write_bytes", '"w"', "'w'", "wb", "OUT", "target", "dest")
TODAY = dt.date.today()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ── nodes and edges ──────────────────────────────────────────────────────────
def scan_scripts() -> tuple[list, list]:
    nodes, edges = [], []
    for script in sorted(ROOT.glob("scripts/**/*.py")):
        if "__pycache__" in script.parts:
            continue
        rel = script.relative_to(ROOT).as_posix()
        text = script.read_text(errors="replace")
        kind = ("generator" if script.name.startswith(("generate_", "build_")) or script.name in ("bind_facts.py", "slate.py")
                else "verifier" if script.name.startswith(("verify_", "check_")) or script.name.startswith("test_")
                else "instrument")
        nodes.append({"id": rel, "type": "script", "kind": kind,
                      "has_check_mode": "--check" in text, "has_test_mode": "--test" in text})
        refs = set()
        for line in text.splitlines():
            found = [m for m in PATH_RE.findall(line)]
            for m in CHAIN_RE.finditer(line):
                parts = [p for p in re.findall(r'"([^"]+)"', m.group(0))]
                found.append("/".join(parts))
            for f in found:
                if f.startswith(("http", "-")) or f == rel:
                    continue
                writes = any(h in line for h in WRITE_HINTS)
                refs.add((f, "writes" if writes else "reads"))
        for f, rel_kind in sorted(refs):
            edges.append({"from": rel, "to": f, "rel": rel_kind, "basis": "STATIC_REF", "inferred": True})
    return nodes, edges


def manifest_edges() -> tuple[list, list]:
    import verification_manifest as vm  # noqa: WPS433
    nodes = [{"id": "scripts/verification_manifest.py", "type": "trunk", "checks": len(vm.CHECKS)}]
    edges = []
    for entry in vm.CHECKS:
        name, script, *args = entry
        edges.append({"from": "scripts/verification_manifest.py", "to": script, "rel": "runs",
                      "basis": "MANIFEST", "check": name, "args": list(args), "inferred": False})
    return nodes, edges


def claim_nodes() -> tuple[list, list]:
    reg = yaml.safe_load((ROOT / "claims.yaml").read_text())
    nodes, edges = [], []
    for c in reg["claims"]:
        reviewed = dt.date.fromisoformat(str(c["last_reviewed"]))
        due = reviewed + dt.timedelta(days=int(c["review_window_days"]))
        nodes.append({"id": c["id"], "type": "claim", "last_reviewed": reviewed.isoformat(),
                      "review_due": due.isoformat(), "days_left": (due - TODAY).days,
                      "support_url": (c.get("support") or {}).get("url"),
                      "consequence": (c.get("falsifier") or {}).get("consequence")})
        for t in c.get("review_triggers") or []:
            if t.get("type") == "local_content_change":
                p = ROOT / t["path"]
                edges.append({"from": c["id"], "to": t["path"], "rel": "pins", "basis": "PIN",
                              "sha256": t["sha256"], "holds": p.exists() and sha(p) == t["sha256"], "inferred": False})
    return nodes, edges


def experiment_nodes() -> tuple[list, list, list]:
    nodes, edges, findings = [], [], []
    for exp in sorted((ROOT / "experiments").iterdir()):
        if not exp.is_dir():
            continue
        rel = exp.relative_to(ROOT).as_posix()
        docs = {n: (exp / n).exists() for n in ("PREREG.md", "RESULT.md", "freeze/FREEZE.md")}
        stops = sorted(p.name for p in exp.glob("STOP-*.md"))
        rows = 0
        for r in exp.glob("results/**/*.jsonl"):
            rows += sum(1 for _ in r.open())
        # D5: any commit to governing files after the first results commit?
        result_files = [p for p in exp.glob("results/**/*") if p.is_file()]
        first_result = None
        for p in result_files:
            d = git("log", "--diff-filter=A", "--format=%ct", "--", p.relative_to(ROOT).as_posix()).splitlines()
            if d:
                t = int(d[-1])
                first_result = t if first_result is None else min(first_result, t)
        governed = [p for pat in ("PREREG.md", "freeze/*", "*_config.json") for p in exp.glob(pat) if p.is_file()]
        post = []
        if first_result:
            for p in governed:
                for line in git("log", "--format=%h %ct %s", "--", p.relative_to(ROOT).as_posix()).splitlines():
                    h, ct, *msg = line.split(" ", 2)
                    if int(ct) > first_result:
                        post.append({"file": p.relative_to(ROOT).as_posix(), "commit": h, "subject": " ".join(msg)})
        if post:
            findings.append({"detector": "D5", "severity": "STOP", "experiment": rel, "edits_after_results": post})
        # D6: seed in config vs draw.py
        cfg = next(iter(exp.glob("*_config.json")), None)
        draw = exp / "run" / "draw.py"
        if cfg and draw.exists():
            try:
                cfg_seed = json.loads(cfg.read_text()).get("seed")
            except Exception:
                cfg_seed = None
            m = re.search(r'SEED\s*=\s*"([^"]+)"', draw.read_text())
            if cfg_seed and m and cfg_seed != m.group(1):
                findings.append({"detector": "D6", "severity": "RECORD", "experiment": rel,
                                 "config_seed": cfg_seed, "draw_seed": m.group(1),
                                 "note": "config is a frozen file; correcting it after results is a post-hoc edit — record, do not edit"})
        nodes.append({"id": rel, "type": "experiment", "docs": docs, "stops": stops,
                      "observation_rows": rows, "first_result_commit_epoch": first_result})
        for p in governed:
            edges.append({"from": rel, "to": p.relative_to(ROOT).as_posix(), "rel": "governed_by", "basis": "GIT", "inferred": False})
    # D7: duplicate freeze files
    seen: dict[str, list[str]] = {}
    for p in ROOT.glob("experiments/*/freeze/*.csv"):
        seen.setdefault(sha(p), []).append(p.relative_to(ROOT).as_posix())
    for digest, paths in seen.items():
        if len(paths) > 1:
            findings.append({"detector": "D7", "severity": "RECORD", "sha256": digest, "paths": paths,
                             "bytes": (ROOT / paths[0]).stat().st_size,
                             "note": "each freeze is self-contained by design; the duplication is the price of that and is recorded, not removed"})
    return nodes, edges, findings


def branch_nodes() -> tuple[list, list]:
    nodes, findings = [], []
    git("fetch", "--quiet", "origin")
    refs = [r for r in git("for-each-ref", "--format=%(refname:short) %(objectname:short)", "refs/heads", "refs/remotes").splitlines()]
    for line in refs:
        name, obj = line.split()
        if name.endswith("/HEAD"):
            continue
        counts = git("rev-list", "--left-right", "--count", f"origin/main...{name}")
        behind, ahead = (int(x) for x in counts.split()) if counts else (0, 0)
        merged = git("merge-base", "--is-ancestor", name, "origin/main") == "" and ahead == 0
        n = {"id": name, "type": "branch", "head": obj, "ahead_of_origin_main": ahead,
             "behind_origin_main": behind, "reachable_from_origin_main": merged,
             "last_commit": git("log", "-1", "--format=%cs", name)}
        nodes.append(n)
        if not merged and name != "origin/main":
            findings.append({"detector": "D4", "severity": "TOPOLOGY", "branch": name, "ahead": ahead, "behind": behind})
    return nodes, findings


def count_speech_findings(check_count: int) -> list:
    findings = []
    for doc in ("CLAUDE.md", "README.md", "CONTRIBUTING.md"):
        p = ROOT / doc
        if not p.exists():
            continue
        for i, line in enumerate(p.read_text().splitlines(), 1):
            for m in re.finditer(r"\b(\d{2,3})\s+(?:deterministic\s+)?checks\b", line):
                if int(m.group(1)) != check_count:
                    findings.append({"detector": "D1", "severity": "FIX", "file": f"{doc}:{i}",
                                     "stated": int(m.group(1)), "actual": check_count})
    return findings


def drift_findings(script_nodes: list) -> list:
    findings = []
    for n in script_nodes:
        if n["kind"] == "generator" and n["has_check_mode"]:
            r = subprocess.run([sys.executable, n["id"], "--check"], cwd=ROOT, capture_output=True, text=True)
            if r.returncode != 0:
                findings.append({"detector": "D2", "severity": "FIX", "generator": n["id"],
                                 "tail": (r.stdout + r.stderr).strip().splitlines()[-1:] })
    return findings


def window_findings(claims: list) -> list:
    return [{"detector": "D3", "severity": "REVIEW" if c["days_left"] >= 0 else "FAIL", "claim": c["id"],
             "review_due": c["review_due"], "days_left": c["days_left"]}
            for c in claims if c["days_left"] <= 14]


def untracked_tests(manifest: list) -> list:
    ran = {e["to"] for e in manifest}
    ci = (ROOT / ".github" / "workflows" / "verify.yml").read_text()
    out = []
    for p in sorted(ROOT.glob("**/test_*.py")) + sorted(ROOT.glob("**/*.test.cjs")):
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith(("_private", ".")) or "__pycache__" in rel:
            continue
        if rel not in ran and rel not in ci:
            out.append({"detector": "D8", "severity": "RECORD", "test": rel, "note": "runs only when someone runs it"})
    return out


# ── assembly ─────────────────────────────────────────────────────────────────
def build(with_git: bool = True, with_drift: bool = True) -> dict:
    s_nodes, s_edges = scan_scripts()
    m_nodes, m_edges = manifest_edges()
    c_nodes, c_edges = claim_nodes()
    e_nodes, e_edges, e_findings = experiment_nodes()
    b_nodes, b_findings = branch_nodes() if with_git else ([], [])
    outcomes = yaml.safe_load((ROOT / "distribution" / "outcomes.yaml").read_text()) if (ROOT / "distribution" / "outcomes.yaml").exists() else {}
    findings = (count_speech_findings(m_nodes[0]["checks"]) + (drift_findings(s_nodes) if with_drift else [])
                + window_findings(c_nodes) + e_findings + b_findings + untracked_tests(m_edges))
    findings += [{"detector": "PIN", "severity": "FAIL", "claim": e["from"], "path": e["to"]}
                 for e in c_edges if not e["holds"]]
    import distribute
    distribution_posts = distribute.draft()
    distribution_report = distribute.learn(distribute.records("publications.json"), distribute.records("metrics.json"))
    d_nodes = [{"id": "distribution/traction", "type": "distribution",
                "queued": len(distribution_posts), "published": distribution_report["publication_count"],
                "metric_snapshots": distribution_report["snapshot_count"],
                "state": "owner_review_only"}]
    d_edges = [{"from": "distribution/traction", "to": cid, "rel": "distributes",
                "basis": "REGISTRY", "inferred": False}
               for cid in sorted({c for p in distribution_posts for c in p["claims"]})]
    graph = {
        "schema": "repo-graph v0.1",
        "generated_from": {"head": git("rev-parse", "--short", "HEAD"), "branch": git("rev-parse", "--abbrev-ref", "HEAD")},
        "nodes": s_nodes + m_nodes + c_nodes + e_nodes + b_nodes + d_nodes,
        "edges": s_edges + m_edges + c_edges + e_edges + d_edges,
        "external": {"qualified_outcomes": sum(len(v) for v in (outcomes.get("qualified") or {}).values())},
        "findings": findings,
    }
    return graph


def stable(graph: dict) -> dict:
    """Strip fields that change without the repository changing, for the drift gate."""
    g = json.loads(json.dumps(graph))
    g.pop("generated_from", None)
    g.pop("stable_digest", None)
    g["nodes"] = [n for n in g["nodes"] if n["type"] != "branch"]
    for n in g["nodes"]:
        n.pop("days_left", None)
    g["findings"] = [f for f in g["findings"] if f["detector"] not in ("D3", "D4", "D2")]
    return g


def mermaid(graph: dict) -> str:
    lines = ["graph LR"]
    ids = {}

    def nid(s: str) -> str:
        if s not in ids:
            ids[s] = f"n{len(ids)}"
        return ids[s]
    for n in graph["nodes"]:
        if n["type"] in ("trunk", "claim", "experiment", "distribution") or (n["type"] == "script" and n["kind"] == "generator"):
            lines.append(f'  {nid(n["id"])}["{n["id"]}"]')
    for e in graph["edges"]:
        if e["basis"] in ("MANIFEST", "PIN", "REGISTRY") or e["rel"] == "governed_by":
            lines.append(f'  {nid(e["from"])} -->|{e["rel"]}| {nid(e["to"])}')
    return "\n".join(lines) + "\n"


def orient(graph: dict) -> str:
    out = [f"REPO GRAPH · {TODAY} · head {graph['generated_from']['head']} on {graph['generated_from']['branch']}", ""]
    trunk = next(n for n in graph["nodes"] if n["type"] == "trunk")
    claims = [n for n in graph["nodes"] if n["type"] == "claim"]
    exps = [n for n in graph["nodes"] if n["type"] == "experiment"]
    scripts = [n for n in graph["nodes"] if n["type"] == "script"]
    out.append(f"TRUNK   scripts/verification_manifest.py runs {trunk['checks']} checks")
    out.append(f"ROOTS   {len(claims)} claims · {sum(1 for e in graph['edges'] if e['basis']=='PIN')} local sha pins · "
               f"{sum(1 for n in scripts if n['kind']=='generator')} generators · {sum(1 for n in scripts if n['kind']=='verifier')} verifiers")
    out.append("")
    d = next(n for n in graph["nodes"] if n["type"] == "distribution")
    out.append(f"DISTRIBUTION {d['queued']} held drafts · {d['published']} publications · {d['metric_snapshots']} snapshots; python3 scripts/distribute.py orient")
    out.append("EXPERIMENTS")
    for e in exps:
        d = e["docs"]
        out.append(f"  {e['id']:<18} rows {e['observation_rows']:>5}  prereg {'✓' if d['PREREG.md'] else '·'}  "
                   f"freeze {'✓' if d['freeze/FREEZE.md'] else '·'}  result {'✓' if d['RESULT.md'] else '·'}  stops {len(e['stops'])}")
    out.append("")
    soon = sorted(claims, key=lambda c: c["days_left"])[:5]
    out.append("REVIEW WINDOWS (soonest five)")
    for c in soon:
        out.append(f"  {c['id']:<10} due {c['review_due']}  {c['days_left']:>4} d")
    out.append("")
    out.append("BRANCHES not reachable from origin/main")
    for n in graph["nodes"]:
        if n["type"] == "branch" and not n["reachable_from_origin_main"] and n["id"] != "origin/main":
            out.append(f"  {n['id']:<48} +{n['ahead_of_origin_main']} / -{n['behind_origin_main']}  last {n['last_commit']}")
    out.append("")
    out.append(f"EXTERNAL qualified outcomes {graph['external']['qualified_outcomes']}")
    rec = OUT_DIR / "organism.receipt.json"
    if rec.exists():
        bound = json.loads(rec.read_text()).get("graph_stable_digest")
        live = hashlib.sha256(json.dumps(stable(graph), sort_keys=True, default=str).encode()).hexdigest()
        out.append(f"ORGANISM docs/graph/organism.png {'current' if bound == live else 'STALE — python3 films/lib/blender/build_repo_organism.py'}")
    out.append("")
    out.append("FINDINGS")
    if not graph["findings"]:
        out.append("  none")
    for f in graph["findings"]:
        body = {k: v for k, v in f.items() if k not in ("detector", "severity")}
        out.append(f"  {f['detector']} {f['severity']:<8} {json.dumps(body, default=str)[:160]}")
    return "\n".join(out) + "\n"


def tasks(graph: dict) -> str:
    verbs = {"D1": "correct the stated count in", "D2": "regenerate", "D3": "re-review claim",
             "D4": "reconcile branch", "D5": "STOP — a frozen file moved after results; do not report", "D6": "record the seed mismatch for",
             "D7": "keep; recorded duplicate freeze", "D8": "decide whether the manifest should run", "PIN": "re-pin claim"}
    lines = []
    for f in graph["findings"]:
        key = f.get("file") or f.get("generator") or f.get("claim") or f.get("branch") or f.get("experiment") or f.get("test") or ",".join(f.get("paths", []))
        lines.append(f"[{f['detector']}] {verbs.get(f['detector'], 'inspect')} {key}")
    return "\n".join(lines) + ("\n" if lines else "no tasks: every detector is quiet\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="drift gate against docs/graph/repo-graph.json")
    ap.add_argument("--orient", action="store_true")
    ap.add_argument("--tasks", action="store_true")
    ap.add_argument("--no-drift", action="store_true", help="skip running every generator --check (faster)")
    a = ap.parse_args()
    graph = build(with_drift=not a.no_drift and not a.check)
    if a.orient:
        sys.stdout.write(orient(graph))
        return 0
    if a.tasks:
        sys.stdout.write(tasks(graph))
        return 0
    if a.check:
        if not OUT_JSON.exists():
            print("FAIL  docs/graph/repo-graph.json missing — run scripts/repo_graph.py")
            return 1
        current = stable(json.loads(OUT_JSON.read_text()))
        if current != stable(graph):
            print("FAIL  docs/graph/repo-graph.json is stale — run scripts/repo_graph.py")
            return 1
        print(f"ok    repo graph current: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges, "
              f"{len(graph['findings'])} live findings")
        return 0
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    graph["stable_digest"] = hashlib.sha256(json.dumps(stable(graph), sort_keys=True, default=str).encode()).hexdigest()
    OUT_JSON.write_text(json.dumps(graph, indent=1, sort_keys=True, default=str) + "\n")
    OUT_MMD.write_text(mermaid(graph))
    print(f"wrote {OUT_JSON.relative_to(ROOT)} ({len(graph['nodes'])} nodes, {len(graph['edges'])} edges, {len(graph['findings'])} findings) and {OUT_MMD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
