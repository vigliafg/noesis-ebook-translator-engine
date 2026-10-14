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
    output = args.output or default_output_path(args.input, args.target)
    settings = _build_settings(args)
    engine = args.engine or "Google(Free)New"

    print(f"Engine : {engine}")
    print(f"Input  : {args.input}")
    print(f"Output : {output}")
    print(f"{args.source} -> {args.target}\n")

    def log(text: str, error: bool = False) -> None:
        if error:
            sys.stderr.write(text + "\n")

    try:
        path = translate_epub(
            args.input, output, engine=engine,
            source_lang=args.source, target_lang=args.target,
            settings=settings, on_progress=_cli_progress, on_log=log)
    except KeyboardInterrupt:
        print("\nCanceled.", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(f"\nError: {exc}", file=sys.stderr)
        return 1
    print(f"Done: {path}")
    return 0


# --------------------------------------------------------------------- TUI
def _make_tui_app():
    """Build (and return) the Textual App class, or ``None`` if unavailable."""
    try:
        from textual import work
        from textual.app import App, ComposeResult
        from textual.containers import Horizontal, Vertical
        from textual.widgets import (
            Button, Checkbox, Footer, Header, Input, ProgressBar, RichLog, Select)
    except Exception:  # noqa: BLE001 - textual is optional
        return None

    class TranslationApp(App):
        CSS = """
        Screen { layout: vertical; }
        #form { height: auto; padding: 1; }
        #row1, #row2 { height: auto; }
        #log { height: 1fr; border: round $accent; }
        """
        BINDINGS = [("q", "quit", "Quit"), ("ctrl+r", "run", "Run")]

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Vertical(id="form"):
                yield Input(placeholder="EPUB file path", id="input")
                yield Select(
                    [(n, n) for n in engine_names()],
                    prompt="Engine", id="engine", value="Google(Free)New")
                yield Input(value="English", placeholder="Source language",
                            id="source")
                yield Input(value="Italian", placeholder="Target language",
                            id="target")
                with Horizontal(id="row1"):
                    yield Checkbox("Bilingual output", id="bilingual")
                    yield Checkbox("Use cache", value=True, id="cache")
                    yield Checkbox("Online batching", id="batch")
                with Horizontal(id="row2"):
                    yield Input(placeholder="API key (if required)", id="api_key",
                                password=True)
                    yield Input(placeholder="Model (optional)", id="model")
                yield Button("Translate", variant="primary", id="run")
                yield ProgressBar(total=100, id="progress")
            yield RichLog(id="log", highlight=True, markup=True)
            yield Footer()

        def on_button_pressed(self, event) -> None:
            if event.button.id == "run":
                self._start()

        def action_run(self) -> None:
            self._start()

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
            settings = {
                "translation_position": (
                    "below" if self._widget(Checkbox, "bilingual").value else "only"),
                "cache_enabled": self._widget(Checkbox, "cache").value,
                "online_batching": self._widget(Checkbox, "batch").value,
            }
            if api_key or model:
                set_engine_preference(
                    engine, api_keys=([api_key] if api_key else []), model=model)
            self._log(f"[b]Translating[/b] {input_path} ({source} -> {target})…")
            self._run(input_path, engine, source, target, settings)

        @work(thread=True)
        def _run(self, input_path, engine, source, target, settings) -> None:
            ensure_defaults()
            output = default_output_path(input_path, target)

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


def run_tui() -> int:
    app_class = _make_tui_app()
    if app_class is None:
        return _fallback_wizard()
    app_class().run()
    return 0


def _fallback_wizard() -> int:
    """Line-based wizard used when Textual is not installed."""
    print("Textual not installed — simple wizard (install `textual` for the TUI).\n")
    input_path = input("EPUB path: ").strip().strip("'\"")
    if not input_path:
        print("No input given.", file=sys.stderr)
        return 1
    print("Engines:", ", ".join(engine_names()))
    engine = input("Engine [Google(Free)New]: ").strip() or "Google(Free)New"
    source = input("Source language [English]: ").strip() or "English"
    target = input("Target language [Italian]: ").strip() or "Italian"
    ensure_defaults()
    output = default_output_path(input_path, target)

    def progress(frac, msg):
        _cli_progress(frac, msg)

    path = translate_epub(
        input_path, output, engine=engine, source_lang=source,
        target_lang=target, settings={"translation_position": "only"},
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
    if args.gui:
        return run_tui()
    if not args.input:
        parser.error("the input EPUB file is required (or use -gui)")
    return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())
