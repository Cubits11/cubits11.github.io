"""Disable each clause of the exemption test in a temporary copy and record which controls flip."""
import json, subprocess, sys, tempfile
from pathlib import Path
repo, py, harness = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
src = (repo / "tests/test_correction_dispositions.py").read_text()
clauses = {
 "legacy-prefix membership": ("                self.assertIn(t['digest'],legacy,f\"{row['claim_id']}: a governed correction needs a falsifier assessment\")\n", ""),
 "exactness": ("        self.assertEqual(set(LEGACY_UNASSESSED),unassessed,'the exemption lists exactly the legacy corrections still unassessed')\n", ""),
 "non-empty": ("        self.assertTrue(LEGACY_UNASSESSED,'the exemption is empty: delete LEGACY_UNASSESSED, LEGACY_END and this check')\n", ""),
}
res = {}
for name, (old, new) in clauses.items():
    assert src.count(old) == 1, name
    d = Path(tempfile.mkdtemp()); f = d / f"tcd_{name.replace(' ', '_').replace('-', '_')}.py"
    f.write_text(src.replace(old, new).replace("ROOT=Path(__file__).resolve().parent.parent", f"ROOT=Path({str(repo)!r})"))
    p = subprocess.run([py, harness, str(repo), str(f)], capture_output=True, text=True)
    rows = json.loads(f.with_suffix(".controls.json").read_text())
    res[name] = {"verdict_flips": [r["control"].split()[0] for r in rows if r["expected"] != r["actual"]],
                 "reason_only_flips": [r["control"].split()[0] for r in rows if r["expected"] == r["actual"] and not r["behaved"]]}
print(json.dumps(res, indent=1))
