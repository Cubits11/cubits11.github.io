#!/bin/sh
# The unattended distribution cycle: due snapshots + reply harvest, then the
# full manifest, then a commit and push — or nothing, if any gate is red.
# Credentials are sourced from a mode-600 file outside the repository and are
# never echoed. Scheduled by cron every four hours; log in _private/cron/.
set -eu
REPO="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${CUBITS11_X_ENV:-$HOME/.config/cubits11/x.env}"
LOG_DIR="$REPO/_private/cron"; mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/cycle-$(date -u +%Y%m%dT%H%M%SZ).log"
exec >"$LOG" 2>&1
cd "$REPO"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
[ -r "$ENV_FILE" ] || { echo "no credentials file at $ENV_FILE"; exit 1; }
set -a; . "$ENV_FILE"; set +a
[ -z "$(git status --porcelain)" ] || { echo "tree not clean; refusing to run unattended"; exit 1; }
git pull -q --ff-only origin main
python3 scripts/distribute.py cycle
python3 scripts/verification_manifest.py >/dev/null || { echo "manifest red; leaving the working tree for the owner"; exit 1; }
if [ -n "$(git status --porcelain)" ]; then
  git add distribution docs
  git commit -qm "distribution: unattended cycle $(date -u +%Y-%m-%dT%H:%MZ)"
  git push -q origin main
  echo "pushed $(git rev-parse --short HEAD)"
else
  echo "nothing new"
fi
