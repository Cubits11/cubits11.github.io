#!/usr/bin/env python3
"""Mechanical clerk-check for the authorized-box evidence.

Run ON THE BOX (or hand it the pasted numbers) before the first real
calibration token. It checks facts, not intentions: memory, disk, the
license record's shape, and the LG4 conversion record's shape. It never
logs in, never downloads, and never reads a token.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NEED_MEM = 24 * 1024 ** 3
failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("ok    " if ok else "FAIL  ") + name + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--memsize", type=int,
                    help="paste of `sysctl -n hw.memsize` (default: measure)")
    args = ap.parse_args()

    mem = args.memsize
    if mem is None:
        try:
            mem = int(subprocess.run(["sysctl", "-n", "hw.memsize"],
                                     capture_output=True, text=True).stdout)
        except Exception:  # noqa: BLE001
            mem = 0
    check(f"unified memory >= 24 GiB", mem >= NEED_MEM,
          f"{mem / 1024**3:.1f} GiB" + ("" if mem >= NEED_MEM else
          " — this is NOT the authorized box; stop"))

    lic = HERE / "LICENSES.md"
    if not lic.exists():
        check("LICENSES.md exists (owner-written, append-only)", False,
              "create from LICENSES.template.md after the first "
              "authenticated pull")
    else:
        body = lic.read_text()
        hashes = re.findall(r"\b[0-9a-f]{64}\b", body)
        check("LICENSES.md carries >= 3 sha256 hashes", len(hashes) >= 3,
              f"{len(hashes)} found")
        cr = [ln for ln in body.splitlines()
              if ln.strip().lower().startswith("commercial_reuse:")]
        filled = [ln for ln in cr if "<OWNER WRITES" not in ln]
        check("three commercial_reuse lines, owner-written",
              len(filled) >= 3, f"{len(filled)} filled of {len(cr)} present")
        check("no template placeholders remain", "<OWNER WRITES" not in body)

    conv = HERE / "LG4_CONVERSION.md"
    if conv.exists():
        b = conv.read_text()
        check("LG4 conversion record: command + >=1 output hash",
              "mlx" in b.lower() or "convert" in b.lower(),
              "tool/command present" if ("convert" in b.lower()) else "")
        check("LG4 conversion record carries output sha256",
              bool(re.search(r"\b[0-9a-f]{64}\b", b)))
    else:
        print("note  LG4_CONVERSION.md absent — required before LG4 "
              "calibration only; sg2b and lg3 are not blocked by it")

    print()
    print("Checklist (facts this script can see on this machine):")
    for item, state in (
            ("hw.memsize >= 24 GiB", mem >= NEED_MEM),
            ("LICENSES.md complete", lic.exists() and not failures),
            ("LG4 conversion recorded", conv.exists())):
        print(f"  [{'x' if state else ' '}] {item}")
    print("  [ ] HF access at the three pinned SHAs (proved by the "
          "authenticated download itself)")
    print("  [ ] E2_ON_AUTHORIZED_BOX=1 exported (shell state, not "
          "checkable from here)")
    print("  [ ] synthetic shakeout green on this box")
    print("  [ ] first token: calibrate.py --guard sg2b")

    if failures:
        print(f"{len(failures)} check(s) failed. No token.")
        return 1
    print("Box evidence consistent with the runbook so far.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
