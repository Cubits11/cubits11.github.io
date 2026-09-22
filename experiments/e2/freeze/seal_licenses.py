#!/usr/bin/env python3
"""Seal the three OWNER-PENDING license hashes in E2's freeze.

The three E2 guards are gated. Their LICENSE bytes could not be hashed
unauthenticated on 2026-09-01, so `sources.json` carries the string
OWNER-PENDING in place of three sha256 digests and `FREEZE.md` says they are
hashed on the owner's authenticated pull, before any collection.

This is that pull. It does not load a guard, run a guard, or collect anything.
It fetches the LICENSE file each gated repository serves at its pinned
revision, hashes the bytes, writes the digests into sources.json, recomputes
config_hash under the scheme sources.json declares, and re-runs check_freeze.py.

    export HF_TOKEN=hf_...          # a read token on an account that has
                                    # accepted all three licenses
    python3 experiments/e2/freeze/seal_licenses.py --check   # what it would do
    python3 experiments/e2/freeze/seal_licenses.py           # do it

It refuses rather than guesses. No digest is written unless the bytes were
actually retrieved at the pinned revision, because a hash invented to clear a
marker is worse than the marker.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCES = HERE / "sources.json"
CHECK_FREEZE = HERE / "check_freeze.py"
PENDING_PREFIX = "OWNER-PENDING"

# Gated repositories do not agree on where the license text lives. Each
# candidate is tried in order; the first that returns 200 at the PINNED
# revision is used, and the filename is recorded beside the digest so a reader
# knows which bytes were hashed.
CANDIDATES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "README.md")

UA = "cubits11-e2-freeze-seal/1 (+https://cubits11.github.io)"


def token() -> str:
    for var in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACE_TOKEN"):
        v = os.environ.get(var, "").strip()
        if v:
            return v
    sys.exit(
        "no token: set HF_TOKEN to a read token on an account that has accepted\n"
        "  https://huggingface.co/meta-llama/Llama-Guard-4-12B\n"
        "  https://huggingface.co/meta-llama/Llama-Guard-3-8B\n"
        "  https://huggingface.co/google/shieldgemma-2b\n"
        "Accepting the licenses is the owner's hand; this script only hashes them."
    )


def fetch(hf_id: str, revision: str, name: str, tok: str) -> bytes | None:
    """LICENSE bytes at the pinned revision, or None if this name is absent."""
    url = f"https://huggingface.co/{hf_id}/resolve/{revision}/{name}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}", "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise SystemExit(
                f"{hf_id}: HTTP {e.code}. The token is valid but this account has not\n"
                f"accepted this repository's license, or the token lacks read scope.\n"
                f"Accept at https://huggingface.co/{hf_id} then re-run."
            )
        if e.code == 404:
            return None
        raise
    except urllib.error.URLError as e:
        raise SystemExit(f"{hf_id}: network error reaching Hugging Face: {e.reason}")


def canonical(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def config_hash(sources: dict) -> str:
    probe = dict(sources, config_hash="")
    return hashlib.sha256(canonical(probe)).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="report, write nothing")
    a = ap.parse_args()

    sources = json.loads(SOURCES.read_text(encoding="utf-8"))
    pending = [g for g in sources["guards"]
               if str(g.get("license_bytes_sha256", "")).startswith(PENDING_PREFIX)]

    if not pending:
        print("nothing pending: all three guard licenses are already sealed.")
        return 0

    print(f"{len(pending)} guard license(s) pending:")
    for g in pending:
        print(f"  {g['hf_id']} @ {g['revision'][:8]}  ({g['license_tag']})")
    print()

    tok = token()
    sealed = []
    for g in pending:
        got = None
        for name in CANDIDATES:
            b = fetch(g["hf_id"], g["revision"], name, tok)
            if b is not None:
                got = (name, b)
                break
        if got is None:
            raise SystemExit(
                f"{g['hf_id']}: no license file found at revision {g['revision']} "
                f"among {', '.join(CANDIDATES)}. Add the correct filename to "
                f"CANDIDATES rather than hashing a substitute."
            )
        name, blob = got
        digest = hashlib.sha256(blob).hexdigest()
        print(f"  {g['hf_id']}\n    {name}  {len(blob)} bytes  sha256 {digest}")
        sealed.append((g, name, digest))

    if a.check:
        print("\n--check: nothing written.")
        return 0

    for g, name, digest in sealed:
        g["license_bytes_sha256"] = digest
        g["license_bytes_path"] = name
        g["license_hashed_on"] = __import__("datetime").date.today().isoformat()

    old = sources["config_hash"]
    sources["config_hash"] = config_hash(sources)
    SOURCES.write_text(json.dumps(sources, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"\nsources.json written.\n  config_hash {old[:12]} -> {sources['config_hash'][:12]}")
    print("  the freeze's config_hash MUST change: three declared-pending fields")
    print("  became known. That is the freeze completing, not the freeze moving.")
    print("\nre-verifying the freeze from committed artifacts:\n")
    return subprocess.call([sys.executable, str(CHECK_FREEZE)])


if __name__ == "__main__":
    sys.exit(main())
