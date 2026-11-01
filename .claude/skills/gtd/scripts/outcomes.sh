#!/bin/bash
# Durable processing Session outcomes. Decision and persistence logic live in Python.
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/gtd_outcomes.py" "$@"
