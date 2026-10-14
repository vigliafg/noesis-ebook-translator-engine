"""Shared fixtures: load the monofile engine and build a sample EPUB."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE_PATH = ROOT / "noesis_ebook_translator_engine.py"

_engine = None


def load_engine():
    """Import (once) the generated single-file engine module."""
    global _engine
    if _engine is not None:
        return _engine
    spec = importlib.util.spec_from_file_location(
        "noesis_ebook_translator_engine", ENGINE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _engine = module
    return module


def register_fake_engine(module):
    """Add an offline engine that wraps every text in ``IT<...>``."""
    # Keep test output readable: the engine logs every paragraph at INFO.
    module.log.level = module.log.ERROR
    if any(getattr(e, "name", None) == "Fake" for e in module.builtin_engines):
        return

    Base = module.Base

    class FakeEngine(Base):
        name = "Fake"
        alias = "Fake"
        free = True
        need_api_key = False
        lang_codes = Base.load_lang_codes(module.google)
        endpoint = ""

        def translate(self, content):
            return "IT<" + content + ">"

    module.builtin_engines = tuple(module.builtin_engines) + (FakeEngine,)


def build_sample_epub(path: str) -> str:
    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier("noesis-engine-test")
    book.set_title("Engine Sample")
    book.set_language("en")
    chapter = epub.EpubHtml(title="Chapter 1", file_name="c1.xhtml", lang="en")
    chapter.content = (
        "<html xmlns='http://www.w3.org/1999/xhtml'><head/><body>"
        "<h1>Chapter One</h1>"
        "<p>Hello <em>world</em>, and an <a href='x'>anchor</a>.</p>"
        "</body></html>")
    book.add_item(chapter)
    book.toc = (epub.Link("c1.xhtml", "Chapter 1", "c1"),)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", chapter]
    epub.write_epub(path, book)
    return path
