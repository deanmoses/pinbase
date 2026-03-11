#!/usr/bin/env bash
# Validate data/*.json files against their JSON schemas.
# Called by the check-data-schemas pre-commit hook.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="$REPO_ROOT/data"
SCHEMA_DIR="$DATA_DIR/schemas"

status=0
for json_file in "$DATA_DIR"/*.json; do
    name="$(basename "$json_file" .json)"
    schema="$SCHEMA_DIR/${name}.schema.json"
    if [ ! -f "$schema" ]; then
        echo "WARNING: no schema for $json_file" >&2
        continue
    fi
    if ! uvx check-jsonschema --schemafile "$schema" "$json_file"; then
        status=1
    fi
done

exit $status
