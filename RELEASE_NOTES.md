# Noesis Ebook Translator Engine 2.4.2

Edizione **CLI + TUI** del motore di [Noesis Ebook Translator](https://github.com/vigliafg/noesis-ebook-translator).
La versione `2.4.2` è quella dell'**engine** (la stessa incorporata nel desktop
`0.10.0`), non quella dell'app desktop.

## Novità

- **`-gui` ora eredita davvero gli argomenti della CLI**: input, `-o`, motore,
  lingue, posizione, cache, batching, chiave e modello vengono precompilati
  (prima venivano ignorati).
- **Posizione della traduzione** selezionabile nella TUI: solo traduzione,
  bilingue sotto o bilingue sopra.
- **Aiuto in TUI** con `?`; restano `Ctrl+R` per avviare e `q` per uscire.
- **Test** headless della TUI per precompilazione, widget e passaggio argomenti.
- **Release complete**: installer Windows (NSIS), AppImage, DMG macOS,
  `SHA256SUMS.txt`; icona `.ico` inclusa.

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
./noesis-ebook-translator-engine --version   # v2.4.2
./noesis-ebook-translator-engine --help
./noesis-ebook-translator-engine --list-engines
```

## Requisiti

- Windows 10+, macOS 12+, oppure Linux x86_64.
- Textual è incluso nei bundle; senza Textual `-gui` usa il wizard a righe.
- I motori LLM richiedono una chiave API (BYOK).

Vedi il [README](https://github.com/vigliafg/noesis-ebook-translator-engine#readme)
per l'elenco completo delle opzioni e dei motori.
