#!/usr/bin/env python3
"""Write freeze.json: the digests every later E9 step checks. Runs once, before any score.

    python3 experiments/e9/run/freeze.py           # write freeze.json
    python3 experiments/e9/run/freeze.py --check   # exit 1 if a frozen input has moved

freeze.json records the contract's sha256, the digest of protocol.json above
"results", the sha256 of every drawn item list, and the seed and bootstrap
size the analysis will use, copied from the protocol rather than typed here.
score.py and admit.py refuse inputs that no longer match it. The commit that
adds it, published on origin/main, is the evidence that the freeze preceded
the first score; a file on disk is not.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
E9 = ROOT / "experiments/e9"
FREEZE = E9 / "freeze"

_spec = importlib.util.spec_from_file_location("score", E9 / "run" / "score.py")
score = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(score)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict:
    protocol = json.loads((FREEZE / "protocol.json").read_text())
    return {
        "frozen_on": protocol["written"],
        "seed": protocol["seed"],
        "bootstrap": protocol["bootstrap"],
        "contract_sha256": digest(E9 / "contract.json"),
        "protocol_declared_sha256": score.declared_digest(protocol),
        "items": {p.name: digest(p) for p in sorted(FREEZE.glob("items_*.csv"))},
        "order_witness": ("score.py refuses every E9 set until this file, the frozen contract and that set's "
                          "item list are committed and this file is on origin/main byte for byte. The time "
                          "GitHub received it is an out-of-repository witness that the freeze preceded the "
                          "first score."),
    }


def check() -> list[str]:
    """Frozen inputs that no longer match freeze.json. Results appended below them are not inputs."""
    path = FREEZE / "freeze.json"
    if not path.exists():
        return []
    recorded, now = json.loads(path.read_text()), build()
    return [f"{key} moved since the freeze" for key in ("contract_sha256", "protocol_declared_sha256", "items", "seed",
                                                       "bootstrap") if recorded[key] != now[key]]


def main() -> int:
    if "--check" in sys.argv:
        errors = check()
        for e in errors:
            print("DRIFT:", e)
        if not errors:
            print("ok    E9's frozen inputs match freeze.json")
        return bool(errors)
    if (FREEZE / "freeze.json").exists():
        print("REFUSED: freeze.json exists; a second freeze is a second declaration")
        return 1
    (FREEZE / "freeze.json").write_text(json.dumps(build(), indent=1) + "\n")
    print("wrote experiments/e9/freeze/freeze.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
