import csv, sys
FIELDS = ["item_id", "system_id", "decision", "split", "threshold", "exposure"]
META = ["event", "every_system_saw_every_item", "thresholds", "exposure"]
def unknown(reason): print(f"UNKNOWN: {reason}"); raise SystemExit(1)
if len(sys.argv) != 2: unknown("input CSV")
try:
    lines = open(sys.argv[1], encoding="utf-8", newline="").read().splitlines()
except OSError: unknown("unreadable input CSV")
meta = {}
for line in lines:
    if line.startswith("#") and ":" in line:
        k, v = line[1:].split(":", 1); meta[k.strip()] = v.strip()
try:
    reader = csv.DictReader(line for line in lines if not line.startswith("#")); rows = list(reader)
except (csv.Error, UnicodeError): unknown("invalid CSV")
if reader.fieldnames != FIELDS: unknown("CSV header")
if any(not meta.get(k) for k in META): unknown("missing header field")
if meta["every_system_saw_every_item"].lower() != "yes": unknown("full exposure not declared")
if meta["exposure"].lower() != "static_full": unknown("routed or unknown exposure")
if not rows or any(not all((r.get(f) or "").strip() for f in FIELDS) for r in rows): unknown("missing CSV field")
if any(None in r for r in rows): unknown("extra CSV field")
if any(r["decision"] not in {"0", "1"} for r in rows): unknown("nonbinary decision")
if any(r["exposure"] != "static_full" for r in rows): unknown("nonstatic row exposure")
items, systems = {r["item_id"] for r in rows}, {r["system_id"] for r in rows}
if len({r["split"] for r in rows}) != 1: unknown("multiple splits")
if any(len({r["threshold"] for r in rows if r["system_id"] == s}) != 1 for s in systems): unknown("threshold varies within a system")
D = {(r["item_id"], r["system_id"]): int(r["decision"]) for r in rows}
if len(D) != len(rows) or len(D) != len(items) * len(systems): unknown("incomplete or duplicate item×system matrix")
n = len(items); union = sum(max(D[i,s] for s in systems) for i in items); all_miss = sum(min(1-D[i,s] for s in systems) for i in items)
print(f"n={n}\nunion={union}/{n} = {union/n:.12g}\nall_miss={all_miss}/{n} = {all_miss/n:.12g}")
