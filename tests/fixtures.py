"""Shared fixtures: load the monofile engine and build sample EPUBs."""
from __future__ import annotations

import base64
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE_PATH = ROOT / "noesis_ebook_translator_engine.py"

TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M8AAAMBAQDJ"
    "/pLvAAAAAElFTkSuQmCC")

_engine = None


def load_engine():
    """Import (once) the generated single-file engine module."""
    global _engine
    if _engine is not None:
        return _engine
    spec = importlib.util.spec_from_file_location(
        "noesis_ebook_translator_engine", ENGINE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses need it registered
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


def build_rich_epub(path: str) -> str:
    """A 3-chapter EPUB with a nested TOC, a captioned figure and a table."""
    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier("noesis-engine-rich")
    book.set_title("Engine Rich")
    book.set_language("en")

    image = epub.EpubImage()
    image.file_name = "images/pic.png"
    image.media_type = "image/png"
    image.set_content(TINY_PNG)
    book.add_item(image)

    c1 = epub.EpubHtml(title="Introduction", file_name="c1.xhtml", lang="en")
    c1.content = (
        "<html xmlns='http://www.w3.org/1999/xhtml'><head/><body>"
        "<h1>Introduction</h1><p>Opening paragraph.</p>"
        "<div class='figcenter'><img src='images/pic.png' alt=''/>"
        "<p>Fig. 1. A very small picture.</p></div>"
        "<table><caption>Tab. 1. Sample</caption>"
        "<tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>"
        "</body></html>")
    c2 = epub.EpubHtml(title="Chapter 2", file_name="c2.xhtml", lang="en")
    c2.content = ("<html xmlns='http://www.w3.org/1999/xhtml'><head/><body>"
                  "<h1>Chapter Two</h1><p>Body two.</p></body></html>")
    c3 = epub.EpubHtml(title="Chapter 3", file_name="c3.xhtml", lang="en")
    c3.content = ("<html xmlns='http://www.w3.org/1999/xhtml'><head/><body>"
                  "<h1>Chapter Three</h1><p>Body three.</p></body></html>")
    for item in (c1, c2, c3):
        book.add_item(item)
    book.toc = (epub.Link("c1.xhtml", "Introduction", "c1"),
                (epub.Section("Part Two"),
                 (epub.Link("c2.xhtml", "Chapter 2", "c2"),
                  epub.Link("c3.xhtml", "Chapter 3", "c3"))))
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", c1, c2, c3]
    epub.write_epub(path, book)
    return path
