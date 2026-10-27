# ═══════════════════════════════════════════════════════════════════════════════
#  FRONT-END — CLI + TUI (hand-written, appended by tools/sync_from_desktop.py)
#
#  This block is *not* generated: it is kept verbatim from tools/frontend.py and
#  is what turns the inlined engine above into a command-line / terminal app.
# ═══════════════════════════════════════════════════════════════════════════════

import argparse
import threading


# ---------------------------------------------------------------- CLI helpers
def _print_engine_list() -> None:
    print("Available translation engines:\n")
    for name in engine_names():
        info = engine_info(name)
        flags = []
        if info["free"]:
            flags.append("free")
        if info["need_api_key"]:
            flags.append("API key")
        models = info["models"]
        suffix = "  [" + ", ".join(flags) + "]" if flags else ""
        print(f"  - {name}{suffix}")
        if models:
            print(f"      models: {', '.join(models)}")


def _print_chapters(path: str) -> None:
    for chapter in flatten(load_chapters(path)):
        indent = "  " * chapter.depth
        label = chapter.name or chapter.file or "(section)"
        print(f"  {chapter.index:>3}  {indent}{label}")


def _selected_chapters(path: str, spec):
    if not spec:
        return None
    return resolve_selection(load_chapters(path), spec)


def _export_extra(args) -> int:
    out = args.output
    if args.export_only in ("figures", "tables"):
        if not out or not os.path.splitext(out)[1] or os.path.isdir(out):
            out_dir = out or "."
        else:
            out_dir = os.path.dirname(out) or "."
        os.makedirs(out_dir, exist_ok=True)
    else:  # text writes a file
        out_dir = os.path.dirname(out) if out else "."
    selected = _selected_chapters(args.input, args.chapters)
    if args.export_only == "figures":
        figures = extract_figures(args.input, selected=selected)
        paths = export_figures(figures, out_dir, args.export_format or "img")
    elif args.export_only == "tables":
        tables = extract_tables(args.input, selected=selected)
        paths = export_tables(tables, out_dir, args.export_format or "csv")
    else:  # text
        target = args.output or default_output_path(args.input).rsplit(".", 1)[0] + ".txt"
        paths = export_text(args.input, target, selected=selected)
    for path in paths:
        print(path)
    print(f"{len(paths)} file(s) written")
    return 0


def _cli_progress(fraction: float, message: str) -> None:
    bar_len = 30
    done = int(max(0.0, min(1.0, fraction)) * bar_len)
    bar = "█" * done + "·" * (bar_len - done)
    sys.stderr.write(f"\r  [{bar}] {int(fraction * 100):3d}%  {message[:60]:<60}")
    sys.stderr.flush()
    if fraction >= 1.0:
        sys.stderr.write("\n")


def _build_settings(args) -> dict:
    settings: dict = {}
    # Always pin the position so a CLI run is deterministic (the value would
    # otherwise be "sticky" from a previous run stored in the config).
    settings["translation_position"] = args.position or "only"
    settings["online_batching"] = bool(args.batch)
    settings["cache_enabled"] = not args.no_cache
    if args.api_key or args.model:
        engine = args.engine or "Google(Free)New"
        set_engine_preference(
            engine, api_keys=([args.api_key] if args.api_key else []),
            model=args.model)
    return settings


def run_cli(args) -> int:
    ensure_defaults()
    settings = _build_settings(args)
    engine = args.engine or "Google(Free)New"
    selected = _selected_chapters(args.input, args.chapters) if args.chapters else None
    target = args.output or default_output_path(args.input, args.target)
    fmt = (args.export_format or "epub").lower()

    print(f"Engine : {engine}")
    print(f"Input  : {args.input}")
    if selected:
        print(f"Chapters: {', '.join((c.name or c.file or '?') for c in selected)}")
    print(f"Output : {target}{'' if fmt == 'epub' else ' (' + fmt + ')'}")
    print(f"{args.source} -> {args.target}\n")

    def log(text: str, error: bool = False) -> None:
        if error:
            sys.stderr.write(text + "\n")

    work_target = target if fmt == "epub" else \
        tempfile.mkdtemp(prefix="noesis-engine-") + "/translated.epub"

    try:
        path = translate_epub(
            args.input, work_target, engine=engine,
            source_lang=args.source, target_lang=args.target,
            chapters=args.chapters or None,
            settings=settings, on_progress=_cli_progress, on_log=log)
        if fmt != "epub":
            written = export_chapters(path, target, None, fmt)
            path = written[0]
    except KeyboardInterrupt:
        print("\nCanceled.", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(f"\nError: {exc}", file=sys.stderr)
        return 1
    print(f"Done: {path}")
    return 0


def run_preview(args) -> int:
    ensure_defaults()
    pairs = preview_translation(
        args.input, engine=args.engine or "Google(Free)New",
        source_lang=args.source, target_lang=args.target,
        chapters=args.chapters or None, limit=args.preview,
        settings=_build_settings(args))
    for original, translation in pairs:
        print(f"─ {original}")
        print(f"→ {translation}\n")
    print(f"{len(pairs)} segment(s) previewed")
    return 0


# --------------------------------------------------------------------- TUI
def _tui_initial(args) -> dict:
    """Values from the CLI to prefill the TUI wizard (``{}`` when no args).

    Only explicit information is carried over; it mirrors the desktop wizard
    and the lite engine's ``-gui libro.pdf --dst en`` behaviour.
    """
    if args is None:
        return {}
    initial = {
        "input": getattr(args, "input", None) or "",
        "output": getattr(args, "output", None) or "",
        "engine": getattr(args, "engine", None) or "Google(Free)New",
        "source": getattr(args, "source", None) or "English",
        "target": getattr(args, "target", None) or "Italian",
        "position": getattr(args, "position", None) or "only",
        "cache": not bool(getattr(args, "no_cache", False)),
        "batch": bool(getattr(args, "batch", False)),
        "api_key": getattr(args, "api_key", None) or "",
        "model": getattr(args, "model", None) or "",
    }
    return initial


def _make_tui_app(initial: dict | None = None):
    """Build (and return) the Textual App class, or ``None`` if unavailable."""
    try:
        from textual import work
        from textual.app import App, ComposeResult
        from textual.containers import Horizontal, Vertical
        from textual.widgets import (
            Button, Checkbox, Footer, Header, Input, ProgressBar, RichLog, Select)
    except Exception:  # noqa: BLE001 - textual is optional
        return None

    initial = dict(initial or {})
    engine_names_list = list(engine_names())
    selected_engine = initial.get("engine") or "Google(Free)New"
    if selected_engine not in engine_names_list:
        selected_engine = "Google(Free)New"

    class TranslationApp(App):
        CSS = """
        Screen { layout: vertical; }
        #form { height: auto; padding: 1; }
        #row1, #row2 { height: auto; }
        #log { height: 1fr; border: round $accent; }
        """
        BINDINGS = [
            ("q", "quit", "Quit"),
            ("ctrl+r", "run", "Run"),
            ("question_mark", "help", "Help"),
        ]

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Vertical(id="form"):
                yield Input(value=initial.get("input", ""),
                            placeholder="EPUB file path", id="input")
                yield Select(
                    [(n, n) for n in engine_names_list],
                    prompt="Engine", id="engine", value=selected_engine)
                yield Input(value=initial.get("source", "English"),
                            placeholder="Source language", id="source")
                yield Input(value=initial.get("target", "Italian"),
                            placeholder="Target language", id="target")
                yield Select(
                    [("Translation only", "only"),
                     ("Bilingual — below", "below"),
                     ("Bilingual — above", "above")],
                    prompt="Translation position", id="position",
                    value=initial.get("position", "only"))
                with Horizontal(id="row1"):
                    yield Checkbox("Use cache", value=initial.get("cache", True),
                                   id="cache")
                    yield Checkbox("Online batching",
                                   value=initial.get("batch", False), id="batch")
                with Horizontal(id="row2"):
                    yield Input(value=initial.get("api_key", ""),
                                placeholder="API key (if required)", id="api_key",
                                password=True)
                    yield Input(value=initial.get("model", ""),
                                placeholder="Model (optional)", id="model")
                yield Button("Translate", variant="primary", id="run")
                yield ProgressBar(total=100, id="progress")
            yield RichLog(id="log", highlight=True, markup=True)
            yield Footer()

        def on_button_pressed(self, event) -> None:
            if event.button.id == "run":
                self._start()

        def action_run(self) -> None:
            self._start()

        def action_help(self) -> None:
            self._log(
                "[b]Noesis Ebook Translator — TUI[/b]\n"
                "Ctrl+R run · q quit · ? help\n"
                "Fields: EPUB · engine · source/target language · position · "
                "cache · online batching · API key · model.\n"
                "The output EPUB is written next to the input unless -o is used."
            )

        def _widget(self, wtype, widget_id):
            try:
                return self.query_one(f"#{widget_id}", wtype)
            except Exception:
                return None

        def _log(self, message: str) -> None:
            widget = self._widget(RichLog, "log")
            if widget is not None:
                widget.write(message)

        def _start(self) -> None:
            input_path = self._widget(Input, "input").value.strip().strip("'\"")
            if not input_path:
                self._log("[red]Choose an EPUB file first.[/red]")
                return
            engine = self._widget(Select, "engine").value
            source = self._widget(Input, "source").value.strip() or "English"
            target = self._widget(Input, "target").value.strip() or "Italian"
            api_key = self._widget(Input, "api_key").value.strip()
            model = self._widget(Input, "model").value.strip() or None
            position = self._widget(Select, "position")
            settings = {
                "translation_position": getattr(position, "value", "only") or "only",
                "cache_enabled": self._widget(Checkbox, "cache").value,
                "online_batching": self._widget(Checkbox, "batch").value,
            }
            if api_key or model:
                set_engine_preference(
                    engine, api_keys=([api_key] if api_key else []), model=model)
            self._log(f"[b]Translating[/b] {input_path} ({source} -> {target})…")
            self._run(input_path, engine, source, target, settings,
                      initial.get("output") or "")

        @work(thread=True)
        def _run(self, input_path, engine, source, target, settings,
                 output_path: str = "") -> None:
            ensure_defaults()
            output = output_path or default_output_path(input_path, target)

            def progress(frac, msg):
                bar = self._widget(ProgressBar, "progress")
                if bar is not None:
                    self.call_from_thread(
                        bar.update, progress=int(max(0.0, min(1.0, frac)) * 100))

            def log(text, error=False):
                self.call_from_thread(self._log, text)

            try:
                path = translate_epub(
                    input_path, output, engine=engine, source_lang=source,
                    target_lang=target, settings=settings, on_progress=progress,
                    on_log=log)
                self.call_from_thread(self._log, f"[green]Done:[/green] {path}")
            except Exception as exc:  # noqa: BLE001 - TUI boundary
                self.call_from_thread(self._log, f"[red]Error:[/red] {exc}")

    return TranslationApp


def run_tui(args=None) -> int:
    initial = _tui_initial(args)
    app_class = _make_tui_app(initial)
    if app_class is None:
        return _fallback_wizard(initial)
    app_class().run()
    return 0


def _fallback_wizard(initial: dict | None = None) -> int:
    """Line-based wizard used when Textual is not installed."""
    initial = dict(initial or {})

    def ask(prompt: str, default: str) -> str:
        shown = f" [{default}]" if default else ""
        value = input(f"{prompt}{shown}: ").strip().strip("'\"")
        return value or default

    print("Textual not installed — simple wizard (install `textual` for the TUI).\n")
    input_path = ask("EPUB path", initial.get("input", ""))
    if not input_path:
        print("No input given.", file=sys.stderr)
        return 1
    print("Engines:", ", ".join(engine_names()))
    engine = ask("Engine", initial.get("engine") or "Google(Free)New")
    source = ask("Source language", initial.get("source") or "English")
    target = ask("Target language", initial.get("target") or "Italian")
    ensure_defaults()
    output = initial.get("output") or default_output_path(input_path, target)

    def progress(frac, msg):
        _cli_progress(frac, msg)

    path = translate_epub(
        input_path, output, engine=engine, source_lang=source,
        target_lang=target,
        settings={"translation_position": initial.get("position", "only")},
        on_progress=progress)
    print(f"Done: {path}")
    return 0


# -------------------------------------------------------------------- main
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="noesis-ebook-translator-engine",
        description="Translate an EPUB using the Ebook Translator engine "
                    "(CLI + Textual TUI).")
    parser.add_argument("input", nargs="?", help="input EPUB file")
    parser.add_argument("-o", "--output", help="output EPUB path")
    parser.add_argument("-e", "--engine", help="translation engine (see --list-engines)")
    parser.add_argument("-s", "--source", default="English", help="source language")
    parser.add_argument("-t", "--target", default="Italian", help="target language")
    parser.add_argument("--position", choices=["only", "below", "above"],
                        help="translation position (default: only)")
    parser.add_argument("--chapters", help="translate/export only these chapters "
                        "(1-based list like 1,3,5-7, or hrefs)")
    parser.add_argument("--export-format",
                        help="output format: epub|html|md|txt (chapters), "
                             "img|html|md (figures), csv|html|md (tables)")
    parser.add_argument("--export-only", choices=["figures", "tables", "text"],
                        help="extract instead of translating")
    parser.add_argument("--preview", type=int, metavar="N",
                        help="show N translated segments and exit")
    parser.add_argument("--list-chapters", action="store_true",
                        help="list the book chapters and exit")
    parser.add_argument("--batch", action="store_true", help="enable online batching")
    parser.add_argument("--no-cache", action="store_true", help="disable the cache")
    parser.add_argument("--api-key", help="API key for the selected engine")
    parser.add_argument("--model", help="model id for the selected engine")
    parser.add_argument("-gui", "--gui", action="store_true",
                        help="launch the terminal UI")
    parser.add_argument("--list-engines", action="store_true",
                        help="list available engines and exit")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    args = parser.parse_args(argv)

    if args.version:
        print(f"noesis-ebook-translator-engine {__version__}")
        return 0
    if args.list_engines:
        _print_engine_list()
        return 0
    if args.list_chapters:
        if not args.input:
            parser.error("--list-chapters requires an input EPUB")
        _print_chapters(args.input)
        return 0
    if args.gui:
        return run_tui(args)
    if not args.input:
        parser.error("the input EPUB file is required (or use -gui)")
    if args.preview:
        return run_preview(args)
    if args.export_only:
        return _export_extra(args)
    return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())
