#!/bin/sh
# Rebuild data/explore/explore.duckdb with timing and a hard timeout.
# Usage: scripts/rebuild_explore.sh [timeout_seconds]
# Default timeout: 60 seconds

set -e

TIMEOUT="${1:-60}"
DB="data/explore/explore.duckdb"
SQL="data/explore/explore.sql"

rm -f "$DB"

echo "Rebuilding $DB (timeout: ${TIMEOUT}s)..."
START=$(date +%s)

# Use perl alarm for macOS compatibility (no coreutils `timeout`)
if ! perl -e "alarm($TIMEOUT); exec @ARGV" duckdb "$DB" < "$SQL"; then
  ELAPSED=$(( $(date +%s) - START ))
  echo "FAILED after ${ELAPSED}s" >&2
  exit 1
fi

ELAPSED=$(( $(date +%s) - START ))
echo "OK in ${ELAPSED}s"
