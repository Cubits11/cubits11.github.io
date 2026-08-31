#!/usr/bin/env python3
"""Reproduce MC-004 — the missing row, computed on a second public release.

Multimodal Safeguard Bench (census row multimodal-safeguard-bench-2026)
committed one Boolean verdict per item per guard for three guards over 400
harmful and 500 benign items, each stratum half text and half image. The
release prints per-guard metrics and two two-guard compositions; it prints
no three-guard union, no all-miss, no leave-one-out table, and no
catch-pattern decomposition. Those joint statistics are directly computable
from the committed verdict files, and claim MC-004 binds the result.

Discipline (the MC-002 pattern, unchanged):
  * every input file is pinned by commit AND content hash — the numbers are
    about exactly these bytes at
    PatrickKollman/Multimodal-Safeguard-Bench @ fb6f32e6, and a changed
    file fails loudly instead of silently recomputing;
  * the arithmetic is scripts/mjgd_reference.py — the same tested kernel
    the disclosure page offers to benchmark authors; strata are computed
    exactly as released (harmful/benign × text/image), never folded;
  * expected counts are read from MC-004's `expected` block in claims.yaml
    and asserted, so the proposition's numbers and the executed computation
    cannot silently diverge;
  * every quantity that overlaps the release's own printed metrics
    (metrics.json per-guard recalls and over-refusals; ensemble.json
    two-guard compositions; the paper's 30-of-36 rescue) is asserted equal
    to the printed value, so this recomputation and the source cannot
    disagree without failing;
  * the files are downloaded to memory and not committed: the upstream
    release is MIT-licensed, but this record cites and hash-verifies the
    source rather than carrying a copy that could drift from it.

Run:  python3 scripts/reanalyze_msbench.py             # downloads
      python3 scripts/reanalyze_msbench.py --dir D     # offline: a local
                                                       # checkout's
                                                       # results/full_run
"""

import hashlib
import json
import pathlib
import sys
import urllib.request

import yaml

import mjgd_reference

ROOT = pathlib.Path(__file__).resolve().parent.parent

BOUND_COMMIT = "fb6f32e6b50b6faad833b815ebcd80afd2068bff"
BASE_URL = ("https://raw.githubusercontent.com/PatrickKollman/"
            f"Multimodal-Safeguard-Bench/{BOUND_COMMIT}/results/full_run/")

GUARDS = ["llama_guard_4", "llama_guard_3_vision", "shield_gemma_2"]
ABBREV = {"llama_guard_4": "lg4", "llama_guard_3_vision": "lg3v",
          "shield_gemma_2": "sg2"}
STRATA = (("harmful", "text", 200), ("harmful", "image", 200),
          ("benign", "text", 250), ("benign", "image", 250))

SHA256 = {
    "guard_llama_guard_4_harmful.jsonl":
        "d416962d2f1a4e762fd2aee27ce6f61cbe3c4e56256542cf19cb389bce4da036",
    "guard_llama_guard_4_benign.jsonl":
        "b8fdbe4cff31fbc9e0d06a5fffd7a71325d89a60cd5b44f61fc340d9d5e16d42",
    "guard_llama_guard_3_vision_harmful.jsonl":
        "777e189833d7c689fa7ebc8ef45f47617053e27f7f3f92de497ce37e180b3c1e",
    "guard_llama_guard_3_vision_benign.jsonl":
        "73a46fd7b3fac53e85c22aee27380b13f7935195273c3ffd18b9a3e39166358e",
    "guard_shield_gemma_2_harmful.jsonl":
        "069bd28f30050684e2ce52f17570f8c75ea1e13f12d8277054068f776b7cdfe4",
    "guard_shield_gemma_2_benign.jsonl":
        "72bd24530b976438aab251efdf23f2a5d2bb1abdc8edff236da6fca76f292970",
    "metrics.json":
        "2a96c77ff6a816fec02244608ae40a045829ce5bc4c403867030c080248eb6c3",
    "ensemble.json":
        "fca2d21da716a5e38dc59b409ac09601ca1ec2a16297db357455f7d17c1a4b02",
}

SUCCESS_LINE = ("MC-004 reproduced: the three-guard joint statistics, computed "
                "from the bound public release, match the registered claim.")

failures: list = []


def summary_line(kind: str, modality: str, union: int, n: int,
                 all_miss: int) -> str:
    """One stratum's summary exactly as this script prints it. The reproduce
    page renders its expected-output receipt through this same function, so
    the page and the executed stdout cannot drift apart."""
    word = "union catches" if kind == "harmful" else "union flags"
    tail = "all-miss" if kind == "harmful" else "flagged by none"
    return (f"  {kind:>7} {modality:<5} {word} {union:>3}/{n} — "
            f"{tail} {all_miss}/{n}")


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL  {msg}")


def ok(msg: str) -> None:
    print(f"ok    {msg}")


def fetch(name: str) -> bytes:
    if "--dir" in sys.argv:
        raw = (pathlib.Path(sys.argv[sys.argv.index("--dir") + 1]) / name).read_bytes()
    else:
        req = urllib.request.Request(BASE_URL + name,
                                     headers={"User-Agent": "cubits11-mc004-repro"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != SHA256[name]:
        fail(f"{name}: sha256 {digest[:16]}… != recorded {SHA256[name][:16]}… "
             f"— the bound artifact changed; MC-004 must be re-reviewed, "
             f"not silently recomputed")
        return b""
    return raw


def pattern_key(mask: int) -> str:
    if not mask:
        return "none"
    return "+".join(ABBREV[g] for bit, g in enumerate(GUARDS) if mask & (1 << bit))


def main() -> int:
    files = {name: fetch(name) for name in SHA256}
    if failures:
        print(f"{len(failures)} check(s) failed.")
        return 1
    ok(f"{len(SHA256)} release files verified against their recorded sha256 "
       f"(commit {BOUND_COMMIT[:12]})")

    registry = yaml.safe_load((ROOT / "claims.yaml").read_text())
    mc = next((c for c in registry["claims"] if c["id"] == "MC-004"), None)
    if mc is None:
        fail("MC-004 not found in claims.yaml")
        print("1 check(s) failed.")
        return 1
    expected = mc["expected"]

    # ---------------------------------------------------------------- parse
    verdicts: dict = {}   # verdicts[kind][guard][item_id] = (blocked, modality)
    for kind in ("harmful", "benign"):
        verdicts[kind] = {}
        for guard in GUARDS:
            rows = [json.loads(line) for line in
                    files[f"guard_{guard}_{kind}.jsonl"].decode("utf-8").splitlines()]
            table: dict = {}
            for r in rows:
                if r["guard_name"] != guard:
                    fail(f"{kind}/{guard}: row names guard {r['guard_name']!r}")
                if not isinstance(r["blocked"], bool):
                    fail(f"{kind}/{guard}: non-Boolean verdict on {r['item_id']}")
                if r["item_id"] in table:
                    fail(f"{kind}/{guard}: duplicate item {r['item_id']}")
                table[r["item_id"]] = (r["blocked"], r["modality"])
            verdicts[kind][guard] = table
        ids = {guard: set(verdicts[kind][guard]) for guard in GUARDS}
        if not (ids[GUARDS[0]] == ids[GUARDS[1]] == ids[GUARDS[2]]):
            fail(f"{kind}: item-id sets differ between guards")
        modalities = {
            guard: {i: verdicts[kind][guard][i][1] for i in verdicts[kind][guard]}
            for guard in GUARDS}
        if not (modalities[GUARDS[0]] == modalities[GUARDS[1]]
                == modalities[GUARDS[2]]):
            fail(f"{kind}: modality assignments differ between guards")
    if failures:
        print(f"{len(failures)} check(s) failed.")
        return 1
    ok("one Boolean verdict per item per guard; identical item and modality "
       "sets across all three guards in both files")

    # -------------------------------------------------- per-stratum kernel
    computed: dict = {}
    for kind, modality, n_expected in STRATA:
        base = verdicts[kind][GUARDS[0]]
        items = sorted(i for i in base if base[i][1] == modality)
        if len(items) != n_expected:
            fail(f"{kind} {modality}: {len(items)} items, release documents "
                 f"{n_expected}")
            continue
        decisions = {g: [verdicts[kind][g][i][0] for i in items] for g in GUARDS}
        d = mjgd_reference.joint_disclosure(decisions, [True] * len(items))
        patterns: dict = {}
        for idx in range(len(items)):
            mask = sum(1 << bit for bit, g in enumerate(GUARDS)
                       if decisions[g][idx])
            patterns[mask] = patterns.get(mask, 0) + 1
        computed[f"{kind}_{modality}"] = {
            "n": d["denominator"],
            "per_guard": d["per_guard"],
            "union": d["union_detection"],
            "all_miss": d["all_miss"],
            "leave_one_out": {row["guard"]: row["union_without"]
                              for row in d["leave_one_out"]},
            "unique_contribution": {row["guard"]: row["unique_contribution"]
                                    for row in d["leave_one_out"]},
            "patterns": {pattern_key(mask): count
                         for mask, count in sorted(patterns.items())},
        }

    # ----------------------------------------- assert the registered claim
    for kind, modality, _n in STRATA:
        stratum = f"{kind}_{modality}"
        got, want = computed[stratum], expected[stratum]
        flag_word = "catches" if kind == "harmful" else "flags"
        checks = [
            ("denominator", got["n"], want["n"]),
            ("union", got["union"], want["union"]),
            ("all-miss" if kind == "harmful" else "flagged-by-none",
             got["all_miss"], want["all_miss"]),
        ]
        for name, have, need in checks:
            if have == need:
                ok(f"{stratum} {name}: {have} (as claimed)")
            else:
                fail(f"{stratum} {name}: computed {have}, claim says {need}")
        for guard in GUARDS:
            have = got["per_guard"][guard]
            need = want["per_guard"][guard]
            if have == need:
                ok(f"{stratum} {flag_word} {guard}: {have}/{got['n']} (as claimed)")
            else:
                fail(f"{stratum} {flag_word} {guard}: computed {have}, "
                     f"claim says {need}")
            have = got["leave_one_out"][guard]
            need = want["leave_one_out_union"][guard]
            if have == need:
                ok(f"{stratum} union without {guard}: {have}/{got['n']} "
                   f"(unique contribution "
                   f"{got['unique_contribution'][guard]})")
            else:
                fail(f"{stratum} union without {guard}: computed {have}, "
                     f"claim says {need}")
        if got["patterns"] == want["patterns"]:
            ok(f"{stratum} catch-pattern table: "
               f"{len(want['patterns'])} nonzero cells of 8 (as claimed)")
        else:
            fail(f"{stratum} catch-pattern table: computed {got['patterns']}, "
                 f"claim says {want['patterns']}")
        if sum(got["patterns"].values()) != got["n"]:
            fail(f"{stratum}: pattern cells sum to "
                 f"{sum(got['patterns'].values())}, not the denominator")

    # -------------------- assert agreement with the release's own printing
    metrics = json.loads(files["metrics.json"])
    ensemble = json.loads(files["ensemble.json"])

    def against_printed(name: str, count: int, n: int, printed: float) -> None:
        if abs(count / n - printed) < 1e-9:
            ok(f"printed agreement — {name}: {count}/{n} = {printed}")
        else:
            fail(f"printed agreement — {name}: recomputed {count}/{n} = "
                 f"{count / n}, release prints {printed}")

    for guard in GUARDS:
        for modality in ("text", "image"):
            against_printed(
                f"{guard} detection_recall_{modality}",
                computed[f"harmful_{modality}"]["per_guard"][guard],
                computed[f"harmful_{modality}"]["n"],
                metrics[guard][f"detection_recall_{modality}"])
        against_printed(
            f"{guard} over_refusal",
            computed["benign_text"]["per_guard"][guard]
            + computed["benign_image"]["per_guard"][guard],
            computed["benign_text"]["n"] + computed["benign_image"]["n"],
            metrics[guard]["over_refusal"])

    def pair_union(stratum: str, members: tuple) -> int:
        abbrevs = {ABBREV[g] for g in members}
        return sum(count for key, count in computed[stratum]["patterns"].items()
                   if key != "none" and abbrevs & set(key.split("+")))

    for label, members in (("lg4_lg3v", ("llama_guard_4", "llama_guard_3_vision")),
                           ("lg4_sg2_modality_routed",
                            ("llama_guard_4", "shield_gemma_2"))):
        for modality in ("text", "image"):
            against_printed(
                f"{label} detection_recall_{modality}",
                pair_union(f"harmful_{modality}", members),
                computed[f"harmful_{modality}"]["n"],
                ensemble[label][f"detection_recall_{modality}"])
        against_printed(
            f"{label} over_refusal",
            pair_union("benign_text", members) + pair_union("benign_image", members),
            computed["benign_text"]["n"] + computed["benign_image"]["n"],
            ensemble[label]["over_refusal"])

    # The paper's one pairwise residual: SG2 rescues 30 of the 36 harmful
    # image items LG4 misses, and loses none.
    img = computed["harmful_image"]["patterns"]
    lg4_misses = sum(count for key, count in img.items()
                     if key == "none" or "lg4" not in key.split("+"))
    rescued = sum(count for key, count in img.items()
                  if "lg4" not in key.split("+") and key != "none"
                  and "sg2" in key.split("+"))
    if (lg4_misses, rescued) == (36, 30):
        ok("printed agreement — SG2 rescues 30 of the 36 harmful image items "
           "LG4 misses (the paper's pairwise residual)")
    else:
        fail(f"printed agreement — LG4 image misses {lg4_misses} (paper: 36), "
             f"SG2 rescues {rescued} (paper: 30)")

    # ------------------------------------------------------------- summary
    print("\nderived from the hash-verified release files; every overlapping")
    print("quantity above is asserted equal to the release's own printing")
    print("(benign burden first — it is the least favorable column):")
    for stratum in ("benign_text", "benign_image", "harmful_text", "harmful_image"):
        kind, modality = stratum.split("_")
        s = computed[stratum]
        print(summary_line(kind, modality, s["union"], s["n"], s["all_miss"]))

    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        return 1
    print(SUCCESS_LINE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
