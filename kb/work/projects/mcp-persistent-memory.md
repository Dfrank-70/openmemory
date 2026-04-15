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

### 2026-04-15 — 8719927
This appears to be a project update log entry for a project called "MCP Persistent Memory". The commit adds 35 lines to a Markdown file tracking the project's details and change log.

Key observations from the diff:

1. The commit adds a detailed entry for a commit dated 2026-04-15 with hash 797ecb5

2. The new entry provides an overview of the project, including:
- Project name: MCP Persistent Memory
- Status: Active
- Technology stack: Python, Docker
- Repository location: Personal Google Drive

3. The project seems to be a persistent memory management system with features like:
- File watching
- Classification
- Embedder modules
- Docker integration
- Obsidian integration tests

4. The entry describes the project structure, recent commits, and notable components

5. The commit is part of a knowledge base (kb/) tracking system, specifically in the projects subdirectory

The log entry provides a comprehensive snapshot of the project's current state and recent development activities.


### 2026-04-15 — 797ecb5
This commit appears to be registering a new project called "MCP Persistent Memory" in a knowledge base tracking system. Let me break down the key details:

1. Project Details:
- Name: MCP Persistent Memory
- Status: Active
- Stack: Python, Docker
- Registered Date: 2026-04-15
- Repository Location: Personal Google Drive

2. Repository Structure:
- Contains typical Python project structure
- Includes Docker configuration
- Has a knowledge base (kb/) directory
- Contains source code (src/), tests, scripts, and logs

3. Recent Commits:
- Latest commit: "Add user guide in Italian" (fe9bff3)
- Previous commits include:
  - Adding Obsidian integration tests
  - Adding configuration
  - Implementing file watcher
  - Bootstrapping "open memory" project

4. Notable Components:
- Docker compose and Dockerfile
- Logging system
- File watcher
- Classifier and embedder modules
- Test suite
- Setup and installation scripts

The project seems to be a persistent memory management system with file watching, classification, and integration capabilities, likely using Obsidian as a note-taking platform.

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
