# Open Memory

Open Memory è un sistema di memoria persistente personale per agenti AI. Il repository git è la fonte di verità, la knowledge base vive in `kb/`, ChromaDB è un indice derivato ricostruibile, e un server MCP espone ricerca e contesto a client esterni.

## Componenti

- `kb/`: knowledge base in Markdown compatibile con Obsidian
- `src/processing/`: classificazione, embedding, lettura file, diff e digest
- `src/ingestors/`: CLI note, bootstrap progetti, git hook, voice, IMAP
- `src/storage/`: accesso a git, ChromaDB e ricostruzione indice
- `src/mcp_server/`: server MCP con tool `search`, `get_project`, `get_context`
- `scripts/`: setup locale, backup periodico, installazione hook

## Quick start

1. Copia `.env.example` in `.env`
2. Crea un virtualenv Python 3.12
3. Installa le dipendenze con `pip install -r requirements.txt`
4. Avvia Chroma e i server MCP con `docker compose up -d`
5. Esegui `bash scripts/setup.sh`
6. Aggiungi l'alias `nota` alla tua shell

## Comandi principali

- `python -m src.ingestors.note_ingestor "testo nota"`
- `python -m src.ingestors.register_project "Progetto Alfa" ~/dev/progetto-alfa --scope work`
- `python -m src.ingestors.bootstrap_projects --config projects.yaml`
- `python -m src.storage.rehydrate`
- `python -m src.processing.digest_generator`
- `python -m src.mcp_server.server`

## MCP

- Profilo work: `http://localhost:8000/mcp`
- Profilo full: `http://localhost:8001/mcp`

## Note operative

- I modelli `intfloat/multilingual-e5-large` e `faster-whisper` vengono scaricati localmente in setup.
- Le chiamate OpenRouter hanno retry singolo e fallback conservativo.
- L'indice Chroma può essere ricreato interamente dai file in `kb/` usando `src/storage/rehydrate.py`.
