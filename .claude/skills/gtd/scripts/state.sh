#!/bin/bash
# Compatibility entry point; tracking rules and persistence live in Python.
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/gtd_tracking.py" "$@"
