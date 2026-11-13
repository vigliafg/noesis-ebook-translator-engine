# E2E workflows — Rosen

Dieci workflow end-to-end che usano **lo stesso percorso di un agente**
(CLI `--json`, AgentAPI, tool MCP) su testo medico reale: i capitoli di
*Rosen's Emergency Medicine, 10th ed. (2023, SLIM)* presenti nel repository
padre in `../noesis-ebook-translator/corpus1/`.

Sono **offline e deterministici**: nessuna API key, nessuna chiamata di rete,
nessun costo. Il harness registra due motori finti (`E2E`, `E2E-Slow`) come fa
`tests/fixtures.py`; la traduzione "vera" del testo Rosen è quindi simulata ma
tutto il resto — parsing EPUB, capitoli, cache, job, export, protocollo — è il
codice di produzione.

## Avvio

```bash
# tutti e dieci i workflow
python scripts/e2e/run_all.py

# uno o più workflow (match sul nome del file)
python scripts/e2e/run_all.py --only wf05 --only wf10 --verbose

# un singolo script, con workspace temporaneo dedicato
python scripts/e2e/wf08_cancel_resume.py --verbose

# elenco
python scripts/e2e/run_all.py --list
```

Opzioni: `--book PATH` (un altro EPUB), `--keep` (tiene i workspace temporanei
per ispezionarli), `--force-sample` (rigenera il campione), `--verbose`.

Il primo avvio deriva un **campione** di circa 50 000 caratteri dai capitoli
Rosen *Airway*, *Management*, *Mechanical Ventilation*, *Management*, *Shock*:
un EPUB di poche centinaia di KB con 5 capitoli, una tabella e una figura. Senza
questo passaggio ogni workflow leggerebbe i 125 MB / 36 MB di testo del libro
completo. Il campione è messo in cache in `scripts/e2e/.cache/` (ignorata da
git) e viene ricostruito se il sorgente cambia.

Le run di **traduzione** restano comunque su **un solo capitolo** (il più ricco,
~250 segmenti): l'intero libro non viene mai tradotto, nemmeno nel campione.
Gli altri workflow (piano, ispezione, selezione) leggono il campione intero
perché sono operazioni di sola lettura.

Se il repository desktop non è presente, il harness ripiega su
`tests/data/corpus/descent_of_man.epub` (con un avviso): i workflow restano
eseguibili, ma perdono i capitoli Rosen e le verifiche su tabella/figure.

## I dieci workflow

| # | Script | Cosa verifica |
|---|---|---|
| 01 | `wf01_inspect.py` | `capabilities`, catalogo motori, `inspect_book`, TOC contiguo 1-based, lettura capitolo paginata, cache vuota |
| 02 | `wf02_plan.py` | piano intero e per capitolo, risoluzione **titolo → indice**, costo/token, parità con `--dry-run`, errore `not_found` |
| 03 | `wf03_translate_mono.py` | traduzione di **un capitolo** via `--json`, path di output, marker, testo sorgente conservato, metadati, EPUB valido |
| 04 | `wf04_translate_bilingual.py` | `--position below` su **un capitolo**: originale + traduzione, file bilingue più lungo del mono |
| 05 | `wf05_chapter_job.py` | job MCP con `wait_seconds`, **un solo capitolo** nell'output, capitolo tradotto |
| 06 | `wf06_chapter_selection.py` | titolo unico case/space-insensitive, titolo **ambiguo** → `ambiguous`, capitolo inesistente → `not_found`, nessun file vuoto |
| 07 | `wf07_job_lifecycle.py` | start non bloccante su **un capitolo**, eventi `plan`/`progress` con cursore, `collect_job`, regola **un job alla volta** (`busy`), cancel |
| 08 | `wf08_cancel_resume.py` | cancel a metà di **un capitolo**, cache conservata, marker di crash, `interrupted_runs`, `--resume` che riusa motore/output/capitolo e completa al 100% |
| 09 | `wf09_export.py` | export md/txt del capitolo tradotto, tabella CSV e figura PNG estratti dal testo Rosen |
| 10 | `wf10_mcp_stdio.py` | **sottoprocesso** `--mcp`: sessione read-only (initialize, tools, inspect, read, plan, resources, prompts) e **traduzione + export via stdio** con il wrapper offline |

## Struttura

- `harness.py` — caricamento del monofile, motori finti, derivazione del
  campione, workspace isolato (config + cache + output), helper `mcp()`,
  `cli()`, `read_json()`, `simulate_crash()`.
- `wf*.py` — un file per workflow, eseguibile anche da solo.
- `run_all.py` — esecuzione sequenziale, riepilogo e exit code.

Ogni workflow riceve un **workspace nuovo**: copia del libro, `config_dir`,
`cache_path` e cartella di output dedicati, con root confinement attivo. Non
tocca mai la configurazione o la cache reali dell'utente.

Exit code: `0` tutti verdi, `1` almeno un fallimento (con traceback).
