# Istruzioni per l'agente — noesis-ebook-translator-engine (CLI + TUI)

## Relazione con il repository desktop

Questo repository è l'edizione **da riga di comando** di
`../noesis-ebook-translator` (app desktop con GUI). **Non possiede un motore
proprio**: usa lo **stesso motore** del desktop, copiato **verbatim**.

Il repository desktop è la **fonte di verità**. Qui il motore viene **inlineato
in un unico file generato**, `noesis_ebook_translator_engine.py`, insieme al
front-end CLI/TUI.

## Il file generato non si modifica a mano

`noesis_ebook_translator_engine.py` è **AUTOGENERATO** da
`tools/sync_from_desktop.py`. **Non** editarlo a mano: ogni modifica andrebbe
persa al successivo sync. Lo script:

1. legge i moduli del motore dal desktop
   (`noesis_ebook_translator/lib/`, `.../engines/*.py`, `.../appconfig.py`,
   `.../book.py`), copiati verbatim dal fork **GPLv3** del plugin Calibre
   `bookfere/Ebook-Translator-Calibre-Plugin`, più le **estensioni locali**
   condivise `engines/openai_compatible.py` e `provider_catalog.py` (trasporto
   generico OpenAI-compatible + catalogo provider curati: non esistono nel fork);
2. li **inlinea** in un unico file, rimuovendo gli import da `calibre` e gli
   import relativi (`from .` / `from ..`);
3. appende il **livello agenti** (`tools/agent.py`: AgentAPI, job runner, server
   MCP stdio) e poi il **front-end CLI/TUI** (`tools/frontend.py`), questo sì
   scritto a mano, ma in file separati;
4. registra la provenienza in `ENGINE_SOURCE.json`.

Per cambiare il motore: modifica il **desktop**, poi risincronizza qui. Per
cambiare la CLI/TUI: modifica `tools/frontend.py`, poi risincronizza.

## Flusso di sincronizzazione

```bash
python tools/sync_from_desktop.py
python -m unittest discover -s tests
```

In una riga:

```bash
python tools/sync_from_desktop.py && python -m unittest discover -s tests
```

Opzioni utili:

```bash
python tools/sync_from_desktop.py --desktop /percorso/noesis-ebook-translator
```

## Provenienza e contratto di parità

`ENGINE_SOURCE.json` registra il **commit desktop** di provenienza
(`desktop_commit`), l'elenco dei moduli **verbatim**, l'**override** locale
(`engines/__init__.py`) e le **estensioni** locali (`extensions`), oltre ai
percorsi dei blocchi scritti a mano (`agent`, `frontend`).

Lo script copia anche il **corpus di test** dal desktop
(`tests/data/corpus/`, `fixtures` in `ENGINE_SOURCE.json`): le fixture reali
(Project Gutenberg, illustrate e con TOC multilivello) devono restare identiche
nei due repo.

`tests/test_sync_parity.py` rigenera il testo atteso con
`sync.build_text(DESKTOP)` e verifica che il file generato sia **byte-identico**;
**fallisce se è stale** (ricorda di lanciare `tools/sync_from_desktop.py`). Il
test si **salta** quando il checkout desktop non è presente (tipicamente in CI,
dove viene clonato solo questo repository). Verifica anche il manifest
`ENGINE_SOURCE.json`.

## Il front-end

Il front-end **CLI/TUI** vive in `tools/frontend.py` e viene **appeso in coda**
al monofile dallo script di sync. Contiene:

- il parsing degli argomenti e `main()` (entry point:
  `python noesis_ebook_translator_engine.py`);
- `run_cli()` e l'helper `_build_settings()`;
- `_print_engine_list()` (per `--list-engines`);
- la TUI Textual (`_make_tui_app()`, `run_tui()`) e il wizard a righe di
  ripiego (`_fallback_wizard()`);
- le modalità macchina `--json`, `--json-stream`, `--dry-run`, `--describe`,
  che delegano all'AgentAPI.

## Il livello agenti

`tools/agent.py` è **scritto a mano** e viene appeso **tra il motore e il
front-end** (il front-end usa `serve_mcp` e l'AgentAPI). Contiene:

- **AgentAPI** (`agent_*`): `capabilities`, `list_engines`, `inspect_book`,
  `list_chapters`, `read_chapter`, `plan_translation`, `preview_translation`,
  `cache_status`, `interrupted_runs`, `export_book`, `translate_now`;
- **Job runner** (`AgentJob`, `_JOBS`): un solo job alla volta, eventi
  incrementali, annullamento via `should_cancel`, ripresa dalla cache;
- **server MCP stdio** (`serve_mcp`, `_mcp_dispatch`): JSON-RPC 2.0 con
  **framing NDJSON** (una riga per messaggio; il Content-Length è accettato solo
  in lettura per tolleranza), tool/risorse/prompt, `notifications/progress` e
  `notifications/cancelled`;
- **policy** su path (`--root`), `--read-only`, isolamento `--config-dir` /
  `--cache-dir`.

Regole:

- **zero dipendenze**: non importare l'SDK `mcp` nel codice di produzione; il
  pacchetto serve solo al test di interoperabilità
  (`tests/test_mcp_interop.py`, che si salta se manca);
- stdout è **riservato al protocollo**: `serve_mcp` duplica `fd 1` e dirotta
  `sys.stdout` su stderr; non aggiungere `print()` nel percorso dei tool;
- stdout non deve contenere altro: niente banner, progress bar o log (vanno su
  stderr o negli eventi del job).
- La guida pubblica per chi integra un agente è `docs/agenti-mcp-cli.md`
  (contratto CLI/MCP, configurazione client, ricette, errori).

## Script E2E (Rosen)

`scripts/e2e/` contiene **dieci workflow end-to-end** che usano la CLI JSON,
l'AgentAPI e i tool MCP come farebbe un agente, su testo medico reale:

- sorgente: `../noesis-ebook-translator/corpus1/Rosen's Emergency Medicine 10ed
  2023 SLIM.epub` (override `--book` o `NOESIS_E2E_BOOK`); se manca, fallback
  su `tests/data/corpus/descent_of_man.epub`;
- il libro completo (125 MB, 1306 voci) viene ridotto a un campione di ~50k
  caratteri, 5 capitoli, 1 tabella e 1 figura, derivato con gli estrattori del
  motore e messo in cache in `scripts/e2e/.cache/` (ignorata da git);
- le run di **traduzione** restano su **un solo capitolo** (~250 segmenti):
  l'intero libro non viene mai tradotto, nemmeno nel campione;
- traduzione **offline e deterministica** con i motori finti `E2E` / `E2E-Slow`
  (stesso principio di `tests/fixtures.py`): nessuna API key e nessuna rete;
- ogni workflow ha un workspace isolato (libro, config, cache, output) e non
  tocca mai la configurazione reale.

```bash
python scripts/e2e/run_all.py
python scripts/e2e/run_all.py --only wf05 --only wf10 --verbose
python scripts/e2e/wf08_cancel_resume.py --keep
python scripts/e2e/run_all.py --list
```

Dettagli e tabella dei dieci scenari in `scripts/e2e/README.md`.

## Convenzioni del repo

- Il motore inlineato dipende da `ebooklib`, `lxml`, `mechanize`, `cssselect`;
  la TUI da `textual`. Vedi `requirements.txt` e `requirements-tui.txt`.
- Il file è un **modulo flat a un solo file**: `pyproject.toml` lo dichiara in
  `[tool.setuptools] py-modules`.
- Comandi utili: `python noesis_ebook_translator_engine.py --help`,
  `... --list-engines`, `... --describe`, `... --mcp`,
  `python -m unittest discover -s tests -v`.
- Il test di interoperabilità MCP (`tests/test_mcp_interop.py`) richiede l'SDK
  ufficiale solo nell'ambiente di test: `pip install mcp` (in CI c'è un job
  dedicato). Non è una dipendenza runtime.
- La CI headless sta in `.github/workflows/tests.yml`; le release in
  `.github/workflows/release.yml` (PyInstaller + NSIS/AppImage/.dmg).

## File da NON toccare senza motivo

- `noesis_ebook_translator_engine.py` — **generato**: passa da
  `tools/sync_from_desktop.py`.
- `tools/sync_from_desktop.py`, `tools/frontend.py`, `tools/agent.py` — motore
  di sincronizzazione, front-end e livello agenti (modificali, poi
  risincronizza).
- `ENGINE_SOURCE.json` — manifest di provenienza (riscritto dal sync).
- `.venv/` — ambiente virtuale locale.
