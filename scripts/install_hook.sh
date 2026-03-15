#!/bin/bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "usage: $0 /path/to/repo"
  exit 1
fi

OPEN_MEMORY_HOME="${OPEN_MEMORY_HOME:-$HOME/open-memory}"
TARGET_REPO="$1"
HOOK_TARGET="$TARGET_REPO/.git/hooks/post-commit"

cat > "$HOOK_TARGET" <<EOF
#!/bin/bash
set -euo pipefail
export OPEN_MEMORY_HOME="$OPEN_MEMORY_HOME"
export PYTHONPATH="$OPEN_MEMORY_HOME"
python3 -m src.ingestors.git_hook
EOF
chmod +x "$HOOK_TARGET"
echo "$HOOK_TARGET"
