# Noesis Ebook Translator Engine 2.5.0

Edizione **CLI + TUI** del motore di
[Noesis Ebook Translator](https://github.com/vigliafg/noesis-ebook-translator),
ora utilizzabile anche come **tool agentico** via **MCP (stdio)** e **CLI JSON**.

La `2.5.0` è la versione di questa edizione. Il **motore di traduzione**
verbatim è invariato rispetto alla `2.4.2` (stesso commit del desktop `0.10.0`);
questa release aggiunge il livello agenti, la documentazione e i test
end-to-end.

## Novità principali

### Server MCP su stdio (zero dipendenze)

- `--mcp`: server JSON-RPC 2.0 su stdio con framing **NDJSON** (una riga per
  messaggio), compatibile con Claude Desktop, Cursor, OpenCode e qualsiasi
  client MCP.
- **16 tool**: `capabilities`, `list_engines`, `inspect_book`, `list_chapters`,
  `read_chapter`, `plan_translation`, `preview_translation`, `cache_status`,
  `interrupted_runs`, `start_translation`, `job_status`, `collect_job`,
  `cancel_job`, `export_book`, `dismiss_interrupted_run`, `configure_engine`.
- **Risorse**: `noesis://capabilities`, `noesis://engines`,
  `noesis://book/<id>[/toc|/chapter/<n>]`.
- **Prompt**: `translate_book`, `review_translation`.
- **Job**: avvio non bloccante, `wait_seconds`, eventi incrementali con cursore,
  `notifications/progress`, `notifications/cancelled`, ripresa dalla cache.
- **Protocollo**: `2025-06-18` (default), `2025-03-26`, `2024-11-05`;
  validato contro il **client MCP ufficiale** (`mcp`).

### CLI per agenti

- `--json`: un solo documento JSON su stdout (log su stderr).
- `--json-stream`: eventi NDJSON `progress` / `log` / `result` / `error`.
- `--describe`: manifest di tool/risorse/prompt, identico a `tools/list`.
- `--dry-run`: segmenti, caratteri, token, **costo USD** e durata senza
  tradurre né scrivere.
- `--resume`: riprende la run interrotta più recente, riusando motore, lingue,
  capitoli, stile e **path di output**.
- Nuovi `--style`, `--genre`, `--cache-dir`, `--config-dir`, `--mcp`,
  `--root`, `--read-only`, `--verbose`, `--max-output`.
- Selezione capitoli per indice, range, href/file o **titolo unico**; un titolo
  ambiguo o inesistente è un errore esplicito, mai un EPUB vuoto.

### Sicurezza

- Con `--mcp` i percorsi sono confinati alle `--root` (realpath, niente escape
  via symlink); `--read-only` vieta ogni scrittura.
- Un solo job alla volta per processo; un secondo `start_translation` risponde
  `busy`.
- Chiavi API da ambiente o da configurazione isolata (`NOESIS_CONFIG_DIR`); il
  testo dei libri è marcato come **dato non attendibile** (prompt injection).
- `--config-dir` isola configurazione **e** cache, senza toccare il desktop.

### Documentazione

- Nuova guida completa
  [`docs/agenti-mcp-cli.md`](https://github.com/vigliafg/noesis-ebook-translator-engine/blob/v2.5.0/docs/agenti-mcp-cli.md):
  contratto CLI/MCP, tool, risorse, prompt, job, errori, sicurezza, ricette.
- README ampliato: installazione da binari precompilati, verifica, setup dei
  client MCP (Claude Desktop, Cursor, OpenCode) con path e schema corretti.
- `AGENTS.md` aggiornato con il livello agenti e gli script E2E.

### Test e CI

- **88 test** (4 skip condizionali): AgentAPI, protocollo MCP in memoria,
  sessione stdio in sottoprocesso, contratto CLI JSON, parity del sync.
- **Interoperabilità** con il client MCP ufficiale (`tests/test_mcp_interop.py`).
- **10 workflow end-to-end** su testo medico reale
  (`scripts/e2e/`, capitoli di *Rosen's Emergency Medicine*): ispezione, piano,
  traduzione mono/bilingue di **un solo capitolo**, job, cancel/resume, export,
  sessione MCP stdio completa.
- Nuovi job CI `mcp-interop` ed `e2e-workflows` (fallback offline al corpus).

### Correzioni

- `--resume` ora riusa anche il path di output della run interrotta.
- Una selezione capitoli che non corrisponde a nulla produce `not_found`
  invece di un output vuoto.
- I capitoli si possono indicare per titolo, con gestione esplicita
  dell'ambiguità.

## Compatibilità

- CLI e TUI esistenti restano compatibili: i nuovi flag sono additivi.
- Configurazione e cache esistenti restano valide.
- Nessuna dipendenza runtime aggiuntiva: il server MCP usa solo la libreria
  standard. `pip install mcp` serve esclusivamente ai test di interoperabilità.
- Python 3.10+; Textual incluso nei bundle (senza Textual `-gui` usa il wizard a
  righe).

## Asset

| Piattaforma | File |
| --- | --- |
| Windows x64 | `noesis-ebook-translator-engine-windows-x64.exe` |
| Windows x64 (installer) | `noesis-ebook-translator-engine-windows-x64-setup.exe` |
| Linux x86_64 | `noesis-ebook-translator-engine-x86_64.AppImage` |
| macOS x86_64 | `noesis-ebook-translator-engine-macos-x64.dmg` |
| macOS arm64 | `noesis-ebook-translator-engine-macos-arm64.dmg` |
| Integrità | `SHA256SUMS.txt` |

## Verifica

```bash
sha256sum -c SHA256SUMS.txt
./noesis-ebook-translator-engine --version     # v2.5.0
./noesis-ebook-translator-engine --describe    # manifest agenti/MCP
./noesis-ebook-translator-engine --mcp --help
```

Handshake MCP manuale:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"check","version":"1"}}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  | ./noesis-ebook-translator-engine --mcp --root .
```

Configurazione client (Claude Desktop, Cursor, OpenCode) e guida completa in
[`docs/agenti-mcp-cli.md`](https://github.com/vigliafg/noesis-ebook-translator-engine/blob/v2.5.0/docs/agenti-mcp-cli.md).

## Requisiti

- Windows 10+, macOS 12+, oppure Linux x86_64.
- I motori LLM richiedono una chiave API (BYOK).
- Nessun runtime aggiuntivo per MCP: `--mcp` è nel binario.

Vedi il [README](https://github.com/vigliafg/noesis-ebook-translator-engine#readme)
per l'elenco completo delle opzioni, dei motori e dei workflow.
