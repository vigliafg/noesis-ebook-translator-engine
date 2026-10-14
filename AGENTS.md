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
   `bookfere/Ebook-Translator-Calibre-Plugin`;
2. li **inlinea** in un unico file, rimuovendo gli import da `calibre` e gli
   import relativi (`from .` / `from ..`);
3. appende il **front-end CLI/TUI** da `tools/frontend.py` (questo sì scritto a
   mano, ma in un file separato);
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
(`desktop_commit`), l'elenco dei moduli **verbatim** e l'**override** locale
(`engines/__init__.py`), oltre al percorso del front-end (`tools/frontend.py`).

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
  ripiego (`_fallback_wizard()`).

## Convenzioni del repo

- Il motore inlineato dipende da `ebooklib`, `lxml`, `mechanize`, `cssselect`;
  la TUI da `textual`. Vedi `requirements.txt` e `requirements-tui.txt`.
- Il file è un **modulo flat a un solo file**: `pyproject.toml` lo dichiara in
  `[tool.setuptools] py-modules`.
- Comandi utili: `python noesis_ebook_translator_engine.py --help`,
  `... --list-engines`, `... -gui`,
  `python -m unittest discover -s tests -v`.
- La CI headless sta in `.github/workflows/tests.yml`; le release in
  `.github/workflows/release.yml` (PyInstaller + NSIS/AppImage/.dmg).

## File da NON toccare senza motivo

- `noesis_ebook_translator_engine.py` — **generato**: passa da
  `tools/sync_from_desktop.py`.
- `tools/sync_from_desktop.py`, `tools/frontend.py` — motore di sincronizzazione
  e front-end (modificali, poi risincronizza).
- `ENGINE_SOURCE.json` — manifest di provenienza (riscritto dal sync).
- `.venv/` — ambiente virtuale locale.
