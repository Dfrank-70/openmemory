---
name: MCP Persistent Memory
scope: work
status: active
stack: ["Python", "Docker"]
repo: /Users/francescogarofano/Library/CloudStorage/GoogleDrive-effegimaster@gmail.com/Il mio Drive/shared docs F/Progetti Cascade/MCP Persistent Memory
registered: 2026-04-15
last_commit: 2026-04-15
description: "# Open Memory"
content_hash: 23f68e49e3e6c79f68cd146424fe8385ac9592cb0b82aaf12c21d092dd30650c
---

## Stato attuale
Branch attivo: `main`.
Ultimo commit: `fe9bff3` — Add user guide in Italian

## Stack
- Python
- Docker

## Change Log
### fe9bff3
Add user guide in Italian
### 4ff87a4
Add Obsidian integration tests
### 693fa90
Add Obsidian configuration
### 0ae2442
chore: add test notes for auto-classification and reconcile verification
### 0cb565a
watcher reconcile: deleted 1 orphaned documents
### e0b5348
watcher sync: 1 upsert, 0 delete
### 12404e6
feat: add reconcile command for periodic orphaned document cleanup
### 95c1796
feat: auto-classify Obsidian notes without frontmatter
### 415553a
chore: increase polling interval to 10s for efficiency
### 61fe511
fix: use PollingObserver for reliable file detection on macOS
### 5d5c3bf
watcher sync: 1 upsert, 0 delete
### 4d88991
test: add debounce test and conftest mocks for kb_watcher
### 6da1f31
feat: implement kb file watcher
### 768e2ba
bootstrap open memory
### 17ed425
ingest unclassified: Test nota Open Memory: decisione di validazione runtime locale

## Punti di ripristino
- Nessun tag disponibile

## Decisioni architetturali
- Da derivare dai commit futuri

## Struttura repository
```text
chroma-data/
docker-compose.yml
Dockerfile.watcher
GUIDA_UTENTE.md
kb/
  - attachments/
  - index.md
  - personal/
  - shared/
  - work/
logs/
  - chroma.log
  - chroma.log.2026-03-15
  - classifier.log
  - classifier.log.2026-03-15
  - classifier.log.2026-03-16
  - embedder.log
  - git.log
  - git.log.2026-03-15
  - kb_watcher.log
  - kb_watcher.log.2026-03-15
  - kb_watcher.log.2026-03-16
  - mcp_server.log
  - mcp_server.log.2026-03-15
  - openrouter.log
  - openrouter.log.2026-03-15
  - pipeline.log
  - register_project.log
  - watcher.log
projects.yaml
README.md
requirements.txt
scripts/
  - backup_cron.sh
  - install_hook.sh
  - setup.sh
src/
  - __init__.py
  - __pycache__/
  - config/
  - ingestors/
  - mcp_server/
  - processing/
  - storage/
  - watchers/
tests/
  - __init__.py
  - __pycache__/
  - conftest.py
  - test_classifier.py
  - test_embedder.py
  - test_file_readers.py
  - test_kb_watcher.py
  - test_mcp_server.py
```
