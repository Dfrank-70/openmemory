#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
export OPEN_MEMORY_HOME="$ROOT_DIR"
export PAGER=cat
VENV_DIR="$ROOT_DIR/.venv"

mkdir -p "$ROOT_DIR/kb/work/projects" \
  "$ROOT_DIR/kb/work/notes" \
  "$ROOT_DIR/kb/work/emails" \
  "$ROOT_DIR/kb/personal/notes" \
  "$ROOT_DIR/kb/personal/projects" \
  "$ROOT_DIR/kb/personal/finance" \
  "$ROOT_DIR/kb/shared/digests" \
  "$ROOT_DIR/kb/attachments" \
  "$ROOT_DIR/logs"

if [ ! -d "$ROOT_DIR/.git" ]; then
  git -C "$ROOT_DIR" init
fi

if [ ! -f "$ROOT_DIR/.env" ]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
fi

if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r "$ROOT_DIR/requirements.txt"

docker compose -f "$ROOT_DIR/docker-compose.yml" up -d

"$VENV_DIR/bin/python" - <<'PY'
from faster_whisper import WhisperModel
from sentence_transformers import SentenceTransformer
from src.config.settings import get_settings

settings = get_settings()
SentenceTransformer(settings.embedding_model)
WhisperModel(settings.whisper_model)
PY

ALIAS_LINE="alias nota='OPEN_MEMORY_HOME=$ROOT_DIR PYTHONPATH=$ROOT_DIR $VENV_DIR/bin/python -m src.ingestors.note_ingestor'"
if ! grep -Fq "$ALIAS_LINE" "$HOME/.zshrc" 2>/dev/null; then
  echo "$ALIAS_LINE" >> "$HOME/.zshrc"
fi

TMP_CRON="$(mktemp)"
crontab -l 2>/dev/null > "$TMP_CRON" || true
grep -Fq "$ROOT_DIR/scripts/backup_cron.sh" "$TMP_CRON" || echo "*/15 * * * * OPEN_MEMORY_HOME=$ROOT_DIR bash $ROOT_DIR/scripts/backup_cron.sh" >> "$TMP_CRON"
grep -Fq "$VENV_DIR/bin/python -m src.processing.digest_generator" "$TMP_CRON" || echo "0 23 * * * OPEN_MEMORY_HOME=$ROOT_DIR PYTHONPATH=$ROOT_DIR $VENV_DIR/bin/python -m src.processing.digest_generator" >> "$TMP_CRON"
crontab "$TMP_CRON"
rm "$TMP_CRON"

echo "Setup completed"
