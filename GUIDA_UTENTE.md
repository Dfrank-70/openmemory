# Guida Utente - Open Memory

Open Memory è un sistema di memoria persistente personale per agenti AI. Questa guida spiega le funzioni attualmente disponibili.

## Panoramica del Progetto

### Finalità Complessive

Open Memory è un sistema di memoria persistente progettato per agenti AI che permette di:
- Memorizzare e organizzare informazioni in formato Markdown compatibile con Obsidian
- Indicizzare semanticamente i contenuti per ricerca intelligente
- Tracciare automaticamente i commit git di progetti monitorati
- Fornire accesso strutturato alla knowledge base tramite server MCP
- Integrare diverse fonti di dati (note, voice, email, progetti git)

### Architettura

Il sistema si basa su tre componenti principali:

1. **Git Repository** - Fonte di verità per tutti i dati
   - Knowledge base in `kb/` (Markdown compatibile Obsidian)
   - Codice sorgente e configurazione
   - Storia completa delle modifiche

2. **ChromaDB** - Indice derivato ricostruibile
   - Embedding vettoriali per ricerca semantica
   - Metadati strutturati per filtraggio
   - Può essere ricostruito completamente dai file in `kb/`

3. **Server MCP** - Interfaccia per agenti AI esterni
   - Tool: search, get_project, get_context
   - Due profili: work (localhost:8000) e full (localhost:8001)
   - Accesso programmatico alla knowledge base

### Funzionalità Implementate

**Core:**
- ✅ Ingestione note da CLI e Obsidian
- ✅ Classificazione automatica delle note
- ✅ Embedding e ricerca semantica con ChromaDB
- ✅ Watcher automatico per monitoraggio file system
- ✅ Registrazione e tracciamento progetti git
- ✅ Git hook per aggiornamento automatico changelog
- ✅ Server MCP con tool di ricerca e contesto

**Ingestori Avanzati:**
- ✅ Note vocali (trascrizione audio)
- ✅ Monitor email IMAP
- ✅ Bootstrap multi-progetti da configurazione

**Utility:**
- ✅ Script di setup automatico
- ✅ Backup periodico via cron
- ✅ Ricostruzione indice (rehydrate)
- ✅ Generazione digest riassuntivi
- ✅ Riconciliazione documenti orfani

### Stato di Sviluppo

**Completato:**
- Architettura core stabile
- Integrazione Obsidian funzionante
- Sistema di indicizzazione affidabile
- Server MCP operativo
- Suite test completa

**In Corso:**
- Miglioramento integrazione Obsidian
- Ottimizzazione performance

**Future:**
- Interfaccia web per gestione manuale
- Supporto additional formati (PDF, DOCX)
- Integrazione con altri servizi esterni

### Limitazioni Note

- Il git hook non può tracciare il repository che lo contiene (per evitare loop infiniti)
- Dipendenza da Docker per ChromaDB
- Richiede Python 3.12
- Classificazione automatica richiede API key OpenRouter
- Watcher usa polling (10 secondi) per compatibilità Obsidian

### Requisiti di Sistema

- **Python:** 3.12+
- **Docker:** per ChromaDB
- **Spazio disco:** ~1GB per modelli ML
- **Opzionale:** OpenRouter API key per classificazione automatica
- **Opzionale:** Obsidian per interfaccia grafica

### Prossimi Passi

1. Completare integrazione Obsidian (wikilinks come metadata)
2. Sviluppare interfaccia web per gestione knowledge base
3. Aggiungere supporto formati documenti aggiuntivi
4. Migliorare performance indicizzazione per knowledge base large
5. Integrazione con altri servizi di note-taking

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
-à 