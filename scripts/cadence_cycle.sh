#!/bin/sh
# The daily cadence: record one row of repository state, then the full manifest,
# then a commit and push — or nothing, if any gate is red. No credentials and no
# network writes beyond the push. Scheduled by cron once a day; log in
# _private/cron/.
set -eu
REPO="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$REPO/_private/cron"; mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/cadence-$(date -u +%Y%m%dT%H%M%SZ).log"
exec >"$LOG" 2>&1
cd "$REPO"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
[ -z "$(git status --porcelain)" ] || { echo "tree not clean; refusing to run unattended"; exit 1; }
git pull -q --ff-only origin main
python3 scripts/cadence.py record
python3 scripts/verification_manifest.py >/dev/null || { echo "manifest red; leaving the working tree for the owner"; exit 1; }
if [ -n "$(git status --porcelain)" ]; then
  git add metrics
  git commit -qm "cadence: $(date -u +%Y-%m-%d) repository state"
  git push -q origin main
  echo "pushed $(git rev-parse --short HEAD)"
else
  echo "nothing new"
fi
python3 scripts/cadence.py report
