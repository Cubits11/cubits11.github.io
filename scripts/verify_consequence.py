#!/usr/bin/env python3
"""Verify the external-consequence system: experiments, intake, launch units, dossiers.

  * distribution/experiments.yaml — every experiment names an existing
    command, registered claims, bound fact ids, a film with a manifest, and
    report routes whose issue template and prefilled field ids exist; the two
    offline experiments are EXECUTED and their final lines must equal the
    line the page promises.
  * .github/ISSUE_TEMPLATE/*.yml — parse, carry unique field ids, required
    fields, and the dropdown options the prefilled links rely on.
  * distribution/launch-units.yaml — every unit names an existing film,
    poster, master, manifest, registered campaign id, experiment id and
    evidence route; a comprehension question and scoring rule exist before
    any trial is recorded; nothing is marked SENT.
  * distribution/dossiers — one file per row named in the README table, and
    every row id exists in census.yaml.
  * try/index.html — every prefilled issue link names a real template and only
    real field ids.

No network. Exit 1 on any failure.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import verify_census  # noqa: E402

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL  {msg}")


def ok(msg: str) -> None:
    print(f"ok    {msg}")


def load_templates() -> dict[str, dict]:
    out = {}
    for p in sorted((ROOT / ".github" / "ISSUE_TEMPLATE").glob("*.yml")):
        spec = yaml.safe_load(p.read_text())
        ids, options = [], {}
        for item in spec.get("body", []):
            fid = item.get("id")
            if fid:
                if fid in ids:
                    fail(f"{p.name}: duplicate field id {fid}")
                ids.append(fid)
                if item.get("type") == "dropdown":
                    options[fid] = list(item["attributes"]["options"])
        for req in ("name", "description", "title", "labels"):
            if req not in spec:
                fail(f"{p.name}: missing {req}")
        out[p.name] = {"ids": set(ids), "options": options}
    return out


def check_url(url: str, templates: dict, where: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.netloc != "github.com" or not parsed.path.endswith("/issues/new"):
        return
    q = dict(urllib.parse.parse_qsl(parsed.query))
    t = q.get("template")
    if t not in templates:
        fail(f"{where}: prefilled link names template {t!r}, which does not exist")
        return
    for key, value in q.items():
        if key in ("template", "title", "labels"):
            continue
        if key not in templates[t]["ids"]:
            fail(f"{where}: prefilled field {key!r} is not a field of {t}")
        elif key in templates[t]["options"] and value not in templates[t]["options"][key]:
            fail(f"{where}: prefilled {key}={value!r} is not an option of {t}")


def check_experiments(templates: dict) -> dict:
    data = yaml.safe_load((ROOT / "distribution" / "experiments.yaml").read_text())
    claims = {c["id"] for c in yaml.safe_load((ROOT / "claims.yaml").read_text())["claims"]}
    facts = json.loads((ROOT / "films" / "data" / "facts.json").read_text())["facts"]
    ids = set()
    for e in data["experiments"]:
        eid = e["id"]
        ids.add(eid)
        for f in ("id", "slug", "title", "minutes", "question", "film", "claims", "input", "command", "variant",
                  "expected_facts", "expected_final_line", "epistemic_status", "falsifier", "non_claim",
                  "report_agree", "report_disagree", "deeper"):
            if f not in e:
                fail(f"{eid}: missing {f}")
        script = e["command"].split()[1] if e["command"].startswith("python3 ") else None
        if not script or not (ROOT / script).exists():
            fail(f"{eid}: command names a script that does not exist: {e['command']}")
        for c in e["claims"]:
            if c not in claims:
                fail(f"{eid}: claim {c} is not registered")
        for f in e["expected_facts"]:
            if f not in facts:
                fail(f"{eid}: fact {f} is not bound")
        if not (ROOT / "films" / e["film"] / "manifest.yaml").exists():
            fail(f"{eid}: film {e['film']} has no manifest")
        for route in ("report_agree", "report_disagree"):
            r = e[route]
            if r["template"] not in templates:
                fail(f"{eid}: {route} names template {r['template']} which does not exist")
            else:
                for key, value in r["prefill"].items():
                    if key not in templates[r["template"]]["ids"]:
                        fail(f"{eid}: {route} prefills {key!r}, not a field of {r['template']}")
                    elif key in templates[r["template"]]["options"] and value not in templates[r["template"]]["options"][key]:
                        fail(f"{eid}: {route} prefills {key}={value!r}, not an option")
        deeper = ROOT / e["deeper"].strip("/") / "index.html"
        if not deeper.exists():
            fail(f"{eid}: deeper route {e['deeper']} is not a committed page")
    # execute the offline experiments and compare final lines
    runs = {"TRY-A": ["python3", "scripts/try_same_scores.py"],
            "TRY-C": ["python3", "scripts/try_audit.py", "--answers", "fixtures/try/audit-example.json"]}
    for e in data["experiments"]:
        if e["id"] not in runs:
            continue
        cmd = [sys.executable, *runs[e["id"]][1:]]
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        if r.returncode != 0:
            fail(f"{e['id']}: {' '.join(cmd)} exited {r.returncode}: {r.stderr.strip()[-200:]}")
        elif last != e["expected_final_line"]:
            fail(f"{e['id']}: final line {last!r} != promised {e['expected_final_line']!r}")
        else:
            ok(f"{e['id']} executes offline and prints the promised final line")
    for route in data.get("film_routes", []):
        if not (ROOT / "films" / route["film"] / "manifest.yaml").exists():
            fail(f"film_routes: {route['film']} has no manifest")
        if route.get("experiment") and route["experiment"] not in ids:
            fail(f"film_routes: {route['film']} routes to unknown experiment {route['experiment']}")
    if not failures:
        ok(f"experiments.yaml: {len(ids)} experiments bound to registered claims, facts, films and intake routes")
    return {"ids": ids}


def check_launch_units(experiment_ids: set) -> None:
    units = yaml.safe_load((ROOT / "distribution" / "launch-units.yaml").read_text())
    campaigns = {row["id"] for row in yaml.safe_load((ROOT / "campaigns.yaml").read_text())["campaigns"]}
    seen = set()
    for u in units["units"]:
        film = u["film"]
        for f in ("campaign", "evidence_url", "experiment_url", "poster", "master", "claim_sentence", "technical_paragraph",
                  "cta", "accessible_description", "post_draft", "comprehension_question", "scoring_rule", "sequence", "order"):
            if not u.get(f):
                fail(f"launch unit {film}: missing {f}")
        for f in ("poster", "master"):
            if u.get(f) and not (ROOT / u[f]).exists():
                fail(f"launch unit {film}: {f} {u[f]} does not exist")
        if not (ROOT / "films" / film / "manifest.yaml").exists():
            fail(f"launch unit {film}: no film manifest")
        if u.get("campaign") not in campaigns:
            fail(f"launch unit {film}: campaign {u.get('campaign')} is not registered in campaigns.yaml")
        if u.get("experiment") and u["experiment"] not in experiment_ids:
            fail(f"launch unit {film}: experiment {u['experiment']} is not registered")
        if (film, u.get("sequence")) in seen:
            fail(f"launch unit {film}: duplicated")
        seen.add((film, u.get("sequence")))
        if re.search(r"\bSENT\b", yaml.safe_dump(u)):
            fail(f"launch unit {film}: marked SENT — the assistant sends nothing; record dispatch in campaigns.yaml readings")
        if any(word in u["cta"].lower() for word in ("learn more",)):
            fail(f"launch unit {film}: CTA ends in 'learn more'")
    ok(f"launch-units.yaml: {len(units['units'])} units bound to films, posters, campaigns and experiments; none marked sent")


def check_dossiers() -> None:
    rows = {r["id"] for r in verify_census.load()["benchmarks"]}
    readme = (ROOT / "distribution" / "dossiers" / "README.md").read_text()
    named = re.findall(r"\[([a-z0-9-]+)\]\(([a-z0-9-]+)\.md\)", readme)
    for row, file in named:
        if row not in rows:
            fail(f"dossier {row}: not a census row id")
        if not (ROOT / "distribution" / "dossiers" / f"{file}.md").exists():
            fail(f"dossier {row}: file {file}.md missing")
        text = (ROOT / "distribution" / "dossiers" / f"{file}.md").read_text()
        for n in range(1, 9):
            if f"**{n}." not in text:
                fail(f"dossier {row}: derived item {n} missing")
        if "@" in text and "[at]" not in text:
            fail(f"dossier {row}: contains an address — contact routes are de-harvested by design")
    ok(f"dossiers: {len(named)} rows, each with the eight derived items and no harvested address")


def check_try_page(templates: dict) -> None:
    page = ROOT / "try" / "index.html"
    if not page.exists():
        fail("try/index.html missing — run scripts/generate_try.py")
        return
    html = page.read_text()
    links = re.findall(r'href="([^"]*issues/new[^"]*)"', html)
    for link in links:
        check_url(link.replace("&amp;", "&"), templates, "try/index.html")
    if not links:
        fail("try/index.html has no intake links")
    for needed in ("REPRODUCE IT", 'id="try-a"', 'id="try-b"', 'id="try-c"', 'id="status"', 'id="counterexample"'):
        if needed not in html:
            fail(f"try/index.html lacks {needed!r}")
    ok(f"try/index.html: {len(links)} intake links name real templates and fields")


def main() -> int:
    templates = load_templates()
    ok(f"issue templates: {', '.join(sorted(templates))}")
    exp = check_experiments(templates)
    check_launch_units(exp["ids"])
    check_dossiers()
    check_try_page(templates)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("ok    external-consequence system verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
