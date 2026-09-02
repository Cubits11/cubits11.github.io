#!/usr/bin/env python3
"""Prove the two prepared reporters on synthetic fixtures shaped like the harnesses' real outputs.

Each fixture is built here, in memory, with a seeded generator; the expected
joint statistics are computed a second way (brute force over items) and
asserted equal; the alignment refusals are proven by planted misalignment.
Nothing here touches the real harnesses or claims anything about them.
"""

from __future__ import annotations

import json
import pickle
import random
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ape_joint  # noqa: E402
import guardbench_joint  # noqa: E402

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("ok    " if cond else "FAIL  ") + msg)
    if not cond:
        failures.append(msg)


def brute(flags: dict[str, list[bool]], pos: list[int]) -> tuple[int, int, dict[str, int]]:
    models = list(flags)
    union = sum(any(flags[m][i] for m in models) for i in pos)
    loo = {m: sum(any(flags[o][i] for o in models if o != m) for i in pos) for m in models}
    return union, len(pos) - union, {m: union - loo[m] for m in models}


def test_guardbench() -> None:
    rng = random.Random(7)
    ids = [f"item-{i}" for i in range(120)]
    labels = {i: (k % 3 != 0) for k, i in enumerate(ids)}
    models = ["A", "B", "C"]
    preds = {m: {i: rng.random() for i in ids} for m in models}
    r = guardbench_joint.joint(models, preds, labels, 0.5)
    pos = [k for k, i in enumerate(ids) if labels[i]]
    flags = {m: [preds[m][i] > 0.5 for i in ids] for m in models}
    u, am, ex = brute(flags, pos)
    check(r["union"] == u and r["all_miss"] == am and r["exclusive_coverage"] == ex,
          f"guardbench reporter matches brute force (union {u}, all-miss {am}, exclusive {ex})")
    check(r["union"] + r["all_miss"] == r["n_positive"], "guardbench union + all-miss = positives")
    # misalignment refusal
    bad = dict(preds); bad["C"] = {i: v for i, v in list(preds["C"].items())[:-1]}
    try:
        guardbench_joint.joint(models, bad, labels, 0.5)
        check(False, "guardbench reporter refuses misaligned ids")
    except SystemExit as exc:
        check(str(exc).startswith("UNKNOWN"), "guardbench reporter refuses misaligned ids with UNKNOWN")
    # end-to-end through the CLI on files shaped like the harness's
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "results" / "ds").mkdir(parents=True)
        for m in models:
            (root / "results" / "ds" / f"{m}.json").write_text(json.dumps(preds[m]))
        (root / "test.jsonl").write_text("\n".join(json.dumps({"id": i, "label": labels[i]}) for i in ids))
        out = subprocess.run([sys.executable, str(HERE / "guardbench_joint.py"), "--results", str(root / "results"),
                              "--dataset", "ds", "--labels", str(root / "test.jsonl"), "--models", *models, "--json"],
                             capture_output=True, text=True)
        check(out.returncode == 0 and json.loads(out.stdout)["union"] == u, "guardbench CLI runs on harness-shaped files")


def test_ape() -> None:
    rng = random.Random(11)
    n = 150
    x = [f"prompt {i}" for i in range(n)]
    y = [1 if i % 4 else 0 for i in range(n)]
    src = ["jailbreak_a" if i % 2 else "jailbreak_b" for i in range(n)]
    models = ["m1", "m2", "m3", "m4"]
    results = {m: {"x_test": x, "y_test": y, "y_pred": [int(rng.random() < 0.6) for _ in range(n)],
                   "y_pred_prob": [], "history": [], "source": src} for m in models}
    out = ape_joint.joint(models, results)
    for source in sorted(set(src)):
        idx = [i for i, s in enumerate(src) if s == source]
        pos = [i for i in idx if y[i] == 1]
        flags = {m: [bool(results[m]["y_pred"][i]) for i in range(n)] for m in models}
        u, am, ex = brute(flags, pos)
        r = out[source]
        check(r["union"] == u and r["all_miss"] == am and r["exclusive_coverage"] == ex,
              f"ape reporter [{source}] matches brute force (union {u}, all-miss {am})")
    bad = {m: dict(r) for m, r in results.items()}
    bad["m4"]["x_test"] = list(reversed(x))
    try:
        ape_joint.joint(models, bad)
        check(False, "ape reporter refuses misaligned prompts")
    except SystemExit as exc:
        check(str(exc).startswith("UNKNOWN"), "ape reporter refuses misaligned prompts with UNKNOWN")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for m in models:
            with (root / f"result_{m}_pool.json.pickle").open("wb") as fh:
                pickle.dump(results[m], fh)
        run = subprocess.run([sys.executable, str(HERE / "ape_joint.py"), "--data", "pool.json", "--models", *models,
                              "--dir", str(root), "--json"], capture_output=True, text=True)
        check(run.returncode == 0 and set(json.loads(run.stdout)) == {"jailbreak_a", "jailbreak_b"},
              "ape CLI runs on harness-shaped pickles")


def main() -> int:
    test_guardbench()
    test_ape()
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("ok    prepared joint reporters: both match brute force and refuse misalignment")
    return 0


if __name__ == "__main__":
    sys.exit(main())
