#!/usr/bin/env bash
set -euo pipefail

# Preview by default. Use --apply to create links; --replace also backs up conflicts.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SCRIPT_DIR/link_skills.py" "$@"
