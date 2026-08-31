#!/usr/bin/env python3
"""Adversarial regression tests for the portable static-OR receipt stub."""
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
SCRIPT = HERE / "joint_or.py"
FIXTURE = (HERE / "fixture.csv").read_text()
GOOD = "interpretation=shared_event\nn=4\nunion=3/4 = 0.75\nall_miss=1/4 = 0.25\n"
ACTION = (FIXTURE.replace("# interpretation: shared_event\n", "# interpretation: harness_action\n")
          .replace("# event: D=1 means the shared, declared flag event E on this fixture's items.\n",
                   "# event: D=1 means the harness takes its declared block action.\n"
                   "# action_source: fixture harness action, line 2\n")
          .replace("# event_translation: shared_source_defined\n", "")
          .replace("# event_translation_source: fixture contract, line 3\n", ""))
ACTION_GOOD = ("interpretation=harness_action\nn=4\nblocked_by_any=3/4 = 0.75\n"
               "blocked_by_none=1/4 = 0.25\n")


def run(name, text, accepted=False, expected=GOOD):
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "receipt.csv"
        path.write_text(text)
        result = subprocess.run([sys.executable, str(SCRIPT), str(path)], text=True,
                                capture_output=True)
    if accepted:
        ok = result.returncode == 0 and result.stdout == expected
    else:
        ok = result.returncode != 0 and result.stdout.startswith("UNKNOWN:") and "union=" not in result.stdout
    if not ok:
        raise SystemExit(f"FAIL {name}: exit={result.returncode}; stdout={result.stdout!r}; stderr={result.stderr!r}")
    print(f"ok  {name}")


run("good fixture", FIXTURE, accepted=True)
run("declared harness action fixture", ACTION, accepted=True, expected=ACTION_GOOD)
run("isolated default threshold", FIXTURE.replace("# threshold_rule: fixed_per_system", "# threshold_rule: default"))
run("default synonym vendor_default", FIXTURE.replace("# threshold_rule: fixed_per_system", "# threshold_rule: vendor_default"))
run("default synonym matched", FIXTURE.replace("# threshold_rule: fixed_per_system", "# threshold_rule: matched"))
run("default synonym unknown", FIXTURE.replace("# threshold_rule: fixed_per_system", "# threshold_rule: unknown"))
run("combined blank-event test", FIXTURE.replace("# event: D=1 means the shared, declared flag event E on this fixture's items.", "# event: ").replace("# threshold_rule: fixed_per_system", "# threshold_rule: default").replace("# exposure: declared_full", "# exposure: full"))
run("native-label aggregate is not a catch contract", FIXTURE.replace("# event_translation: shared_source_defined", "# event_translation: native_label_or"))
run("harness action needs a declared action", ACTION.replace("# action_source: fixture harness action, line 2\n", ""))
run("harness action cannot smuggle a shared translation", ACTION.replace("# event: D=1 means the harness takes its declared block action.", "# event_translation: native_label_or\n# event: D=1 means the harness takes its declared block action."))
run("NA decision", FIXTURE.replace("i4,B,0,fixture-v1,0.5,declared_full", "i4,B,NA,fixture-v1,0.5,declared_full"))
run("missing cell", FIXTURE.replace("i4,B,0,fixture-v1,0.5,declared_full\n", ""))
run("missing declared item", FIXTURE.replace("i4,A,0,fixture-v1,0.5,declared_full\ni4,B,0,fixture-v1,0.5,declared_full\n", ""))
run("missing declared system", "\n".join(line for line in FIXTURE.splitlines() if ",B," not in line) + "\n")
run("duplicate cell", FIXTURE + "i4,B,0,fixture-v1,0.5,declared_full\n")
run("threshold drift", FIXTURE.replace("i2,B,0,fixture-v1,0.5,declared_full", "i2,B,0,fixture-v1,0.6,declared_full"))
run("split drift", FIXTURE.replace("i2,B,0,fixture-v1,0.5,declared_full", "i2,B,0,other,0.5,declared_full"))
run("operator smuggling", FIXTURE.replace("# operator: static_or", "# operator: majority"))
run("deployed composition", FIXTURE.replace("# composition: counterfactual_static", "# composition: deployed"))
run("routed exposure", FIXTURE.replace("# exposure: declared_full", "# exposure: routed"))
print("static-OR receipt regressions passed")
