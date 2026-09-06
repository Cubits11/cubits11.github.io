#!/usr/bin/env python3
"""E3 scoring. Refuses to score harmful items until e3_config.json is committed.

Guards emit a probability for the "unsafe/injection" class. A flag is
prob >= threshold. Thresholds come from e3_config.json and never from here.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FREEZE = ROOT / "experiments/e3/freeze"
CONFIG = ROOT / "experiments/e3/e3_config.json"
GUARDS = {
    "G1": ("protectai/deberta-v3-base-prompt-injection-v2", "90c9989b1a342275dd0d1a95aad283c04e075671"),
    "G2": ("dcarpintero/pangolin-guard-base", "eb220d9f8d75cfbc82cc9d430fa19f85d9764cef"),
}


def committed(path: Path) -> bool:
    """True only if the file is committed — not merely present on disk."""
    r = subprocess.run(["git", "cat-file", "-e", f"HEAD:{path.relative_to(ROOT)}"],
                       cwd=ROOT, capture_output=True)
    return r.returncode == 0


def texts(name: str) -> list[tuple[str, str]]:
    pool = "or-bench-toxic.csv" if name == "items_harmful" else "or-bench-80k.csv"
    rows = list(csv.DictReader((FREEZE / pool).open(encoding="utf-8")))
    ids = list(csv.DictReader((FREEZE / f"{name}.csv").open()))
    out = []
    for r in ids:
        t = rows[int(r["row_index"])]["prompt"]
        assert hashlib.sha256(t.encode()).hexdigest() == r["text_sha256"], f"text drift at {r['id']}"
        out.append((r["id"], t))
    return out


def probs(hf_id: str, rev: str, items: list[tuple[str, str]]) -> list[float]:
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    tok = AutoTokenizer.from_pretrained(hf_id, revision=rev)
    mdl = AutoModelForSequenceClassification.from_pretrained(hf_id, revision=rev).eval()
    lab = {v.upper(): k for k, v in mdl.config.id2label.items()}
    pos = lab.get("INJECTION", lab.get("UNSAFE", lab.get("LABEL_1", 1)))
    out = []
    with torch.no_grad():
        for i in range(0, len(items), 16):
            b = [t for _, t in items[i:i + 16]]
            enc = tok(b, return_tensors="pt", truncation=True, max_length=512, padding=True)
            out += torch.softmax(mdl(**enc).logits, -1)[:, pos].tolist()
            print(f"    {min(i+16,len(items))}/{len(items)}", end="\r", file=sys.stderr)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True,
                    choices=["items_benign_calibration", "items_benign_evaluation", "items_harmful"])
    a = ap.parse_args()

    if a.set == "items_harmful" and not committed(CONFIG):
        print("REFUSED: e3_config.json is not committed. Calibrate and commit the "
              "thresholds before any harmful item is scored. This has no recovery.",
              file=sys.stderr)
        return 2

    items = texts(a.set)
    out = FREEZE.parent / "results" / f"{a.set}.probs.json"
    out.parent.mkdir(exist_ok=True)
    rec = {"set": a.set, "n": len(items), "guards": {}}
    for slot, (hf_id, rev) in GUARDS.items():
        print(f"  {slot} {hf_id}", file=sys.stderr)
        rec["guards"][slot] = dict(zip([i for i, _ in items], probs(hf_id, rev, items)))
    out.write_text(json.dumps(rec))
    print(f"wrote {out.relative_to(ROOT)}  n={len(items)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
