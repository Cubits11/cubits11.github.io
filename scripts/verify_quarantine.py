#!/usr/bin/env python3
"""A quarantined asset must not exist in the tree it is quarantined from.

RECEIPT_PROTOCOL.md declares assets quarantined in prose. Prose does not
stop a web server: on 2026-09-01 a card declared "not an approved asset"
was serving HTTP 200 from the live site. This gate makes the quarantine
executable — it parses every `path` named as quarantined in the protocol
and fails the build while any such file exists in the repository.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROTOCOL = ROOT / "distribution" / "RECEIPT_PROTOCOL.md"

failures = 0
text = PROTOCOL.read_text()
quarantined = re.findall(r"`([^`]+)`[^`]{0,80}?\bis quarantined\b", text)
if not quarantined:
    print("FAIL  RECEIPT_PROTOCOL.md names no quarantined path — if the "
          "quarantine was lifted, retire this gate deliberately, not by "
          "rewording")
    sys.exit(1)
for rel in quarantined:
    p = ROOT / rel
    if p.exists():
        print(f"FAIL  quarantined asset exists in the tree (and would be "
              f"served): {rel}")
        failures += 1
    else:
        print(f"ok    quarantined asset absent from the tree: {rel}")
if failures:
    sys.exit(1)
print("Quarantine verified: every asset the protocol quarantines is out "
      "of the tree.")
