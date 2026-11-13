# Agenti — MCP e CLI

Guida di riferimento per usare il motore come **strumento di un agente**:
un'interfaccia **CLI macchina-leggibile** (`--json`, `--json-stream`,
`--describe`) e un **server MCP su stdio** (`--mcp`), con tool, risorse, prompt,
job, progresso e annullamento.

Il documento descrive il contratto pubblico; l'implementazione vive in
`tools/agent.py` (AgentAPI, job runner, trasporto) e `tools/frontend.py` (CLI),
ed è inclusa nel monofile generato.

- [1. In breve](#1-in-breve)
- [2. Architettura](#2-architettura)
- [3. Requisiti e installazione](#3-requisiti-e-installazione)
- [4. CLI per agenti](#4-cli-per-agenti)
- [5. Server MCP](#5-server-mcp)
- [6. Ricette](#6-ricette)
- [7. Errori e troubleshooting](#7-errori-e-troubleshooting)
- [8. Sicurezza](#8-sicurezza)
- [9. Test e verifica](#9-test-e-verifica)
- [10. Limiti e non-obiettivi](#10-limiti-e-non-obiettivi)

---

## 1. In breve

Due modi per parlare con il motore, stesso livello semantico:

| Interfaccia | Quando usarla | Comando |
|---|---|---|
| **CLI JSON** | script, agenti con sola shell, pipeline, debug | `noesis-ebook-translator-engine … --json` |
| **MCP stdio** | agenti con supporto MCP (Claude Desktop, Cursor, OpenCode…) | `noesis-ebook-translator-engine --mcp` |

Capacità esposte:

- **scoperta**: motori, lingue, metadati, TOC, segmenti, cache, run interrotte;
- **pianificazione**: token, costo in USD, durata, senza tradurre;
- **anteprima**: pochi segmenti tradotti per saggiare tono e qualità;
- **traduzione**: job asincrono su tutto il libro o su capitoli selezionati,
  con progresso, log incrementali, annullamento e ripresa;
- **export**: capitoli (epub/html/md/txt/json/csv/docx/pdf), figure, tabelle;
- **configurazione**: modello e chiave API per motore.

Nessuna dipendenza aggiuntiva: il server MCP è implementato nel monofile, con
solo la libreria standard. L'SDK ufficiale `mcp` serve **solo** al test di
interoperabilità.

---

## 2. Architettura

```
Agente (Claude Desktop / Cursor / OpenCode / script)
   │  MCP stdio (JSON-RPC 2.0, NDJSON)       │  shell
   ▼                                         ▼
serve_mcp()  ──────────────────┐        CLI: --json / --json-stream / --describe
                               ├──►  AgentAPI (dict in / dict out, zero dipendenze)
JobRunner (1 job, thread)  ────┘             │
                                             ▼
                               motore inlineato (verbatim dal desktop)
```

- **AgentAPI** valida path, selezioni, impostazioni; traduce le eccezioni del
  motore in codici stabili; è l'unica fonte di verità per CLI e MCP.
- **JobRunner** esegue **una** traduzione alla volta, registra eventi
  incrementali (`plan`, `progress`, `log`, `state`), supporta `should_cancel` e
  lascia la cache pronta per la ripresa.
- **serve_mcp** implementa JSON-RPC 2.0 su stdio con framing **NDJSON** (una
  riga per messaggio), `tools`, `resources`, `prompts`, `progress` e
  `cancelled`. Accetta `Content-Length` solo in lettura, per tolleranza.

---

## 3. Requisiti e installazione

```bash
pip install -r requirements.txt            # motore (ebooklib, lxml, mechanize, cssselect)
pip install -r requirements-tui.txt        # solo per -gui
python noesis_ebook_translator_engine.py --version
```

- Python ≥ 3.10.
- Nessun pacchetto MCP richiesto a runtime.
- Il server funziona anche nel binario PyInstaller (`--mcp` è un flag del
  binario, nessuna dipendenza esterna).
- Per il test di interoperabilità (solo sviluppo/CI): `pip install mcp`.

---

## 4. CLI per agenti

Tutte le modalità macchina sono **non interattive**: leggono solo gli argomenti,
scrivono il risultato su **stdout** e i log su **stderr**.

### 4.1 Scoperta: `--describe`

Stampa il manifest completo (stesso registro di `tools/list`: nomi, schema
JSON, annotazioni, risorse, prompt, versioni, exit code).

```bash
noesis-ebook-translator-engine --describe
```

Struttura:

```json
{
  "server": {"name": "noesis-ebook-translator", "version": "v2.5.0",
             "api_version": "1.0", "protocol": "2025-06-18",
             "protocol_versions": ["2025-06-18", "2025-03-26", "2024-11-05"]},
  "roots": ["/percorso/corrente"],
  "read_only": false,
  "tools": [{"name": "plan_translation", "inputSchema": {...},
             "annotations": {"readOnlyHint": true, ...}}],
  "resources": [...],
  "resource_templates": [...],
  "prompts": [...],
  "cli": {"json": ["--json", "--json-stream", "--describe", "--dry-run"],
          "server": ["--mcp", "--root DIR", "--read-only"],
          "exit_codes": {"0": "ok", "1": "error", "2": "usage",
                         "130": "cancelled"}}
}
```

### 4.2 Contratto di output

| Modalità | stdout | stderr | Uso |
|---|---|---|---|
| `--json` | **un** documento JSON | log/progressi | parsing diretto |
| `--json-stream` | NDJSON di eventi | — | monitoraggio in tempo reale |
| `--dry-run` | un documento JSON (piano) | — | stima senza scrivere |
| default | testo umano | log/progressi | uso interattivo |

Eventi di `--json-stream`:

```json
{"type": "progress", "data": {"fraction": 0.42, "message": "Chapter 3"}}
{"type": "log", "data": {"text": "...", "error": false}}
{"type": "result", "data": {"output": "/libri/libro_italian.epub", ...}}
{"type": "error", "data": {"code": "not_found", "message": "..."}}
```

L'ultimo evento di una run riuscita è sempre `result`; in caso di errore è
`error` (exit code 1). I log sono limitati (max ~2/s) per non inondare il canale.

Errore in modalità JSON:

```json
{"ok": false, "error": {"code": "not_found", "message": "chapter selection matched nothing: [999]"}}
```

Codici: `not_found`, `permission_denied`, `invalid_path`, `invalid_argument`,
`ambiguous`, `busy`, `cancelled`, `no_api_key`, `bad_api_key`,
`unsupported_model`, `translation_failed`, `chapter_error`, `unknown_engine`,
`internal_error`.

Exit code: `0` ok, `1` errore, `2` uso scorretto, `130` annullato con Ctrl+C.

### 4.3 Riferimento dei flag

Flag esistenti (`--help` per l'elenco completo) più quelli per agenti:

| Flag | Descrizione |
|---|---|
| `--json` | output JSON a documento singolo |
| `--json-stream` | eventi NDJSON (`progress`/`log`/`result`/`error`) |
| `--describe` | manifest di tool/risorse/prompt ed esce |
| `--dry-run` | piano e stima (token, costo, durata); non scrive |
| `--resume` | precompila dalla run interrotta più recente |
| `--style TESTO` | addendum di stile/genere per i motori LLM |
| `--genre GENRE` | genere registrato con la run |
| `--cache-dir DIR` | cache stabile (usata anche dalla ripresa) |
| `--config-dir DIR` | configurazione isolata (isola anche la cache) |
| `--mcp` | avvia il server MCP stdio |
| `--root DIR` | (solo `--mcp`) root consentite, ripetibile |
| `--read-only` | (solo `--mcp`) vieta ogni scrittura |
| `--verbose` | (solo `--mcp`) log debug su stderr |
| `--max-output N` | (solo `--mcp`) limite caratteri dei tool di testo |

> La confinazione dei path vale **solo** per il server MCP. La CLI è la shell
> dell'utente e accetta qualsiasi percorso, come prima.

### 4.4 Esempi

```bash
# Cosa sa fare
noesis-ebook-translator-engine --describe

# Piano completo (nessuna scrittura, nessuna rete)
noesis-ebook-translator-engine libro.epub --dry-run

# Piano di un solo capitolo (indice 1-based)
noesis-ebook-translator-engine libro.epub --dry-run --chapters 3

# Traduzione di un capitolo, output JSON
noesis-ebook-translator-engine libro.epub -e DeepSeek --model deepseek-chat \
  -t Italian --chapters "3" --json

# Eventi in tempo reale
noesis-ebook-translator-engine libro.epub -e ChatGPT --json-stream

# Ripresa della run interrotta (motore, lingue, capitoli, output, stile)
noesis-ebook-translator-engine libro.epub --resume --json

# Anteprima di 5 segmenti
noesis-ebook-translator-engine libro.epub -e Claude --preview 5 --json

# Export di capitoli / figure / tabelle
noesis-ebook-translator-engine libro.epub --export-only text --export-format md \
  -o libro.md --json
noesis-ebook-translator-engine libro.epub --export-only figures \
  -o figure/ --json
```

**Selezione dei capitoli** (`--chapters` e `chapters` dei tool):

- indice 1-based sull'indice appiattito: `"3"` o `3`;
- lista/range: `"1,3,5-7"`, `["1", "5-7"]`;
- href o nome file del capitolo;
- **titolo unico** (case/space-insensitive), es. `"Preface to the Second Edition."`.

Se la selezione non corrisponde a nulla → errore `not_found` (mai un EPUB
vuoto). Se il titolo è ambiguo → `ambiguous`, con l'indicazione di usare
`list_chapters` e l'indice.

---

## 5. Server MCP

### 5.1 Avvio

```bash
noesis-ebook-translator-engine --mcp --root ~/Libri --cache-dir ~/.cache/noesis
```

- Lo stdin/stdout sono il canale del protocollo: **non** lanciarlo da un
  terminale interattivo (lo rifiuta con exit 2).
- `--config-dir` isola configurazione **e** cache: consigliato per non
  toccare la config del desktop.
- `--root` è ripetibile; default: directory corrente (o `$HOME` se la cwd è la
  radice).
- `--read-only` disabilita traduzione/export/dismiss.
- Log e diagnostica vanno su stderr; `--verbose` alza il dettaglio.

### 5.2 Configurazione del client

Il server MCP è **lo stesso binario/comando** della CLI: non serve installare
altro. `pip install mcp` è richiesto solo dal test di interoperabilità.

Usa un **path assoluto** se il client non eredita il `PATH` (tipico delle app
grafiche su macOS/Windows), oppure `python` + il percorso del monofile.

**Claude Desktop** — `claude_desktop_config.json`:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "noesis-ebook-translator": {
      "command": "/home/me/.venv/bin/noesis-ebook-translator-engine",
      "args": ["--mcp", "--root", "/home/me/Libri"],
      "env": {"NOESIS_CONFIG_DIR": "/home/me/.config/noesis-mcp"}
    }
  }
}
```

Su Windows: forward slash o doppio backslash
(`"C:/Users/me/AppData/Local/Programs/noesis-ebook-translator-engine.exe"`).

**Cursor** — `~/.cursor/mcp.json` (globale) o `.cursor/mcp.json` (progetto),
schema `mcpServers`.

**OpenCode** — `opencode.json` (progetto) o `~/.config/opencode/opencode.json`;
schema diverso: `command` è un array, l'ambiente si chiama `environment`.

```json
{
  "mcp": {
    "noesis-ebook-translator": {
      "type": "local",
      "command": ["noesis-ebook-translator-engine", "--mcp",
                  "--root", "/home/me/Libri"],
      "environment": {"NOESIS_CONFIG_DIR": "/home/me/.config/noesis-mcp"},
      "enabled": true
    }
  }
}
```

**Altri client** — schema `mcpServers` con `command`/`args`/`env`.

Dopo la modifica **riavvia il client**. Ogni client avvia un proprio processo;
la config isolata evita sovrapposizioni con il desktop.

#### Verifica

```bash
noesis-ebook-translator-engine --describe | head

printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"check","version":"1"}}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  | noesis-ebook-translator-engine --mcp --root .
```

Se il secondo messaggio elenca i tool, il server funziona; altrimenti controlla
path assoluto, validità del JSON, `--root` e riavvia il client.

### 5.3 Trasporto e protocollo

- **JSON-RPC 2.0** su stdio, framing **NDJSON**: un messaggio JSON per riga
  (`\n`), UTF-8, nessun `Content-Length`. Il server accetta `Content-Length`
  solo in ingresso, per tolleranza.
- Versione negoziata: `2025-06-18` (default), `2025-03-26`, `2024-11-05`.
  A un client che chiede una versione sconosciuta si risponde con la nostra.
- Metodi: `initialize`, `ping`, `tools/list|call`, `resources/list|read`,
  `resources/templates/list`, `prompts/list|get`, `logging/setLevel`,
  `notifications/initialized|cancelled`.
- Il batching JSON-RPC non è supportato (`-32600`).
- Errori di protocollo → `error` JSON-RPC; errori di dominio → risultato con
  `isError: true` e `structuredContent.error.{code,message}`.

### 5.4 `capabilities`

Tool di scoperta, da chiamare per primo:

```json
{
  "api_version": "1.0",
  "engine_version": "v2.5.0",
  "server": "noesis-ebook-translator",
  "mcp_protocol": "2025-06-18",
  "mcp_protocol_versions": ["2025-06-18", "2025-03-26", "2024-11-05"],
  "roots": ["/home/me/Libri"],
  "root_confinement": true,
  "read_only": false,
  "config_dir": "/home/me/.config/noesis-mcp",
  "cache_dir": "...",
  "cache_path": "...",
  "engines": 18,
  "languages": 243,
  "default_engine": "Google(Free)New",
  "settings_schema": {"translation_position": {...}, "...": {}},
  "limits": {"max_output_chars": 20000, "max_preview_segments": 50,
             "max_batch_segments": 20, "chapter_formats": ["epub", "..."]},
  "features": {"jobs": true, "progress": true, "cancel": true,
               "resume": true, "resources": true, "prompts": true},
  "notes": ["One translation job at a time; ...", "..."]
}
```

`root_confinement` è `true` solo nel server; `--describe` da CLI riporta
`false` perché la CLI non confina i path.

### 5.5 Tool

Legenda: `RO` = `readOnlyHint`, `OW` = `openWorldHint`, `D` = `destructiveHint`.

| Tool | Flag | Parametri principali | Restituisce |
|---|---|---|---|
| `capabilities` | RO | — | versioni, root, directory, limiti, schema impostazioni |
| `list_engines` | RO | — | motori con free/API key, provider, modelli, `configured` |
| `inspect_book` | RO | `input`, `chapters`, `engine`, `source_lang`, `target_lang` | metadati, TOC, segmenti/caratteri per capitolo, cache, run interrotte |
| `list_chapters` | RO | `input` | indice, titolo, href, file, profondità |
| `read_chapter` | RO | `input`, `chapter`, `offset`, `limit` | testo del capitolo, `truncated`, `next_offset`, `untrusted` |
| `plan_translation` | RO | `input`, `chapters`, `engine`, `model`, `source_lang`, `target_lang`, `batching` | segmenti, caratteri, token, `cost_usd`, durata, `per_chapter`, `warnings` |
| `preview_translation` | RO, OW | `input`, `chapters`, `engine`, `model`, lingue, `limit` (1–50) | coppie `source`/`translation`; nessuna scrittura |
| `cache_status` | RO | `input` | `coverage`, `segments_total`, `segments_done`, `status`, run interrotte |
| `interrupted_runs` | RO | `input` (opz.) | run con opzioni, lingue, output, `done/total` |
| `start_translation` | OW | `input`, `output`, `engine`, `model`, `api_key`, lingue, `chapters`, `position`, `cache`, `batching`, `style`, `genre`, `wait_seconds` | snapshot del job (`job_id`, `state`, …) |
| `job_status` | RO | `job_id`, `after` | stato, progresso, piano, risultato, `events`, `next_cursor` |
| `collect_job` | RO | `job_id`, `wait_seconds` | snapshot finale (attende fino a N s) |
| `cancel_job` | RO | `job_id`, `wait_seconds` | snapshot; la cache resta per la ripresa |
| `export_book` | D | `input`, `kind`, `format`, `output`, `chapters`, `target_lang` | file scritti |
| `dismiss_interrupted_run` | D | `input` oppure `cache_path` | run non più offerta (le traduzioni restano) |
| `configure_engine` | D | `engine`, `model`, `api_key` | preferenza salvata; la chiave non viene mai restituita |

Dettagli utili:

- **`inspect_book`** è la chiamata di orientamento: una sola risposta con
  metadati, capitoli, segmenti e stato della cache; include `next_steps`.
- **`plan_translation`** non fa rete e non scrive. `cost_usd` è `null` quando il
  prezzo non è noto (motore gratuito o modello fuori catalogo): il motivo è in
  `warnings`. `duration_seconds` usa la velocità misurata dell'ultima run, se
  disponibile.
- **`preview_translation`** è l'unico tool `readOnly` che fa rete: spendi pochi
  segmenti per decidere stile e motore. È rifiutato con `busy` mentre un job
  gira.
- **`start_translation`** valida tutto prima di restituire il `job_id` (path,
  motore, selezione capitoli); l'esecuzione è asincrona. Con
  `wait_seconds > 0` la chiamata resta aperta fino a N secondi e trasmette
  `notifications/progress`, poi restituisce lo snapshot (il job continua se non
  è finito).
- **`job_status`** è incrementale: passa `after = next_cursor` per ricevere solo
  i nuovi eventi. Tipi: `state`, `plan`, `progress`, `log`, `cancel`.
- **`cancel_job`** imposta `should_cancel`: il motore si ferma al primo punto
  sicuro e conserva la cache; `cancel` è idempotente.
- **`export_book`**: `kind = chapters` scrive un file (`output`), `figures` e
  `tables` scrivono in una directory (se `output` ha estensione, si usa la sua
  cartella). Formati capitoli: `epub`, `html`, `md`, `txt`, `json`, `csv`,
  `docx`, `pdf`; figure: `img`, `html`, `md`; tabelle: `csv`, `html`, `md`.
- **`configure_engine`** scrive nella config del server: usalo con
  `NOESIS_CONFIG_DIR`/`--config-dir` isolati. Preferisci l'ambiente.

### 5.6 Risorse

| URI | Contenuto |
|---|---|
| `noesis://capabilities` | stesse informazioni di `capabilities` |
| `noesis://engines` | catalogo motori |
| `noesis://book/<book_id>` | brief del libro (metadati, TOC, segmenti, cache) |
| `noesis://book/<book_id>/toc` | tabella dei capitoli |
| `noesis://book/<book_id>/chapter/<n>` | testo del capitolo `n` (limitato) |

`book_id` è lo SHA-1 abbreviato del path reale, restituito da `inspect_book`,
`list_chapters` e `plan_translation`. Un libro entra nel registro quando viene
letto da un tool; le risorse vengono filtrate in base alle `--root`.

Template dichiarato: `noesis://book/{book_id}/chapter/{chapter}`.

### 5.7 Prompt

| Prompt | Argomenti | Scopo |
|---|---|---|
| `translate_book` | `input`, `target_lang`, `style` | workflow guidato: inspect → plan → preview → start → poll |
| `review_translation` | `input`, `chapter` | confronto sorgente/traduzione e correzioni concrete |

### 5.8 Job, progresso, annullamento

Esempio di sequenza (equivalente a quella di un agente):

```json
{"name":"start_translation","arguments":{"input":"/libri/b.epub",
  "engine":"DeepSeek","model":"deepseek-chat","target_lang":"Italian",
  "chapters":3,"wait_seconds":0}}
→ {"job_id":"7f3a1c","state":"queued","next_cursor":0,...}

{"name":"job_status","arguments":{"job_id":"7f3a1c","after":0}}
→ {"state":"running","progress":{"fraction":0.32,"message":"Chapter 3"},
   "events":[{"seq":1,"type":"plan","data":{...}},
             {"seq":2,"type":"progress","data":{...}}],"next_cursor":2}
```

Con `_meta.progressToken` il server invia `notifications/progress` con
`progressToken`, `progress` (0–1), `total` e `message` (throttle ~4/s).

`notifications/cancelled` annulla il job attivo. Un solo job alla volta: il
secondo `start_translation` risponde `busy`; usa `cancel_job` o attendi.

### 5.9 Configurazione persistente

- `--config-dir`/`NOESIS_CONFIG_DIR`: configurazione isolata; la cache segue la
  stessa directory se non passi `--cache-dir`.
- `--cache-dir`: store dedicato (utile per cache stabile tra riavvii; il default
  su Linux/macOS è una directory temporanea).
- Chiavi API: da ambiente/configurazione del server; `configure_engine` e
  `api_key` di `start_translation` scrivono nella config (opt-in) e non vengono
  mai restituiti.
- Proxy: il motore rispetta `http_proxy`/`https_proxy` (e SOCKS5 se `PySocks` è
  installato).

---

## 6. Ricette

### «Traduci il capitolo X del libro Y in italiano»

1. `inspect_book` (o `list_chapters`) → trova l'indice del titolo.
2. `plan_translation` con `chapters: <indice>` → segmenti e costo.
3. `preview_translation` con `limit: 5–10` → controlla il tono.
4. `start_translation` con `chapters: <indice>`, `target_lang: "Italian"`,
   `wait_seconds` oppure polling di `job_status`.
5. `read_chapter` sull'output per la revisione, oppure `export_book`.

CLI equivalente:

```bash
noesis-ebook-translator-engine libro.epub -t Italian --chapters 3 --json
```

Nota: la traduzione di un capitolo produce un EPUB con **solo** quel capitolo;
la selezione è 1-based sull'indice appiattito. Un titolo ambiguo richiede
l'indice.

### «Quanto costa e quanto dura?»

```json
{"name":"plan_translation","arguments":{"input":"/libri/b.epub",
  "engine":"Claude","model":"claude-3-5-sonnet-latest"}}
```

`cost_usd` è `null` per motori gratuiti o modelli assenti dal catalogo:
controlla `warnings` e `price_per_million_usd`.

### «Riprendi dopo un crash»

1. `interrupted_runs` con `input` → la run più recente con `options`,
   `chapters`, `output_path`.
2. `start_translation` con gli stessi parametri: la cache salta i segmenti già
   tradotti.
3. Da CLI: `--resume` precompila tutto dalla run più recente, incluso l'output.

### «Esporta il capitolo in Markdown»

```json
{"name":"export_book","arguments":{"input":"/libri/b_it.epub",
  "kind":"chapters","format":"md","output":"/libri/capitolo.md","chapters":3}}
```

### «Rivedi la traduzione»

1. `read_chapter` sul sorgente (capitolo `n`).
2. `read_chapter` sull'output (capitolo 1, se l'output contiene un solo
   capitolo).
3. Se serve, riparti con `style` diverso e `cache: true` (le parti invariate
   restano in cache).

### «Scopri cosa può fare prima di agire»

`--describe` per la CLI, `capabilities` via MCP; entrambi derivano dallo stesso
registro, quindi non possono divergere.

---

## 7. Errori e troubleshooting

| Sintomo | Causa / rimedio |
|---|---|
| exit 2 con «--mcp expects an MCP client on stdin» | stai lanciando il server da un terminale: usalo dal client MCP |
| `permission_denied` su un path | fuori dalle `--root` (server) o `--read-only` attivo |
| `busy` su `start_translation` | c'è già un job; `job_status`/`cancel_job` |
| `unknown_engine` | usa `list_engines` e passa il nome esatto |
| `ambiguous` | titolo duplicato: passa l'indice da `list_chapters` |
| `not_found` su `chapters` | selezione vuota: nessun EPUB vuoto viene creato |
| `no_api_key` / `bad_api_key` | configura la chiave (env o `configure_engine`) |
| `cost_usd: null` | motore gratuito o modello fuori catalogo: vedi `warnings` |
| il client non vede i tool | verifica `tools/list`, la versione del protocollo e che stdout non sia inquinato |
| output corrotto/illeggibile | non stampare nulla su stdout nel codice del server; log solo su stderr |
| cache persa dopo il riavvio | usa `--cache-dir` (il default può stare in `/tmp`) |

---

## 8. Sicurezza

- **Path confinati** (solo server): realpath, niente escape via `..` o symlink;
  `--read-only` vieta traduzione/export/dismiss.
- **Un job alla volta** per processo: niente corse sullo stato globale del
  motore (config di classe, cache condivisa).
- **Segreti**: chiavi da ambiente o config isolata; `configure_engine` è
  esplicito e non restituisce mai la chiave; i log non la contengono.
- **Testo del libro non attendibile**: i tool restituiscono contenuto con
  `untrusted: true`; le descrizioni avvisano di non eseguire istruzioni trovate
  dentro un EPUB (prompt injection).
- **Nessuna rete in ascolto**: solo stdio locale, nessun trasporto HTTP/SSE,
  nessuna autenticazione multiutente. Non esporlo su una rete.
- **Output limitato**: `--max-output` (default 20 000 caratteri) e
  `read_chapter` paginato evitano risposte enormi.

---

## 9. Test e verifica

```bash
# suite completa (agent, MCP, CLI, motore, sync, TUI)
python -m unittest discover -s tests -v

# interoperabilità con il client MCP ufficiale (richiede `pip install mcp`)
python -m unittest tests.test_mcp_interop -v

# dieci workflow E2E offline su testo Rosen (fallback al corpus in CI)
python scripts/e2e/run_all.py
python scripts/e2e/run_all.py --list
```

I test coprono: schema dei tool (`--describe` ≡ `tools/list`), framing NDJSON,
handshake e negoziazione versione, resources/prompts, path policy, job
(start/poll/cancel/resume), notifiche di progresso, contratto `--json` /
`--json-stream`, sessione stdio reale in sottoprocesso e traduzione completa via
stdio con motori offline.

---

## 10. Limiti e non-obiettivi

- Un solo job di traduzione per processo.
- Nessun trasporto HTTP/SSE, multiutente o remoto.
- `sampling`/`elicitation` (l'engine che interroga l'agente) non sono
  implementati: la direzione supportata è agente → engine.
- Nessun tool per glossario/quality judge (il motore li supporta via config, ma
  non sono esposti come tool).
- L'engine non modifica i moduli verbatim: il livello agenti vive in
  `tools/agent.py` e viene appeso al monofile dal sync.

---

## Riferimenti

- `README.md` — uso della CLI e della TUI.
- `AGENTS.md` — come è costruito il repo e regole di sync.
- `scripts/e2e/README.md` — i dieci workflow end-to-end.
- `tools/agent.py` — AgentAPI, job runner, server MCP.
- `tools/frontend.py` — CLI e modalità macchina.
