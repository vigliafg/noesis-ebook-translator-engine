# assets

Risorse grafiche di **Noesis Ebook Translator — Engine** (CLI + TUI).

## File attesi

| File | Formato | Piattaforma | Note |
| --- | --- | --- | --- |
| `noesis-ebook-translator-engine.png` | PNG 256×256 | Linux / AppImage | **presente** (placeholder) |
| `noesis-ebook-translator-engine.ico` | ICO multi-risoluzione | Windows (PyInstaller + NSIS) | **presente** (7 risoluzioni, generato dal PNG) |
| `noesis-ebook-translator-engine.icns` | ICNS | macOS (PyInstaller) | opzionale (se assente il build ripiega) |

Il file `.ico` è incluso (generato dal PNG); `.icns` è opzionale. Se un formato
manca, il workflow di build ripiega senza icona (vedi
`.github/workflows/release.yml`).

Il `noesis-ebook-translator-engine.png` è un **placeholder**
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
