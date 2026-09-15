#!/bin/sh
# Record locally even during work. Queue a checked PR from synchronized main.
# Missing days stay missing; the append-only series is never backfilled.
set -eu
REPO="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$REPO/_private/cron"; mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/cadence-$(date -u +%Y%m%dT%H%M%SZ).log"
exec >"$LOG" 2>&1
cd "$REPO"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
PYTHON="${CUBITS11_PYTHON:-$REPO/.venv/bin/python3}"
[ -x "$PYTHON" ] || PYTHON=python3

LOCK="$LOG_DIR/repository-cycle.lock"
mkdir "$LOCK" 2>/dev/null || { echo "cadence already running; refusing a concurrent append"; exit 1; }
trap 'rmdir "$LOCK"' EXIT
trap 'exit 1' HUP INT TERM

PUBLISH=false
if [ "$(git branch --show-current)" = main ] && [ -z "$(git status --porcelain)" ]; then
  if git pull -q --ff-only origin main; then
    PUBLISH=true
  else
    echo "pull declined; recording locally only"
  fi
fi
"$PYTHON" scripts/cadence.py record

if [ "$PUBLISH" != true ]; then
  echo "working tree or branch unsuitable for unattended publication; row recorded locally"
  "$PYTHON" scripts/cadence.py report
  exit 0
fi
if ! "$PYTHON" scripts/verification_manifest.py >/dev/null; then
  echo "manifest red; row retained locally"
  exit 1
fi
# Recheck after verification so concurrent owner edits cannot enter the commit.
if [ "$(git branch --show-current)" != main ] || [ -n "$(git status --porcelain -- . ':!metrics/repo_state.jsonl')" ]; then
  echo "tree changed during verification; row retained locally"
  exit 1
fi
if [ -n "$(git status --porcelain -- metrics/repo_state.jsonl)" ]; then
  BRANCH="claude/cycle-cadence-$(date -u +%Y%m%dT%H%M%SZ)"
  git checkout -qb "$BRANCH"
  git commit --only -qm "cadence: $(date -u +%Y-%m-%d) repository state" -- metrics/repo_state.jsonl
  "$PYTHON" scripts/queue_repository_update.py "$BRANCH"
else
  echo "nothing new"
fi
"$PYTHON" scripts/cadence.py report
