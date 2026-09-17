#!/bin/sh
# The unattended distribution cycle: due snapshots + reply harvest, then the
# full manifest, then a protected-branch pull request if every gate passes.
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
PYTHON="${CUBITS11_PYTHON:-$REPO/.venv/bin/python3}"
[ -x "$PYTHON" ] || PYTHON=python3
LOCK="$LOG_DIR/repository-cycle.lock"
mkdir "$LOCK" 2>/dev/null || { echo "repository cycle already running"; exit 1; }
trap 'rmdir "$LOCK"' EXIT
trap 'exit 1' HUP INT TERM
[ "$(git branch --show-current)" = main ] || { echo "not on main; refusing unattended publication"; exit 1; }
[ -z "$(git status --porcelain)" ] || { echo "tree not clean; refusing to run unattended"; exit 1; }
git pull -q --ff-only origin main
[ -r "$ENV_FILE" ] || { echo "no credentials file at $ENV_FILE"; exit 1; }
set -a; . "$ENV_FILE"; set +a
"$PYTHON" scripts/distribute.py cycle
"$PYTHON" scripts/distribute.py run
"$PYTHON" scripts/repo_graph.py --no-drift
"$PYTHON" scripts/verification_manifest.py >/dev/null || { echo "manifest red; leaving the working tree for the owner"; exit 1; }
# The unattended cycle owns only its observations and generated previews.
# Never sweep unrelated source changes into a publication commit.
if [ "$(git branch --show-current)" != main ] || [ -n "$(git status --porcelain -- . ':!distribution/traction' ':!docs/graph/repo-graph.json' ':!docs/graph/repo-graph.mmd')" ]; then
  echo "tree changed during verification; retaining observations locally"
  exit 1
fi
if [ -n "$(git status --porcelain)" ]; then
  BRANCH="claude/cycle-distribution-$(date -u +%Y%m%dT%H%M%SZ)"
  git checkout -qb "$BRANCH"
  git add -- distribution/traction docs/graph/repo-graph.json docs/graph/repo-graph.mmd
  git commit -qm "distribution: unattended cycle $(date -u +%Y-%m-%dT%H:%MZ)"
  "$PYTHON" scripts/queue_repository_update.py "$BRANCH"
else
  echo "nothing new"
fi
