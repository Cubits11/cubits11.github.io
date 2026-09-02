#!/usr/bin/env python3
"""Prove the two prepared reporters on synthetic fixtures shaped like the harnesses' real outputs.

Each fixture is built here, in memory, with a seeded generator; the expected
joint statistics are computed a second way (brute force over items) and
asserted equal; every refusal in the input contract is proven by a planted
violation, through the CLI where the contract is a declared exit status.
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
    bad = dict(preds); bad["C"] = {i: v for i, v in list(preds["C"].items())[:-1]}
    try:
        guardbench_joint.joint(models, bad, labels, 0.5)
        check(False, "guardbench reporter refuses misaligned ids")
    except SystemExit as exc:
        check(str(exc).startswith("UNKNOWN"), "guardbench reporter refuses misaligned ids with UNKNOWN")
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


def ape_fixture(n: int = 150, seed: int = 11) -> tuple[list[str], dict[str, dict], list[int], list[str]]:
    rng = random.Random(seed)
    x = [f"prompt {i}" for i in range(n)]
    y = [1 if i % 4 else 0 for i in range(n)]
    src = ["jailbreak_a" if i % 2 else "jailbreak_b" for i in range(n)]
    models = ["m1", "m2", "m3", "m4"]
    results = {m: {"x_test": x, "y_test": y, "y_pred": [int(rng.random() < 0.6) for _ in range(n)],
                   "y_pred_prob": [], "history": [], "source": src} for m in models}
    return models, results, y, src


def write_pickles(root: Path, results: dict, data: str = "pool") -> None:
    for m, r in results.items():
        with (root / f"result_{m}_{data}.pickle").open("wb") as fh:
            pickle.dump(r, fh)


def run_ape(root: Path, models: list[str], data: str = "pool.json") -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(HERE / "ape_joint.py"), "--data", data, "--models", *models,
                           "--dir", str(root), "--json"], capture_output=True, text=True)


def test_ape() -> None:
    models, results, y, src = ape_fixture()
    n = len(y)
    out = ape_joint.joint(models, results)
    for source in sorted(set(src)):
        idx = [i for i, s in enumerate(src) if s == source]
        pos = [i for i in idx if y[i] == 1]
        flags = {m: [bool(results[m]["y_pred"][i]) for i in range(n)] for m in models}
        u, am, ex = brute(flags, pos)
        r = out[source]
        check(r["union"] == u and r["all_miss"] == am and r["exclusive_coverage"] == ex
              and all(r["leave_one_out_union"][m] == u - ex[m] for m in models),
              f"ape reporter [{source}] matches brute force (union {u}, all-miss {am}, LOO consistent)")
    # filename normalization: the harness strips .json before naming the pickle
    check(ape_joint.data_name("sub_sample_filtered_data.json") == "sub_sample_filtered_data"
          and ape_joint.data_name("sub_sample_filtered_data") == "sub_sample_filtered_data",
          "ape --data accepts the .json form and resolves the harness's result name")
    check(str(ape_joint.result_path(Path("scripts"), "langkit", "ood_filtered_data.json")).endswith("scripts/result_langkit_ood_filtered_data.pickle"),
          "ape result path is result_<model>_<data-without-.json>.pickle")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_pickles(root, results)
        ok_run = run_ape(root, models)
        check(ok_run.returncode == 0 and set(json.loads(ok_run.stdout)) == {"jailbreak_a", "jailbreak_b"},
              "ape CLI runs on harness-shaped pickles with --data given as .json")
        # every contract violation exits 2 with a REFUSED diagnostic and prints no statistic
        def planted(name: str, mutate) -> None:
            _, bad, _, _ = ape_fixture()
            mutate(bad)
            with tempfile.TemporaryDirectory() as t2:
                r2 = Path(t2); write_pickles(r2, bad)
                run = run_ape(r2, models)
                check(run.returncode == ape_joint.EXIT_REFUSED and "REFUSED" in run.stderr and not run.stdout.strip(),
                      f"ape CLI refuses (exit 2, nothing printed) on {name}: {run.stderr.strip()[:90]}")
        planted("prompt mismatch", lambda b: b["m4"].__setitem__("x_test", list(reversed(b["m4"]["x_test"]))))
        planted("source mismatch", lambda b: b["m2"].__setitem__("source", list(reversed(b["m2"]["source"]))))
        planted("label mismatch", lambda b: b["m3"].__setitem__("y_test", [1 - v for v in b["m3"]["y_test"]]))
        planted("y_pred length mismatch", lambda b: b["m1"].__setitem__("y_pred", b["m1"]["y_pred"][:-1]))
        planted("x/y length mismatch", lambda b: b["m2"].__setitem__("y_test", b["m2"]["y_test"][:-3]))
        planted("non-binary label", lambda b: b["m1"]["y_test"].__setitem__(0, 2))
        planted("non-binary prediction", lambda b: b["m2"]["y_pred"].__setitem__(5, 0.7))
        planted("missing field", lambda b: b["m3"].pop("source"))
        one = run_ape(root, ["m1"])
        check(one.returncode == ape_joint.EXIT_REFUSED and "at least two" in one.stderr, "ape CLI refuses a single model (exit 2)")
        dup = run_ape(root, ["m1", "m1"])
        check(dup.returncode == ape_joint.EXIT_REFUSED and "unique" in dup.stderr, "ape CLI refuses duplicate model names (exit 2)")
        missing = run_ape(root, ["m1", "nope"])
        check(missing.returncode == 1 and "not found" in missing.stderr, "ape CLI exits 1 with the expected filename when a pickle is missing")
    check("unpickling can execute code" in " ".join(ape_joint.__doc__.split()),
          "ape docstring discloses the pickle trust boundary")


def main() -> int:
    test_guardbench()
    test_ape()
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("ok    prepared joint reporters: match brute force, honour the input contract, refuse with the declared status")
    return 0


if __name__ == "__main__":
    sys.exit(main())
