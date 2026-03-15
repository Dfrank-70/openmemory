#!/bin/bash
set -euo pipefail

OPEN_MEMORY_HOME="${OPEN_MEMORY_HOME:-$HOME/open-memory}"
export PAGER=cat

git -C "$OPEN_MEMORY_HOME" add -A
git -C "$OPEN_MEMORY_HOME" diff --cached --quiet || git -C "$OPEN_MEMORY_HOME" commit -m "auto-sync $(date +%Y-%m-%d_%H:%M)"
git -C "$OPEN_MEMORY_HOME" push origin main 2>/dev/null || true
