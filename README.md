# Noesis Ebook Translator — Engine (CLI + TUI)

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
appende il front-end CLI/TUI (`tools/frontend.py`).

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

### A) Con un ambiente virtuale (consigliato)

```bash
python3 -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python noesis_ebook_translator_engine.py --help
```

### B) Come comando installato

```bash
pip install .
noesis-ebook-translator-engine --version
```

Dopo l'installazione il comando `noesis-ebook-translator-engine` è disponibile
ovunque.

Per includere anche la **TUI** (`-gui`) installa l'extra `tui`:

```bash
pip install ".[tui]"                    # oppure: pip install -r requirements-tui.txt
noesis-ebook-translator-engine -gui
```

### C) Senza installare nulla (uso dal checkout)

```bash
python noesis_ebook_translator_engine.py libro.epub
```

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
| `--batch` | flag | off | Abilita il **batching online** delle richieste. |
| `--no-cache` | flag | off | Disabilita la **cache** su disco. |
| `--api-key KEY` | stringa | — | Chiave API per il motore scelto (se richiesta). |
| `--model NAME` | stringa | — | Modello del motore scelto (per gli LLM). |
| `-gui`, `--gui` | flag | off | Avvia la **TUI** interattiva (o il wizard a righe). |
| `--list-engines` | flag | — | Elenca i motori disponibili ed esce. |
| `--version` | flag | — | Stampa la versione ed esce. |

---

## Interfaccia TUI (`-gui`)

Se preferisci un'interfaccia guidata alla riga di comando, lancia la **TUI**:

```bash
noesis-ebook-translator-engine -gui
```

Si apre una schermata Textual con: campo **EPUB**, scelta del **motore**, lingua
di **origine** e **destinazione**, opzioni (*Testo bilingue*, *Usa cache*,
*Batching online*), campo **chiave API** e **modello**, pulsante **Translate**,
barra di avanzamento e log. Da tastiera: `Ctrl+R` per avviare, `q` per uscire.

```bash
noesis-ebook-translator-engine -gui libro.epub -t German   # precompila l'input
```

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
(es. `git tag v2.4.2 && git push --tags`), creando una **GitHub Release** con gli
artefatti. Essendo un'app **da console**, il build PyInstaller **non** usa
`--windowed`.

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
2. appende il **front-end CLI/TUI** (`tools/frontend.py`, scritto a mano);
3. registra la provenienza (commit desktop) in `ENGINE_SOURCE.json`.

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
- **parità di sorgente** con il checkout desktop
  (`tests/test_sync_parity.py`, si salta se il repo desktop non è presente);
- **corpus Darwin**: tre libri reali di **Charles Darwin** (Project Gutenberg,
  pubblico dominio) in `tests/data/darwin/` — vedi
  `tests/data/darwin/SOURCE.md`. Le fixture sono **copiate dal repo desktop** da
  `tools/sync_from_desktop.py`. I test end-to-end le traducono con il motore
  fittizio; con `NOESIS_ONLINE_TESTS=1` si aggiunge un test reale con Google.

La CI (`.github/workflows/tests.yml`) gira su `ubuntu-latest` (Python 3.12) su
ogni push e PR: installa `requirements.txt` + `requirements-tui.txt` ed esegue
l'intera suite.

---

## Licenza

**GNU General Public License v3.0** (o successive) — vedi [LICENSE](LICENSE).

Quest'opera deriva dal plugin **Ebook Translator** di **bookfere**, distribuito
sotto la stessa licenza GPLv3; gli engine e la gestione degli elementi sono copie
verbatim dell'upstream. Se ridistribuisci o modifichi il progetto, mantieni
l'attribuzione a bookfere e la licenza GPLv3.
