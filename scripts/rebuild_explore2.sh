#!/bin/sh
# Export pinbase Markdown to JSON, then rebuild data/explore2/explore2.duckdb.
# Usage: scripts/rebuild_explore2.sh [timeout_seconds]
# Default timeout: 60 seconds

set -e

TIMEOUT="${1:-20}"
DB="data/explore2/explore2.duckdb"
DIR="data/explore2"

pkill -9 -f duckdb 2>/dev/null || true
rm -f "$DB" "$DB.wal"

echo "Exporting pinbase Markdown to JSON..."
EXPORT_START=$(date +%s)
python scripts/export_pinbase_json.py
EXPORT_ELAPSED=$(( $(date +%s) - EXPORT_START ))
echo "  export ${EXPORT_ELAPSED}s"

echo "Rebuilding $DB (timeout: ${TIMEOUT}s)..."
TOTAL_START=$(date +%s)

for sql in "$DIR"/[0-9]*.sql; do
  LAYER=$(basename "$sql")
  LAYER_START=$(date +%s)
  if ! perl -e "alarm($TIMEOUT); exec @ARGV" duckdb "$DB" < "$sql"; then
    ELAPSED=$(( $(date +%s) - LAYER_START ))
    echo "  FAILED $LAYER after ${ELAPSED}s" >&2
    exit 1
  fi
  ELAPSED=$(( $(date +%s) - LAYER_START ))
  echo "  $LAYER ${ELAPSED}s"
done

TOTAL=$(( $(date +%s) - TOTAL_START ))
echo "OK in ${EXPORT_ELAPSED}s export + ${TOTAL}s build"
