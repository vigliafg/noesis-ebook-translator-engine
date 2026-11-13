#!/usr/bin/env python3
"""Shared harness for the Rosen end-to-end workflows.

These scripts exercise the **same entry points an agent uses** (the ``--json``
CLI, the AgentAPI and the MCP tools) against a real medical textbook:

* the source of truth is ``../noesis-ebook-translator/corpus1/Rosen's Emergency
  Medicine 10ed 2023 SLIM.epub`` (override with ``--book`` or
  ``NOESIS_E2E_BOOK``);
* the full book is 125 MB / 1306 TOC entries, so the harness derives a small
  **sample edition** (~50k characters, 5 chapters, 1 table, 1 figure) from five
  real Rosen chapters, cached in ``scripts/e2e/.cache/``;
* translation is **offline and deterministic**: the harness registers the fake
  engines ``E2E`` and ``E2E-Slow`` (the same trick as ``tests/fixtures.py``), so
  no API key, network call or money is involved.

Each workflow gets a fresh workspace (book copy, config, cache, output dir) and
runs in-process; the stdio workflow spawns a real subprocess instead.
"""
from __future__ import annotations

import argparse
import contextlib
import html
import importlib.util
import io
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import time
import traceback
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINE_PATH = ROOT / "noesis_ebook_translator_engine.py"
HERE = Path(__file__).resolve().parent
CACHE_DIR = HERE / ".cache"

#: Rosen chapters used to build the sample: Airway, Management,
#: Mechanical Ventilation, Management, Shock. The two "Management" entries are
#: intentional: WF06 uses them to exercise the ambiguity error.
ROSEN_INDICES = (14, 16, 18, 20, 22)
SAMPLE_SCHEMA = 1

MARKER = "[IT]"
END_MARKER = "[/IT]"


class WorkflowFailure(AssertionError):
    """A workflow assertion failed (reported by the runner)."""


def check(condition, message):
    if not condition:
        raise WorkflowFailure(message)


# ---------------------------------------------------------------------------
#  Engine + offline fake translators
# ---------------------------------------------------------------------------
_ENGINE = None


def load_engine():
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE
    spec = importlib.util.spec_from_file_location(
        "noesis_ebook_translator_engine", ENGINE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.log.level = module.Log.ERROR
    _register_engines(module)
    _ENGINE = module
    return module


def _register_engines(module) -> None:
    if any(getattr(engine, "name", None) == "E2E"
           for engine in module.builtin_engines):
        return

    class E2E(module.Base):
        name = "E2E"
        alias = "E2E"
        free = True
        need_api_key = False
        lang_codes = module.Base.load_lang_codes(module.google)
        endpoint = ""

        def translate(self, content):
            return MARKER + content + END_MARKER

    class E2ESlow(E2E):
        name = "E2E-Slow"
        alias = "E2E-Slow"

        def translate(self, content):
            # WF08 tunes this so cancellation is deterministic for both a large
            # Rosen chapter and a tiny fallback chapter.
            time.sleep(float(os.environ.get("NOESIS_E2E_DELAY", "0.02")))
            return MARKER + content + END_MARKER

    module.builtin_engines = tuple(module.builtin_engines) + (E2E, E2ESlow)


# ---------------------------------------------------------------------------
#  Source book + sample edition
# ---------------------------------------------------------------------------
def find_source(explicit=None):
    """Locate the Rosen EPUB (or an explicit/fallback book)."""
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    override = os.environ.get("NOESIS_E2E_BOOK")
    if override:
        candidates.append(Path(override))
    desktop = ROOT.parent / "noesis-ebook-translator"
    if desktop.is_dir():
        corpus = desktop / "corpus1"
        candidates.append(corpus / "Rosen's Emergency Medicine 10ed 2023 SLIM.epub")
        if corpus.is_dir():
            candidates.extend(sorted(corpus.glob("*osen*.epub")))
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate).resolve()
    fallback = ROOT / "tests" / "data" / "corpus" / "descent_of_man.epub"
    if fallback.is_file():
        print(f"[harness] Rosen not found, falling back to {fallback.name}",
              file=sys.stderr)
        return fallback.resolve()
    raise SystemExit("Rosen EPUB not found: pass --book or set NOESIS_E2E_BOOK")


def _pick_chapters(engine, source):
    chapters = engine.load_chapters(str(source))
    flat = engine.flatten(chapters)
    if "rosen" in source.name.lower() and len(flat) >= max(ROSEN_INDICES):
        return [flat[index - 1] for index in ROSEN_INDICES], chapters
    picked, total = [], 0
    for node in flat:
        if not node.file:
            continue
        rows = engine.extract_text(str(source), chapters, [node])
        size = sum(len(text) for _index, _name, text in rows)
        if 400 <= size <= 20000:
            picked.append(node)
            total += size
        if len(picked) >= 5 or total >= 40000:
            break
    if not picked:
        picked = flat[:3]
    return picked, chapters


def _render_table(table) -> str:
    rows = []
    for row in (table.rows or [])[:8]:
        cells = "".join(f"<td>{html.escape(str(cell))}</td>" for cell in row)
        rows.append(f"<tr>{cells}</tr>")
    caption = (f"<caption>{html.escape(table.caption)}</caption>"
               if table.caption else "")
    return f"<table>{caption}{''.join(rows)}</table>"


def _find_table_and_figure(engine, source, nodes):
    table_html = None
    figure = None
    for node in nodes:
        if table_html is None:
            tables = engine.extract_tables(str(source), selected=[node])
            if tables and tables[0].rows:
                table_html = _render_table(tables[0])
        if figure is None:
            figures = [
                item for item in engine.extract_figures(str(source),
                                                       selected=[node])
                if item.data and len(item.data) <= 200_000]
            if figures:
                figure = min(figures, key=lambda item: len(item.data))
        if table_html and figure:
            break
    return table_html, figure


def _build_sample(engine, source, nodes, chapters, target: Path) -> None:
    from ebooklib import epub

    table_html, figure = _find_table_and_figure(engine, source, nodes)
    book = epub.EpubBook()
    book.set_identifier("noesis-e2e-sample")
    book.set_title("Rosen E2E Sample")
    book.set_language("en")
    items = []
    for index, node in enumerate(nodes, 1):
        rows = engine.extract_text(str(source), chapters, [node])
        body = [f"<h1>{html.escape(node.name or f'Chapter {index}')}</h1>"]
        body.extend(f"<p>{html.escape(text)}</p>"
                    for _row_index, _row_name, text in rows if text.strip())
        if index == 1:
            if table_html:
                body.append(table_html)
            if figure:
                body.append('<figure><img src="images/e2e-figure.png" '
                            'alt="Rosen figure"/><figcaption>Rosen figure'
                            '</figcaption></figure>')
        item = epub.EpubHtml(
            title=node.name or f"Chapter {index}",
            file_name=f"ch{index}.xhtml", lang="en")
        item.content = "<html><body>" + "".join(body) + "</body></html>"
        book.add_item(item)
        items.append(item)
    if figure:
        image = epub.EpubImage()
        image.file_name = "images/e2e-figure.png"
        image.media_type = figure.mime or "image/png"
        image.content = figure.data
        book.add_item(image)
    book.toc = tuple(items)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav"] + items
    target.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(target), book)


def _sample_key(source: Path, nodes) -> dict:
    stat = source.stat()
    return {
        "schema": SAMPLE_SCHEMA,
        "source": str(source),
        "mtime_ns": stat.st_mtime_ns,
        "size": stat.st_size,
        "chapters": [node.name for node in nodes],
    }


def ensure_sample(engine, source, force=False) -> Path:
    """Build (or reuse) the small EPUB every workflow reads."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    nodes, chapters = _pick_chapters(engine, source)
    key = _sample_key(source, nodes)
    slug = re.sub(r"[^a-z0-9]+", "-", source.stem.lower()).strip("-")[:40]
    sample = CACHE_DIR / f"sample-{slug}.epub"
    key_file = CACHE_DIR / f"sample-{slug}.key.json"
    if not force and sample.is_file() and key_file.is_file():
        try:
            if json.loads(key_file.read_text(encoding="utf-8")) == key:
                return sample
        except ValueError:
            pass
    print(f"[harness] building the sample from {source.name} "
          f"({len(nodes)} chapters)…", file=sys.stderr)
    _build_sample(engine, source, nodes, chapters, sample)
    segments = engine.collect_segments(str(sample))
    chapter_count = len(engine.flatten(engine.load_chapters(str(sample))))
    if not segments or chapter_count < 2:
        raise SystemExit("the derived sample is empty; check the source EPUB")
    key_file.write_text(json.dumps(key), encoding="utf-8")
    return sample


# ---------------------------------------------------------------------------
#  Workspace (fresh book/config/cache per workflow)
# ---------------------------------------------------------------------------
class Workspace:
    def __init__(self, engine, sample: Path, label: str):
        self.engine = engine
        self.dir = Path(tempfile.mkdtemp(prefix=f"noesis-e2e-{label}-"))
        self.book = self.dir / "book.epub"
        shutil.copy2(sample, self.book)
        self.out = self.dir / "out"
        self.out.mkdir()
        self.config_dir = self.dir / "config"
        self.config_dir.mkdir()
        self.cache_store = self.dir / "cache-store"
        store = engine.TranslationCache
        store.dir_path = str(self.cache_store)
        store.cache_path = str(self.cache_store / "cache")
        store.temp_path = str(self.cache_store / "temp")
        for path in (store.cache_path, store.temp_path):
            os.makedirs(path, exist_ok=True)
        engine.config_dir = str(self.config_dir)
        engine.plugin_dir = str(self.config_dir)
        engine._JOBS.clear()
        engine._ACTIVE_JOB = None
        engine._AGENT_BOOKS.clear()
        engine._agent_configure(
            roots=[str(self.dir)], enforce_roots=True, configure_log=False)
        engine.log.level = engine.Log.ERROR

    def close(self, keep=False) -> None:
        job = self.engine._ACTIVE_JOB
        if job is not None and job.state in ("queued", "running"):
            job.cancel()
            job.wait(10)
        if keep:
            print(f"[harness] kept {self.dir}", file=sys.stderr)
        else:
            shutil.rmtree(self.dir, ignore_errors=True)


class Env:
    def __init__(self, engine, workspace, source, sample, is_rosen,
                 verbose=False):
        self.engine = engine
        self.workspace = workspace
        self.source = source
        self.sample = sample
        self.is_rosen = is_rosen
        self.verbose = verbose

    def log(self, message: str) -> None:
        if self.verbose:
            print(f"    {message}", file=sys.stderr)


# ---------------------------------------------------------------------------
#  Helpers shared by the workflows
# ---------------------------------------------------------------------------
def mcp(engine, name: str, arguments=None) -> dict:
    """Call an MCP tool in-process and return its structured content."""
    response = engine._mcp_dispatch({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": name, "arguments": arguments or {}},
    })
    result = response.get("result")
    if result is None:
        raise WorkflowFailure(f"{name}: protocol error {response.get('error')}")
    if result.get("isError"):
        raise WorkflowFailure(f"{name}: {result['structuredContent'].get('error')}")
    return result["structuredContent"]


def mcp_error(engine, name: str, arguments, code: str) -> dict:
    """Assert that a tool fails with a specific machine code."""
    response = engine._mcp_dispatch({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": name, "arguments": arguments or {}},
    })
    result = response.get("result") or {}
    check(result.get("isError"), f"{name}: expected an error, got success")
    info = result["structuredContent"]["error"]
    check(info["code"] == code,
          f"{name}: expected {code!r}, got {info!r}")
    return info


def cli(engine, argv):
    """Run the real CLI entry point in-process, capturing both streams."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = engine.main(list(argv))
    return code, out.getvalue(), err.getvalue()


def run_ok(engine, argv, label=""):
    code, out, err = cli(engine, argv)
    check(code == 0, f"{label or argv[:2]} failed with rc={code}\n{err[-3000:]}")
    return out, err


def read_json(engine, argv, label=""):
    out, _err = run_ok(engine, argv, label)
    try:
        return json.loads(out)
    except ValueError as exc:
        raise WorkflowFailure(
            f"{label or argv[:2]}: stdout is not one JSON document ({exc})\n"
            f"{out[:800]}") from exc


def book_text(path) -> str:
    with zipfile.ZipFile(path) as archive:
        return "\n".join(
            archive.read(name).decode("utf-8", "replace")
            for name in archive.namelist()
            if name.endswith((".xhtml", ".html")))


def plain_text(path) -> str:
    return re.sub(r"<[^>]+>", " ", book_text(path))


def doc_count(path) -> int:
    with zipfile.ZipFile(path) as archive:
        return sum(1 for name in archive.namelist()
                   if name.endswith((".xhtml", ".html")))


def source_phrase(engine, book, chapter=None) -> str:
    """A phrase unique in its chapter *and* in the whole book.

    Without ``chapter`` every chapter is scanned (TOC titles and figure
    captions repeat text, so uniqueness must be checked on the whole file).
    """
    whole = plain_text(book)
    if chapter is None:
        chapters = mcp(engine, "list_chapters",
                       {"input": str(book)})["chapters"]
        indexes = [item["index"] for item in chapters]
    else:
        indexes = [chapter]
    for index in indexes:
        text = mcp(engine, "read_chapter",
                   {"input": str(book), "chapter": index})["text"]
        for match in re.finditer(r"[A-Za-z][A-Za-z ]{24,}", text):
            phrase = match.group(0).strip()
            if text.count(phrase) == 1 and whole.count(phrase) == 1:
                return phrase
    raise WorkflowFailure("no phrase unique to a chapter and to the book")


def unique_chapter(chapters):
    """The first chapter whose title matches no other chapter (unique spec)."""
    for chapter in chapters:
        name = (chapter.get("name") or "").strip().lower()
        if not name:
            continue
        hits = sum(1 for other in chapters
                   if name in (other.get("name") or "").lower())
        if hits == 1:
            return chapter
    return chapters[0]


def translation_target(engine, book) -> dict:
    """The chapter every translation workflow uses (the richest one).

    The analysis workflows keep looking at the whole book; translation runs are
    deliberately limited to **one chapter** so the E2E suite stays fast and the
    paid work an agent would trigger is small.
    """
    plan = mcp(engine, "plan_translation",
               {"input": str(book), "engine": "E2E"})
    rows = [row for row in plan.get("per_chapter") or []
            if row.get("index") and row.get("segments")]
    check(rows, "the book has no translatable chapter")
    row = max(rows, key=lambda item: item["segments"])
    return row


def simulate_crash(engine) -> Path:
    """Turn the newest cache into an 'interrupted' run (as after a power cut)."""
    databases = sorted(
        Path(engine.TranslationCache.cache_path).glob("*.db"),
        key=lambda path: path.stat().st_mtime, reverse=True)
    check(databases, "no cache database to mark as interrupted")
    with sqlite3.connect(databases[0]) as connection:
        connection.execute(
            "INSERT INTO info(key, value) VALUES('run_status', 'running') "
            "ON CONFLICT(key) DO UPDATE SET value='running'")
        connection.commit()
    return databases[0]


def ndjson(payload) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8") + b"\n"


# ---------------------------------------------------------------------------
#  Single-workflow entry point (each wfXX.py is runnable on its own)
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--book", help="EPUB to use instead of Rosen")
    parser.add_argument("--keep", action="store_true",
                        help="keep the temporary workspace")
    parser.add_argument("--force-sample", action="store_true",
                        help="rebuild the derived sample")
    parser.add_argument("--verbose", action="store_true")
    return parser


def run_single(name, function, argv=None) -> int:
    args = build_parser().parse_args(argv)
    engine = load_engine()
    source = find_source(args.book)
    sample = ensure_sample(engine, source, force=args.force_sample)
    workspace = Workspace(engine, sample, "single")
    env = Env(engine, workspace, source, sample,
              "rosen" in source.name.lower(), args.verbose)
    started = time.time()
    try:
        function(env)
    except Exception:                          # noqa: BLE001 - script boundary
        traceback.print_exc()
        workspace.close(keep=args.keep)
        print(f"[FAIL] {name}")
        return 1
    elapsed = time.time() - started
    print(f"[PASS] {name} ({elapsed:.2f}s)")
    workspace.close(keep=args.keep)
    return 0
