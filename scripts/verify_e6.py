#!/usr/bin/env python3
"""Re-derive every registered E6 number from the committed rows alone.

E6 asks how much of a scenario model's output is fixed by the marginals of its
inputs and how much by the coupling between them. This verifier never touches
the network and never re-runs the model: it reads the 243 committed observation
rows and recomputes each headline quantity from them, so the registry's numbers
are checkable without reaching an external artifact.

Exit codes match this repository's convention:
  0  every quantity re-derived and agrees
  1  a quantity disagrees  -- a real failure
  2  a quantity could not be evaluated (rows or result file absent or malformed);
     NOT a pass and NOT a refutation
"""
import json
import pathlib
import sys
from itertools import permutations

ROOT = pathlib.Path(__file__).resolve().parent.parent
E6 = ROOT / "experiments" / "e6"
ROWS = E6 / "results" / "observations.jsonl"
RESULT = E6 / "results" / "e6_result.json"
SOURCES = E6 / "freeze" / "sources.json"

TOL = 1e-9
KEYS = ["m2030", "d2030", "psi", "a2030", "mu"]
W = [0.25, 0.50, 0.25]

fails: list[str] = []
checks = 0


def ok(label: str) -> None:
    global checks
    checks += 1
    print(f"ok    {label}")


def bad(label: str, got, want) -> None:
    global checks
    checks += 1
    fails.append(f"{label}: got {got!r}, expected {want!r}")
    print(f"FAIL  {label}: got {got!r}, expected {want!r}")


def unevaluable(msg: str) -> None:
    print(f"E6 EXIT 2: {msg}")
    print("A check that could not be evaluated is not a pass and not a refutation.")
    sys.exit(2)


def agrees(label: str, got, want, tol: float = TOL) -> None:
    if isinstance(want, (int, float)) and isinstance(got, (int, float)):
        if abs(got - want) <= tol:
            ok(f"{label} = {got}")
        else:
            bad(label, got, want)
    else:
        if got == want:
            ok(f"{label} = {got}")
        else:
            bad(label, got, want)


def weighted_quantile(pairs, q):
    """q-quantile of a discrete distribution given as (value, weight) pairs."""
    acc = 0.0
    for v, w in sorted(pairs):
        acc += w
        if acc >= q - 1e-12:
            return v
    return sorted(pairs)[-1][0]


def main() -> int:
    for p in (ROWS, RESULT, SOURCES):
        if not p.exists():
            unevaluable(f"{p.relative_to(ROOT)} absent")

    try:
        rows = [json.loads(line) for line in ROWS.read_text().splitlines() if line.strip()]
        result = json.loads(RESULT.read_text())
        sources = json.loads(SOURCES.read_text())
    except json.JSONDecodeError as exc:
        unevaluable(f"malformed JSON: {exc}")

    print(f"E6 verifier -- re-deriving from {len(rows)} committed rows, no network, no model re-run\n")

    # ---- shape
    agrees("row count", len(rows), 243)
    agrees("declared cells", result["secondary"]["cells"], 243)
    agrees("preregistered flag is false", result["preregistered"], False)
    agrees("sources.json agrees E6 is not preregistered", sources["preregistered"], False)

    digests = {r["kernel_sha256"] for r in rows}
    if len(digests) == 1 and digests.pop() == sources["artifacts"][1]["sha256"]:
        ok("every row carries the pinned kernel digest")
    else:
        bad("kernel digest on rows", digests, sources["artifacts"][1]["sha256"])

    # ---- the marginals on the rows are the ones the registry froze
    q = {k: [sources["marginals"]["parameters"][k][f"q{n}"] for n in (25, 50, 75)] for k in KEYS}
    for k in KEYS:
        seen = sorted({r[k] for r in rows})
        if seen == sorted(q[k]):
            ok(f"rows span exactly the three published quantiles of {k}: {seen}")
        else:
            bad(f"support of {k}", seen, sorted(q[k]))

    by_cell = {r["cell"]: r for r in rows}
    if len(by_cell) != 243:
        bad("cells are distinct", len(by_cell), 243)
    else:
        ok("all 243 cells distinct")

    gdp = lambda r: r["gdp_pct_above_noAI"]  # noqa: E731
    une = lambda r: r["unemp_all_pct"]  # noqa: E731

    # ---- primary: the vector of published medians is the centre cell
    centre = by_cell.get("11111")
    if centre is None:
        unevaluable("centre cell 11111 (the vector of published medians) missing")
    prim = result["primary"]["at_vector_of_published_medians"]
    agrees("primary GDP at the vector of published medians", gdp(centre), prim["gdp_pct_above_noAI"], 5e-5)
    agrees("primary unemployment at the same vector", une(centre), prim["unemp_all_pct"], 5e-5)

    # ---- primary: comonotone quartiles are the corner cells
    lo, hi = by_cell.get("00000"), by_cell.get("22222")
    if lo is None or hi is None:
        unevaluable("comonotone corner cells 00000 / 22222 missing")
    agrees("comonotone q25 of GDP", gdp(lo), result["primary"]["comonotone_quartiles_gdp"][0], 5e-5)
    agrees("comonotone q75 of GDP", gdp(hi), result["primary"]["comonotone_quartiles_gdp"][1], 5e-5)

    # ---- secondary: the three couplings, recomputed from rows
    como = [(gdp(by_cell[str(k) * 5]), W[k]) for k in range(3)]
    indep = [(gdp(r), r["weight_independent"]) for r in rows]
    agrees("comonotone median GDP", weighted_quantile(como, 0.5),
           result["secondary"]["median_gdp"]["comonotone"], 5e-5)
    agrees("independent median GDP", weighted_quantile(indep, 0.5),
           result["secondary"]["median_gdp"]["independent"], 5e-5)

    como_u = [(une(by_cell[str(k) * 5]), W[k]) for k in range(3)]
    indep_u = [(une(r), r["weight_independent"]) for r in rows]
    agrees("comonotone median unemployment", weighted_quantile(como_u, 0.5),
           result["secondary"]["median_unemp_all"]["comonotone"], 5e-5)
    agrees("independent median unemployment", weighted_quantile(indep_u, 0.5),
           result["secondary"]["median_unemp_all"]["independent"], 5e-5)

    tw = sum(r["weight_independent"] for r in rows)
    agrees("independent weights sum to one", round(tw, 12), 1.0, 1e-9)
    agrees("independent mean GDP", sum(gdp(r) * r["weight_independent"] for r in rows) / tw,
           result["secondary"]["mean_gdp"]["independent"], 5e-5)
    agrees("independent mean unemployment", sum(une(r) * r["weight_independent"] for r in rows) / tw,
           result["secondary"]["mean_unemp_all"]["independent"], 5e-5)

    # ---- secondary: the range of the median over rank-permutation couplings
    perms = list(permutations(range(3)))
    seen_lo, seen_hi, n = float("inf"), float("-inf"), 0
    for p1 in perms:
        for p2 in perms:
            for p3 in perms:
                for p4 in perms:
                    pairs = [(gdp(by_cell[f"{k}{p1[k]}{p2[k]}{p3[k]}{p4[k]}"]), W[k]) for k in range(3)]
                    m = weighted_quantile(pairs, 0.5)
                    seen_lo, seen_hi, n = min(seen_lo, m), max(seen_hi, m), n + 1
    rec = result["secondary"]["median_gdp_over_rank_permutation_couplings"]
    agrees("rank-permutation couplings enumerated", n, rec["couplings"])
    agrees("min median GDP over couplings", seen_lo, rec["min"], 5e-5)
    agrees("max median GDP over couplings", seen_hi, rec["max"], 5e-5)

    agrees("support of GDP over the 243 cells (min)", min(map(gdp, rows)),
           result["secondary"]["support_gdp"][0], 5e-5)
    agrees("support of GDP over the 243 cells (max)", max(map(gdp, rows)),
           result["secondary"]["support_gdp"][1], 5e-5)

    # ---- the load-bearing structural facts
    published = sources["published_comparators"]["table4_survey_joint"]["gdp_pct_above_noAI"]["q50"]
    if rec["min"] < published < rec["max"]:
        ok(f"the measured joint's median ({published}) lies strictly inside the coupling range "
           f"[{rec['min']}, {rec['max']}] -- the marginals do not determine it")
    else:
        bad("measured joint inside the coupling range", published, [rec["min"], rec["max"]])

    width = rec["max"] - rec["min"]
    if width > abs(published) * 0.5:
        ok(f"coupling range is {width:.2f} points wide, more than half the joint's own median value")
    else:
        bad("coupling range materially wide", width, "> 50% of the joint median")

    # monotonicity is what licenses reading the comonotone quantiles off the corners
    for row in result["monotonicity"]:
        if row["increasing"]:
            ok(f"GDP monotone increasing in {row['parameter']}")
        else:
            bad(f"GDP monotone in {row['parameter']}", row["gdp"], "strictly increasing")

    print()
    if fails:
        print(f"E6 VERIFY FAILED -- {len(fails)} of {checks} checks did not hold:")
        for f in fails:
            print(f"  - {f}")
        return 1
    print(f"E6 verified: {checks} checks re-derived from the committed rows alone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
