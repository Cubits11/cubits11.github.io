"""Disable each falsifier_assessment rule in a temporary copy of the kernel and record which mutants flip.
Usage: disable_controls.py <repo_dir> <python>"""
import json, re, subprocess, sys
from pathlib import Path
repo, py = Path(sys.argv[1]), sys.argv[2]
src = (repo / "scripts/claims_history.py").read_text()
FAIL_V1a = 'R.fail(f"{where}: subject_transition_digest names no earlier entry (V1)")'
FAIL_V1b = 'R.fail(f"{where}: a falsifier assessment targets a transition, not a {target.get(\'kind\')} (V1)")'
FAIL_V4 = 'R.fail(f"{where}: an assessment cannot be recorded before the genesis or its subject transition (V4)")'
V2_block = ('R.fail(f"{where}: the subject\'s predecessor has no falsifier — the relation is NOT_APPLICABLE, "\n'
            '                               f"derived, and storing an assessment of it is an error (V2)")')
V3_block = ('R.fail(f"{where}: falsifier_assessment {e.get(\'falsifier_assessment\')!r} is not one of "\n'
            '                       f"{list(ASSESSMENT_VALUES)}; NOT_APPLICABLE and UNASSESSED are derived, never stored (V3)")')
V5_block = ('R.fail(f"{where}: a falsifier assessment carries exactly {sorted(ASSESSMENT_KEYS)} "\n'
            '                       f"(extra {sorted(keys - ASSESSMENT_KEYS)}, missing {sorted(ASSESSMENT_KEYS - keys)}) (V5)")')
F14_old = ('if pred is None and not use_git and target.get("provenance_class") == "RETROSPECTIVE_RECONSTRUCTION":')
F14_new = ('if False:')
controls = {"V1 no earlier entry": (FAIL_V1a, "pass"), "V1 target not a transition": (FAIL_V1b, "pass"),
            "V2 predecessor falsifier null": (V2_block, "pass"), "V3 enum": (V3_block, "pass"),
            "V4 dates": (FAIL_V4, "pass"), "V5 closed keys": (V5_block, "pass"),
            "no-git retrospective = unknown (F14)": (F14_old, F14_new)}
out = {}
for name, (old, new) in controls.items():
    assert src.count(old) == 1, (name, src.count(old))
    tmp = repo / "scripts/_mut_claims_history.py"
    tmp.write_text(src.replace(old, new))
    try:
        p = subprocess.run([py, str(tmp), "--test"], cwd=repo, capture_output=True, text=True)
    finally:
        tmp.unlink()
    flipped = sorted({m.group(1) for m in re.finditer(r"^(?:FAIL|not ok|MISBEHAVED|x)\S*\s+(F\d+b?|M\d+|[A-Z]\d+b?)\b", p.stdout, re.M)})
    bad = [l for l in p.stdout.splitlines() if l and not l.startswith("ok") and not l.startswith("  ")]
    out[name] = {"rc": p.returncode, "flipped": [re.split(r"\s+", l, 2)[1] for l in bad if re.match(r"^\S+\s+[A-Z]\d", l)], "summary": bad[-1] if bad else p.stdout.splitlines()[-1]}
print(json.dumps(out, indent=1))
