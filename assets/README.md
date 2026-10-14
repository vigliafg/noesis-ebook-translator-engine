# assets

Risorse grafiche di **Noesis Ebook Translator — Engine** (CLI + TUI).

## File attesi

| File | Formato | Piattaforma | Note |
| --- | --- | --- | --- |
| `noesis-ebook-translator-engine.png` | PNG 256×256 | Linux / AppImage | **presente** (placeholder) |
| `noesis-ebook-translator-engine.ico` | ICO multi-risoluzione | Windows (PyInstaller + NSIS) | da aggiungere prima della release |
| `noesis-ebook-translator-engine.icns` | ICNS | macOS (PyInstaller) | da aggiungere prima della release |

Le **icone reali** (`.ico` e `.icns`) verranno inserite **prima della release**:
i workflow di build le referenziano, ma se assenti il build ripiega senza icona
(vedi `.github/workflows/release.yml`).

Il `noesis-ebook-translator-engine.png` attualmente presente è un **placeholder**
generato automaticamente (256×256, sfondo blu scuro con un glifo "libro"):
serve a far girare build e AppImage finché non arriva l'icona definitiva.
Per rigenerarlo basta un PNG valido 256×256 con lo stesso nome.

## Uso nelle build

- **Windows** — `--icon assets/noesis-ebook-translator-engine.ico` (PyInstaller)
  e `!define MUI_ICON "assets\noesis-ebook-translator-engine.ico"`
  (`installer.nsi`).
- **macOS** — `--icon assets/noesis-ebook-translator-engine.icns` (PyInstaller).
- **Linux / AppImage** — `assets/noesis-ebook-translator-engine.png` copiato
  nell'AppDir come `noesis-ebook-translator-engine.png`.
