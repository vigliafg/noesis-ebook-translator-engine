# Noesis Ebook Translator — Engine (CLI + TUI)

[![tests](https://github.com/vigliafg/noesis-ebook-translator-engine/actions/workflows/tests.yml/badge.svg)](https://github.com/vigliafg/noesis-ebook-translator-engine/actions/workflows/tests.yml)
[![release](https://github.com/vigliafg/noesis-ebook-translator-engine/actions/workflows/release.yml/badge.svg)](https://github.com/vigliafg/noesis-ebook-translator-engine/actions/workflows/release.yml)

**`noesis-ebook-translator-engine`** è l'edizione **da riga di comando** del
motore di [Noesis Ebook Translator](https://github.com/vigliafg/noesis-ebook-translator):
traduce un **EPUB** in un'altra lingua conservando la formattazione, i **markup
inline** (corsivi, link…), i blocchi di codice e l'**indice** (TOC).

È lo **stesso motore** dell'app desktop, qui impacchettato in un **singolo file**
(`noesis_ebook_translator_engine.py`) con un front-end **CLI** e, con `-gui`, una
**TUI opzionale** (Textual) per chi vuole l'interfaccia guidata senza la GUI.

Nessuna dipendenza da Qt: solo il motore di traduzione e il traduttore.

---

## Indice

- [A cosa serve](#a-cosa-serve)
- [Il motore inlineato](#il-motore-inlineato)
- [Motori supportati](#motori-supportati)
- [Lingue](#lingue)
- [Requisiti](#requisiti)
- [Installazione](#installazione)
- [Avvio rapido](#avvio-rapido)
- [Esempi d'uso](#esempi-duso)
- [Riferimento delle opzioni](#riferimento-delle-opzioni)
- [Interfaccia TUI (`-gui`)](#interfaccia-tui--gui)
- [Output](#output)
- [Agenti: CLI JSON e server MCP](#agenti-cli-json-e-server-mcp)
- [Guida completa agenti (MCP + CLI)](docs/agenti-mcp-cli.md)
- [Build delle release](#build-delle-release)
- [Come è costruito](#come-è-costruito)
- [Test e CI](#test-e-ci)
- [Licenza](#licenza)

---

## A cosa serve

Hai un EPUB in inglese e lo vuoi in italiano (o in un'altra lingua) **senza
aprire nessuna finestra**. Con un solo comando ottieni il file tradotto accanto
all'originale, con la formattazione e l'indice conservati:

```bash
noesis-ebook-translator-engine libro.epub
# → libro_ITALIAN.epub
```

Essendo l'edizione **engine** dell'app desktop, condivide **lo stesso motore di
traduzione** copiato verbatim (vedi [Il motore inlineato](#il-motore-inlineato)):
il risultato è identico a quello prodotto dal desktop.

---

## Il motore inlineato

Il file `noesis_ebook_translator_engine.py` è un **unico modulo generato**: lo
script `tools/sync_from_desktop.py` **inlinea** i moduli del motore
(`lib/` + `engines/`, più `appconfig.py` e `book.py`) dal repository desktop e vi
appende due blocchi scritti a mano: il **livello agenti**
(`tools/agent.py` — AgentAPI + server MCP) e il **front-end CLI/TUI**
(`tools/frontend.py`).

Il motore è una copia **verbatim** del fork del plugin Calibre di **bookfere**:

- **Ebook Translator (plugin Calibre)** — autore **bookfere**
  (<https://translator.bookfere.com>)
- Repository upstream:
  <https://github.com/bookfere/Ebook-Translator-Calibre-Plugin>
- Licenza upstream: **GNU GPL v3.0**

Crediti e ringraziamenti a **bookfere** per il motore originale. La piccola
superficie dell'API `calibre` di cui il motore ha bisogno è reimplementata
all'interno del file generato, così **Calibre non serve**.

L'unico file **non** verbatim del motore è `engines/__init__.py` (override locale
che ripristina **tutti** i motori del plugin). Vedi `AGENTS.md` e
`ENGINE_SOURCE.json`.

---

## Motori supportati

Sono esposti tutti i motori ripristinati in `engines/__init__.py`; l'elenco
esatto (con l'indicazione di *free* / *API key* e dei modelli) si ottiene con:

```bash
noesis-ebook-translator-engine --list-engines
```

| Categoria | Motori |
| --- | --- |
| Google (gratuiti) | `Google(Free)New`, `Google(Free)Html`, `Google(Free)` |
| Google (API) | `Google(Basic)`, `Google(Basic)ADC`, `Google(Advanced)` |
| LLM | `Gemini`, `ChatGPT`, `ChatGPT(Azure)`, `Claude`, `DeepSeek`, `OpenRouter` |
| DeepL | `DeepL`, `DeepL(Pro)`, `DeepL(Free)` |
| Altri | `MicrosoftEdge(Free)`, `Youdao`, `Baidu` |

I motori LLM e le API a pagamento richiedono una **chiave API** (e a volte un
**modello**, es. `gpt-4o-mini`) da passare con `--api-key` / `--model`. I motori
Google gratuiti, DeepL Free e Microsoft Edge funzionano senza chiave.

---

## Lingue

- **Origine**: una lingua esplicita (default `English`) — usata per dare un
  suggerimento al motore.
- **Destinazione**: il set Google copre **~240 lingue**
  (`engines/languages.py`); la disponibilità effettiva dipende dal motore scelto.

Esempi di codici/nomi accettati: `English`, `Italian`, `French`, `German`,
`Spanish`, `Portuguese`, `Russian`, `Chinese`, `Japanese`… Il file tradotto
porta il suffisso della lingua di destinazione in **maiuscolo** (vedi
[Output](#output)).

---

## Requisiti

- **Python 3.10+**
- **pip**
- Connessione a Internet per i motori online.
- *(opzionale)* **Textual ≥ 0.80** — serve solo per la **TUI `-gui`**. Senza
  Textual il comando funziona lo stesso: `-gui` ripiega su un wizard a righe.
- *(opzionale)* **PySocks** — solo per instradare i motori tramite proxy SOCKS5.

---

## Installazione

Tre modi equivalenti: binario precompilato, comando installato con `pip`,
oppure esecuzione diretta dal checkout.

### A) Binario precompilato (nessun Python richiesto)

Scarica l'artefatto della release per il tuo sistema dalla pagina
**Releases** di GitHub:

| Sistema | File | Installazione |
|---|---|---|
| Windows x64 | `noesis-ebook-translator-engine-windows-x64-setup.exe` | esegui l'installer NSIS: installa in `Program Files` e crea la voce nel menu Start (opzionale sul Desktop). Per usarlo da terminale aggiungi la cartella al `PATH` o usa il percorso completo |
| Windows x64 (portable) | `noesis-ebook-translator-engine-windows-x64.exe` | mettilo in una cartella nel `PATH` (es. `%LOCALAPPDATA%\Programs`) |
| macOS Intel / Apple Silicon | `…-macos-x64.dmg` / `…-macos-arm64.dmg` | apri il DMG, trascina il **binario** in `/usr/local/bin` (o `~/.local/bin`); se Gatekeeper blocca: `xattr -d com.apple.quarantine /usr/local/bin/noesis-ebook-translator-engine` |
| Linux x64 | `noesis-ebook-translator-engine-x86_64.AppImage` | `chmod +x` e spostalo in `~/.local/bin` (o `/usr/local/bin`) |

I binari hanno la **stessa** interfaccia della versione pip: CLI, `--json`,
`--describe` e `--mcp`. Non serve installare Python né pacchetti MCP.

### B) Con un ambiente virtuale (consigliato per lo sviluppo)

```bash
python3 -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# opzionale, per il comando e la TUI:
pip install -e ".[tui]"
python noesis_ebook_translator_engine.py --help
```

### C) Come comando installato

```bash
pip install .                 # oppure: pip install -e ".[tui]" per lo sviluppo
noesis-ebook-translator-engine --version
```

Dopo l'installazione il comando `noesis-ebook-translator-engine` è disponibile
ovunque (nella directory degli script di Python o del virtualenv; su Linux/macOS
spesso `~/.local/bin`, che deve essere nel `PATH`).

Per includere anche la **TUI** (`-gui`) installa l'extra `tui`:

```bash
pip install ".[tui]"                    # oppure: pip install -r requirements-tui.txt
noesis-ebook-translator-engine -gui
```

Per aggiornare un'installazione esistente: `pip install --upgrade .`.

### D) Senza installare nulla (uso dal checkout)

```bash
python noesis_ebook_translator_engine.py libro.epub
```

### E) Verifica dell'installazione

```bash
noesis-ebook-translator-engine --version        # versione del motore
noesis-ebook-translator-engine --help           # opzioni CLI
noesis-ebook-translator-engine --list-engines   # catalogo motori
noesis-ebook-translator-engine --describe       # manifest per agenti/MCP
```

Se `--describe` stampa JSON, l'installazione è completa: la stessa interfaccia
è pronta anche per il server MCP (`--mcp`).

---

## Avvio rapido

```bash
# 1) Traduzione con il motore Google gratuito, in italiano (default)
noesis-ebook-translator-engine libro.epub
# → libro_ITALIAN.epub

# 2) Motore e lingue espliciti
noesis-ebook-translator-engine libro.epub -e "Google(Free)New" -s English -t French

# 3) Testo bilingue (traduzione sotto l'originale)
noesis-ebook-translator-engine libro.epub --position below -o libro_bilingue.epub

# 4) Interfaccia guidata (TUI)
noesis-ebook-translator-engine -gui

# 5) Elenco dei motori disponibili
noesis-ebook-translator-engine --list-engines
```

---

## Esempi d'uso

### Tradurre in tedesco con Microsoft Edge (gratuito)

```bash
noesis-ebook-translator-engine novella.epub -e "MicrosoftEdge(Free)" -s English -t German
```

### Usare un motore LLM con chiave API e modello

```bash
noesis-ebook-translator-engine saggio.epub -e "ChatGPT" \
  --api-key "sk-..." --model "gpt-4o-mini" -s English -t Italian
```

### DeepL (Pro) da inglese a spagnolo

```bash
noesis-ebook-translator-engine libro.epub -e "DeepL(Pro)" \
  --api-key "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" -s English -t Spanish
```

### Output cartella/nome esplicito

```bash
noesis-ebook-translator-engine libro.epub -t Portuguese -o /percorso/out/libro_pt.epub
```

### Testo bilingue (traduzione sopra l'originale)

```bash
noesis-ebook-translator-engine libro.epub --position above -o libro_bi.epub
```

### Disattivare la cache e il batching online

```bash
noesis-ebook-translator-engine libro.epub --no-cache
```

### Interfaccia guidata (TUI)

```bash
noesis-ebook-translator-engine -gui
noesis-ebook-translator-engine -gui libro.epub -t French
```

---

## Riferimento delle opzioni

| Opzione | Valori | Default | Descrizione |
|---|---|---|---|
| `input` *(posizionale)* | percorso | — | L'EPUB di input (obbligatorio, **salvo con `-gui`**). |
| `-o`, `--output PATH` | percorso | accanto all'input | File EPUB di output. |
| `-e`, `--engine NAME` | nome motore | `Google(Free)New` | Motore di traduzione (vedi `--list-engines`). |
| `-s`, `--source LANG` | nome lingua | `English` | Lingua di origine. |
| `-t`, `--target LANG` | nome lingua | `Italian` | Lingua di destinazione. |
| `--position` | `only` · `below` · `above` | `only` | Posizione della traduzione: solo traduzione, oppure bilingue sotto/sopra l'originale. |
| `--chapters SPEC` | lista/href | tutto | Traduce/esporta solo i capitoli indicati (`1,3,5-7` oppure href). |
| `--export-format FMT` | vedi sotto | per tipo | Formato di export: `epub|html|md|txt` (capitoli), `img|html|md` (figure), `csv|html|md` (tabelle). |
| `--export-only KIND` | `figures` · `tables` · `text` | — | Estrae invece di tradurre. |
| `--preview N` | intero | — | Mostra N segmenti tradotti ed esce (anteprima offline). |
| `--list-chapters` | flag | — | Elenca i capitoli del libro ed esce. |
| `--batch` | flag | off | Abilita il **batching online** delle richieste. |
| `--no-cache` | flag | off | Disabilita la **cache** su disco. |
| `--api-key KEY` | stringa | — | Chiave API per il motore scelto (se richiesta). |
| `--model NAME` | stringa | — | Modello del motore scelto (per gli LLM). |
| `--style TESTO` | stringa | — | Addendum di stile/genere aggiunto al prompt dei motori LLM. |
| `--genre GENRE` | stringa | — | Genere del libro, registrato con le opzioni della run. |
| `--resume` | flag | off | Precompila le opzioni dalla run interrotta più recente. |
| `-gui`, `--gui` | flag | off | Avvia la **TUI** interattiva (o il wizard a righe). |
| `--list-engines` | flag | — | Elenca i motori disponibili ed esce. |
| `--version` | flag | — | Stampa la versione ed esce. |
| `--json` | flag | off | Output macchina: un solo documento JSON su stdout. |
| `--json-stream` | flag | off | Eventi NDJSON (`progress`/`log`/`result`/`error`). |
| `--dry-run` | flag | off | Piano e stima (token, costo, durata) senza tradurre. |
| `--describe` | flag | — | Manifest di tool/risorse/prompt (stesso registro MCP) ed esce. |
| `--mcp` | flag | off | Avvia il **server MCP** su stdio. |
| `--root DIR` | percorso (ripetibile) | cwd | Con `--mcp`: directory consentite per lettura/scrittura. |
| `--read-only` | flag | off | Con `--mcp`: vieta ogni scrittura. |
| `--cache-dir DIR` | percorso | temp di sistema | Cache stabile (usata anche per la ripresa). |
| `--config-dir DIR` | percorso | `~/.config/...` | Config isolata (isola anche la cache). |
| `--verbose`, `--max-output N` | — | off / 20000 | Log debug su stderr e limite caratteri dei tool di testo. |

> `--export-format` viene validato in base a `--export-only`: per i capitoli
> (`epub/html/md/txt`), per le figure (`img/html/md`) e per le tabelle
> (`csv/html/md`). I formati non validi per il tipo scelto producono un errore
> esplicito.

---

## Interfaccia TUI (`-gui`)

Se preferisci un'interfaccia guidata alla riga di comando, lancia la **TUI**:

```bash
noesis-ebook-translator-engine -gui
```

Si apre una schermata Textual con: campo **EPUB**, scelta del **motore**, lingua
di **origine** e **destinazione**, **posizione della traduzione** (solo
traduzione / bilingue sotto / bilingue sopra), opzioni (*Usa cache*, *Batching
online*), campo **chiave API** e **modello**, pulsante **Translate**, barra di
avanzamento e log. Da tastiera: `Ctrl+R` per avviare, `?` per l'aiuto, `q` per
uscire.

La TUI **eredita gli argomenti della CLI**: input, output (`-o`), motore,
lingue, posizione, cache, batching, chiave e modello vengono precompilati.

```bash
noesis-ebook-translator-engine -gui libro.epub -t German --position below
```

Se Textual non è installato, lo stesso comando apre un wizard a righe con gli
stessi valori precompilati tra parentesi quadre.

Per la TUI moderna installa l'extra:

```bash
pip install -r requirements-tui.txt     # oppure: pip install ".[tui]"
```

**Compatibilità.** Se Textual non è installato il comando **non fallisce**:
`-gui` ripiega automaticamente su un **wizard a righe** che usa solo `input()`.

---

## Output

Il file tradotto viene salvato **accanto all'originale** (o dove indica
`-o`/`--output`), con il suffisso della lingua di destinazione in **maiuscolo**:

```text
libro.epub  ->  libro_ITALIAN.epub
```

Il nome deriva da `default_output_path`: `*_<LINGUA>.epub`. Con
`--position below`/`above` il file contiene **originale + traduzione**; con
`--position only` (default) contiene **solo la traduzione**.

> **Cache:** la cache delle parti già tradotte viene salvata in
> `~/.config/noesis-ebook-translator/` (override con `NOESIS_CONFIG_DIR`). Usa
> `--no-cache` per disattivarla.

---

## Agenti: CLI JSON e server MCP

Il motore può essere pilotato da un agente (Claude Desktop, Cursor, OpenCode,
uno script) in due modi complementari, senza dipendenze aggiuntive:

1. **CLI macchina-leggibile** — un processo per comando, output JSON su stdout e
   log su stderr;
2. **server MCP su stdio** — `--mcp`, JSON-RPC 2.0 una riga per messaggio, con
   tool, risorse, prompt, progresso e annullamento.

La guida di riferimento completa (contratto dei tool, risorse, prompt, job,
errori, ricette) è in [`docs/agenti-mcp-cli.md`](docs/agenti-mcp-cli.md).

### CLI JSON

```bash
# Cosa sa fare il motore (manifest dei tool, stesso registro del server MCP)
noesis-ebook-translator-engine --describe

# Piano completo: capitoli, segmenti, caratteri, token, costo, durata
noesis-ebook-translator-engine libro.epub --dry-run

# Traduzione: un solo oggetto JSON su stdout
noesis-ebook-translator-engine libro.epub -e DeepSeek --model deepseek-chat \
  -s English -t Italian --json

# Eventi NDJSON: progressi, log, risultato finale
noesis-ebook-translator-engine libro.epub -e ChatGPT --json-stream

# Riprendi l'ultima esecuzione interrotta (stesse lingue, motore e stile)
noesis-ebook-translator-engine libro.epub --resume

# Elenchi e anteprime in JSON
noesis-ebook-translator-engine --list-engines --json
noesis-ebook-translator-engine libro.epub --list-chapters --json
noesis-ebook-translator-engine libro.epub --preview 5 --json
```

Exit code: `0` ok, `1` errore, `2` uso scorretto, `130` annullato. In caso di
errore l'oggetto è `{"ok": false, "error": {"code", "message"}}`.

### Server MCP (`--mcp`)

#### Requisiti e avvio

Il server MCP è **lo stesso binario/comando** della CLI: non serve installare
nulla di aggiuntivo (`pip install mcp` serve solo al test di interoperabilità,
non a usare il server). Avvio manuale, solo per verifica:

```bash
noesis-ebook-translator-engine --mcp --root ~/Libri --cache-dir ~/.cache/noesis
```

Il server parla su **stdin/stdout**: non lanciarlo da un terminale interattivo
(lo rifiuta con exit 2). I client MCP lo avviano da soli.

#### Configurazione del client

Usa un **path assoluto** se il client non eredita il `PATH` (tipico delle app
grafiche su macOS/Windows), oppure `python` + il percorso del monofile se non
hai installato il comando.

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

Su Windows usa forward slash o doppio backslash, ad esempio
`"C:/Users/me/AppData/Local/Programs/noesis-ebook-translator-engine.exe"`;
con il binario portable il `command` è il percorso dell'`.exe`.

**Cursor** — `~/.cursor/mcp.json` (globale) o `.cursor/mcp.json` nel progetto,
stesso schema `mcpServers`.

**OpenCode** — `opencode.json` (progetto) o `~/.config/opencode/opencode.json`.
Lo schema è diverso: `command` è un array e l'ambiente si chiama `environment`.

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

**Altri client** — schema `mcpServers` con `command`/`args`/`env`, oppure
`command` come array se richiesto.

Dopo la modifica **riavvia il client**. Ogni client avvia un proprio processo
del server: la configurazione isolata (`NOESIS_CONFIG_DIR`) evita che più
sessioni si sovrappongano alla config del desktop.

#### Verifica

```bash
# 1) il comando esiste e il manifest è valido
noesis-ebook-translator-engine --describe | head

# 2) handshake manuale (NDJSON): initialize + tools/list
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"check","version":"1"}}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  | noesis-ebook-translator-engine --mcp --root .
```

Se il secondo messaggio elenca i tool, il server funziona. Se il client non lo
mostra: controlla il path assoluto del comando, la validità del JSON, che
`--root` contenga i libri e riavvia il client.

Tool esposti (i primi sono di sola lettura e non spendono nulla):

| Tool | Cosa fa |
|---|---|
| `capabilities` | versioni, root consentite, directory di cache/config, limiti, schema impostazioni |
| `list_engines` | motori, modelli, requisiti di chiave, supporto prompt/reasoning |
| `inspect_book` | metadati + TOC + segmenti/caratteri + copertura cache + run interrotte |
| `list_chapters`, `read_chapter` | indice dei capitoli e testo paginato (con `offset`/`limit`) |
| `plan_translation` | segmenti, token stimati, **costo USD**, durata misurata |
| `preview_translation` | traduce 1–50 segmenti per saggiare tono e qualità (rete, nessuna scrittura) |
| `cache_status`, `interrupted_runs` | copertura della cache e run da riprendere |
| `start_translation` | job asincrono (`job_id`) con `wait_seconds` opzionale e progresso |
| `job_status`, `collect_job`, `cancel_job` | polling incrementale, attesa, annullamento conservando la cache |
| `export_book` | capitoli (`epub/html/md/txt/json/csv/docx/pdf`), figure e tabelle |
| `dismiss_interrupted_run` | non offrire più una run interrotta (non cancella le traduzioni) |
| `configure_engine` | salva modello/chiave nella config del server (opt-in) |

Sono disponibili anche risorse (`noesis://capabilities`, `noesis://engines`,
`noesis://book/<id>[/toc|/chapter/<n>]`) e prompt di workflow
(`translate_book`, `review_translation`).

**Sicurezza.** Con `--mcp` i percorsi sono confinati alle `--root` indicate
(realpath, niente escape via symlink), `--read-only` vieta ogni scrittura,
le chiavi si leggono dall'ambiente o da una config isolata
(`NOESIS_CONFIG_DIR`) e il testo dei libri è marcato come **dato non
attendibile**: un agente non deve eseguire istruzioni trovate dentro un EPUB.
Un solo job di traduzione alla volta: il secondo `start_translation` risponde
`busy`.

**Protocollo.** Nessun SDK: il server implementa il sottoinsieme MCP necessario
(versione `2025-06-18`, accettando anche `2025-03-26` e `2024-11-05`) con
framing NDJSON su stdio. La suite si valida contro il **client ufficiale**
(`pip install mcp`, test `tests/test_mcp_interop.py`, saltato se assente).

---

## Build delle release

Le release standalone sono compilate con **PyInstaller** su runner nativi
(PyInstaller non fa cross-compile):

| Target | Runner | Artefatto |
| --- | --- | --- |
| Windows x64 | `windows-latest` | `.exe` + installer **NSIS** (`installer.nsi`) |
| Linux x64 | `ubuntu-latest` | **AppImage** (`noesis-ebook-translator-engine-x86_64.AppImage`) |
| macOS x86_64 | `macos-15-intel` | `.dmg` |
| macOS Apple Silicon (arm64) | `macos-15` | `.dmg` |

Il workflow `.github/workflows/release.yml` parte manualmente da
**Actions → build-releases → Run workflow** oppure al push di un tag `v*`
(es. `git tag v2.5.0 && git push --tags`), creando una **GitHub Release** con gli
artefatti e `SHA256SUMS.txt`. Essendo un'app **da console**, il build
PyInstaller **non** usa `--windowed`.

Nomi degli asset della release:

```text
noesis-ebook-translator-engine-windows-x64.exe
noesis-ebook-translator-engine-windows-x64-setup.exe
noesis-ebook-translator-engine-macos-x64.dmg
noesis-ebook-translator-engine-macos-arm64.dmg
noesis-ebook-translator-engine-x86_64.AppImage
SHA256SUMS.txt
```

La versione `2.5.0` è quella di questa edizione. Il **motore verbatim** resta
quello del desktop `0.10.0`; la `2.5.0` aggiunge il livello agenti (MCP + CLI
JSON), la documentazione e i test end-to-end.

### Build locale (opzionale)

```bash
.venv/bin/pip install pyinstaller
.venv/bin/pyinstaller --onefile --clean --noconfirm \
  --name noesis-ebook-translator-engine \
  --collect-all textual noesis_ebook_translator_engine.py
```

---

## Come è costruito

Il repository desktop `../noesis-ebook-translator` è la **fonte di verità** del
motore. Qui **non** si modifica a mano il file generato: si sincronizza.

```bash
python tools/sync_from_desktop.py
python tools/sync_from_desktop.py --desktop /percorso/noesis-ebook-translator
```

Lo script:

1. inlinea i moduli del motore (`lib/` + `engines/`, più `appconfig.py` e
   `book.py`) in un unico file, rimuovendo gli import da `calibre` e quelli
   relativi;
2. appende il **livello agenti** (`tools/agent.py`, scritto a mano): AgentAPI,
   job runner e server MCP;
3. appende il **front-end CLI/TUI** (`tools/frontend.py`, scritto a mano);
4. registra la provenienza (commit desktop) in `ENGINE_SOURCE.json`.

```bash
python tools/sync_from_desktop.py && python -m unittest discover -s tests
```

Dettagli nel file [`AGENTS.md`](AGENTS.md).

---

## Test e CI

```bash
pip install -r requirements.txt -r requirements-tui.txt
python -m unittest discover -s tests -v
```

La suite include:

- **end-to-end della CLI** su EPUB sintetici con un **motore fittizio offline**
  (nessuna rete): traduzione mono-lingua, bilingue (`--position below`),
  percorso di output di default;
- **smoke test del motore** generato;
- **test della TUI** che pilotano l'app Textual *reale* headless (si saltano se
  Textual non è installato);
- **agenti**: AgentAPI, protocollo MCP in memoria, sessione stdio reale in un
  sottoprocesso e contratto `--json`/`--json-stream`/`--describe`
  (`tests/test_agent_api.py`, `tests/test_mcp_protocol.py`,
  `tests/test_mcp_stdio.py`, `tests/test_cli_json.py`);
- **interoperabilità** con il client MCP ufficiale
  (`tests/test_mcp_interop.py`, si salta se `mcp` non è installato);
- **workflow E2E su testo Rosen** (`scripts/e2e/`): dieci scenari agenti
  (ispezione, piano, traduzione mono/bilingue **di un solo capitolo**, job,
  cancel+resume, export, MCP stdio in sottoprocesso) con motori finti offline.
  Vedi [`scripts/e2e/README.md`](scripts/e2e/README.md).
- **parità di sorgente** con il checkout desktop
  (`tests/test_sync_parity.py`, si salta se il repo desktop non è presente);
- **corpus Project Gutenberg**: **13 libri reali** (Project Gutenberg, pubblico
  dominio, edizione `.epub.images`) in `tests/data/corpus/` — vedi
  `tests/data/corpus/SOURCE.md`. **10** hanno **TOC multilivello e illustrazioni**
  (trattati, manuali, testi scientifici). Le fixture sono **copiate dal repo
  desktop** da `tools/sync_from_desktop.py`. I test end-to-end verificano
  **testo, link, illustrazioni e profondità del TOC**; con `NOESIS_ONLINE_TESTS=1`
  si aggiunge un test reale con Google.

La CI (`.github/workflows/tests.yml`) gira su `ubuntu-latest` (Python 3.12) su
ogni push e PR: installa `requirements.txt` + `requirements-tui.txt` ed esegue
l'intera suite. Due job aggiuntivi validano il server MCP contro il **client
ufficiale** (`mcp`) e lanciano i **dieci workflow E2E** con il corpus di
fallback (il libro Rosen non è in CI).

---

## Licenza

**GNU General Public License v3.0** (o successive) — vedi [LICENSE](LICENSE).

Quest'opera deriva dal plugin **Ebook Translator** di **bookfere**, distribuito
sotto la stessa licenza GPLv3; gli engine e la gestione degli elementi sono copie
verbatim dell'upstream. Se ridistribuisci o modifichi il progetto, mantieni
l'attribuzione a bookfere e la licenza GPLv3.
