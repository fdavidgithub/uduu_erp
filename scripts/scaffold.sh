#!/usr/bin/env bash
# Usage: ./scripts/scaffold.sh <module_name>
# Creates a new Odoo module skeleton inside addons/
set -euo pipefail

MODULE="${1:?Usage: $0 <module_name>}"
TARGET="addons/${MODULE}"

if [ -d "$TARGET" ]; then
  echo "Module '${MODULE}' already exists at ${TARGET}" >&2
  exit 1
fi

docker compose exec odoo odoo scaffold "/mnt/extra-addons/${MODULE}"
echo "Module scaffolded at ${TARGET}"
