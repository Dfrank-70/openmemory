# Guida Utente - Open Memory

Open Memory è un sistema di memoria persistente personale per agenti AI. Questa guida spiega le funzioni attualmente disponibili.

## Funzionalità Principali

### 1. Gestione Note

**Crea una nuova nota da riga di comando:**
```bash
python -m src.ingestors.note_ingestor "testo della tua nota"
```
La nota viene automaticamente classificata e salvata nella knowledge base.

**Usa Obsidian per creare note:**
- Apri la cartella `kb/` con Obsidian
- Crea o modifica file Markdown
- Il watcher automatico rileva le modifiche e le indicizza in ChromaDB
- I file nella cartella `.obsidian/` vengono ignorati automaticamente

### 2. Gestione Progetti

**Registra un nuovo progetto:**
```bash
python -m src.ingestors.register_project "Nome Progetto" ~/percorso/progetto --scope work
```

**Registra più progetti da file di configurazione:**
```bash
python -m src.ingestors.bootstrap_projects --config projects.yaml
```

### 3. Indicizzazione e Ricerca

**Ricostruisci l'indice ChromaDB da zero:**
```bash
python -m src.storage.rehydrate
```
Utile se l'indice è corrotto o vuoto. Tutti i file in `kb/` vengono reindicizzati.

**Genera digest riassuntivi:**
```bash
python -m src.processing.digest_generator
```
Crea riassunti automatici delle note.

### 4. Server MCP

**Avvia il server MCP:**
```bash
python -m src.mcp_server.server
```

**Endpoint disponibili:**
- Profilo work: `http://localhost:8000/mcp`
- Profilo full: `http://localhost:8001/mcp`

**Tool MCP disponibili:**
- `search`: Cerca nella knowledge base
- `get_project`: Ottieni informazioni su un progetto
- `get_context`: Ottieni contesto pertinente

### 5. Watcher Automatico

Il watcher monitora continuamente la cartella `kb/` e:
- Rileva nuove o modificate note
- Le classifica automaticamente se il frontmatter è incompleto
- Le indicizza in ChromaDB
- Committa le modifiche su git

**Avvia il watcher:**
```bash
python -m src.watchers.kb_watcher
```

**Pulizia documenti orfani:**
```bash
python -m src.watchers.kb_watcher --reconcile
```

### 6. Ingestori Avanzati

**Note vocali:**
```bash
python -m src.ingestors.voice_ingestor
```
Trascrive audio in testo e crea note.

**Monitor email (IMAP):**
```bash
python -m src.ingestors.imap_watcher
```
Monitora una casella email e crea note dalle email.

### 7. Script di Utilità

**Setup iniziale:**
```bash
bash scripts/setup.sh
```
Configura l'ambiente, scarica i modelli ML, installa git hook.

**Backup periodico:**
```bash
bash scripts/backup_cron.sh
```
Crea backup della knowledge base.

**Installa git hook:**
```bash
bash scripts/install_hook.sh
```
Configura hook git per processare automaticamente i commit.

## Struttura della Knowledge Base

```
kb/
├── .obsidian/          # Configurazione Obsidian (ignorata dal watcher)
├── attachments/        # Allegati (ignorati dal watcher)
├── personal/           # Note personali
├── shared/             # Note condivise
└── work/               # Note di lavoro
```

## Frontmatter delle Note

Le note possono contenere frontmatter YAML:

```yaml
---
scope: work
type: note
entities:
  - progetto-alfa
tags:
  - architettura
source: obsidian
---
```

**Campi supportati:**
- `scope`: work, personal, shared
- `type`: note, decision, meeting, idea
- `entities`: progetti o entità correlate
- `tags`: tag per categorizzazione
- `source`: origine della nota (obsidian, watcher, voice, etc.)

## Wikilinks Obsidian

Il sistema supporta i wikilinks di Obsidian:
- `[[altra nota]]`: link a un'altra nota
- I wikilinks vengono preservati nel testo indicizzato
- Attualmente non vengono estratti come metadata separati

## Testing

Esegui i test per verificare il funzionamento:
```bash
pytest -v
```

I test includono verifiche specifiche per l'integrazione con Obsidian.

## Note Operative

- I modelli ML (`intfloat/multilingual-e5-large`, `faster-whisper`) vengono scaricati localmente durante il setup
- Le chiamate OpenRouter hanno retry singolo e fallback conservativo
- L'indice Chroma può essere ricreato interamente dai file in `kb/`
- Il watcher usa polling di 10 secondi per compatibilità con Obsidian
- File temporanei e di configurazione vengono automaticamente ignorati

## Risoluzione Problemi

**Il watcher non rileva le modifiche:**
- Verifica che Docker sia in esecuzione: `docker compose ps`
- Controlla i log: `docker compose logs`

**Classificazione automatica non funziona:**
- Verifica che `OPENROUTER_API_KEY` sia impostato in `.env`
- Controlla che `watcher_auto_classify` sia `true` nella configurazione

**ChromaDB vuoto o corrotto:**
- Esegui `python -m src.storage.rehydrate` per ricostruire l'indice

**Test falliscono:**
- Assicurati di aver attivato il virtualenv: `source .venv/bin/activate`
- Verifica che tutte le dipendenze siano installate: `pip install -r requirements.txt`
