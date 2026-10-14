"""End-to-end tests over the real Darwin corpus (offline fake engine).

The corpus (three Project Gutenberg books by Charles Darwin) is copied from the
desktop repository by ``tools/sync_from_desktop.py``; see
``tests/data/darwin/SOURCE.md``. These tests run offline.

Set ``NOESIS_ONLINE_TESTS=1`` to add a real Google-translate smoke test.
"""
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from ebooklib import epub

from tests.fixtures import load_engine, register_fake_engine

CORPUS = Path(__file__).resolve().parent / "data" / "darwin"
BOOKS = [
    "origin_of_species.epub",
    "voyage_of_the_beagle.epub",
    "descent_of_man.epub",
]


def _documents(path):
    book = epub.read_epub(str(path))
    return [item for item in book.get_items() if item.get_type() == 9]


def _xhtml_text(path):
    chunks = []
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if name.endswith((".xhtml", ".html", ".htm")):
                chunks.append(archive.read(name).decode("utf-8", "replace"))
    return "\n".join(chunks)


@unittest.skipUnless(CORPUS.is_dir(), "Darwin corpus not present")
class TestDarwinCorpus(unittest.TestCase):
    outputs: dict = {}

    @classmethod
    def setUpClass(cls):
        cls.engine = load_engine()
        register_fake_engine(cls.engine)
        cls.tmp = tempfile.mkdtemp(prefix="noesis-engine-darwin-")
        for name in BOOKS:
            cls.outputs[name] = cls.engine.translate_epub(
                str(CORPUS / name), os.path.join(cls.tmp, name), engine="Fake",
                source_lang="English", target_lang="Italian",
                settings={"translation_position": "only", "cache_enabled": False})

    def test_each_book_translates_and_stays_valid(self):
        for name in BOOKS:
            with self.subTest(book=name):
                self.assertTrue(os.path.isfile(self.outputs[name]))
                self.assertEqual(
                    len(_documents(CORPUS / name)),
                    len(_documents(self.outputs[name])))

    def test_translation_is_applied_and_anchors_kept(self):
        for name in BOOKS:
            with self.subTest(book=name):
                body = _xhtml_text(self.outputs[name])
                self.assertIn("IT&lt;", body)
                self.assertIn("href=", body)
                self.assertNotIn("IT&lt;", _xhtml_text(CORPUS / name))


@unittest.skipUnless(os.environ.get("NOESIS_ONLINE_TESTS"), "online tests disabled")
class TestDarwinOnline(unittest.TestCase):
    def test_google_translates_a_real_section(self):
        engine = load_engine()
        out = os.path.join(tempfile.mkdtemp(prefix="noesis-engine-online-"),
                           "origin_it.epub")
        engine.translate_epub(
            str(CORPUS / "origin_of_species.epub"), out,
            engine="Google(Free)New", source_lang="English",
            target_lang="Italian",
            settings={"translation_position": "only", "cache_enabled": False})
        self.assertGreater(os.path.getsize(out), 0)


if __name__ == "__main__":
    unittest.main()
