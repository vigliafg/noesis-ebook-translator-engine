"""CLI end-to-end test with an offline fake engine."""
import os
import tempfile
import unittest
import zipfile

from tests.fixtures import build_sample_epub, load_engine, register_fake_engine


class TestCli(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = load_engine()
        register_fake_engine(cls.engine)

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="noesis-et-engine-e2e-")
        self.src = build_sample_epub(os.path.join(self.tmp, "book.epub"))
        self.out = os.path.join(self.tmp, "book_out.epub")

    def test_translate_replaces_text_and_keeps_markup(self):
        rc = self.engine.main(
            [self.src, "-o", self.out, "-e", "Fake", "--no-cache"])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isfile(self.out))

        docs = []
        with zipfile.ZipFile(self.out) as archive:
            for name in archive.namelist():
                if name.endswith((".xhtml", ".html")):
                    docs.append(archive.read(name).decode("utf-8"))
        body = "\n".join(docs)
        self.assertIn("IT&lt;", body)      # fake engine marker
        self.assertIn("<a", body)          # anchors preserved
        self.assertEqual(body.count("Hello"), 1)  # single-language output

    def test_default_output_path(self):
        self.assertTrue(
            self.engine.default_output_path("/x/Book.epub", "Italian")
            .endswith("_ITALIAN.epub"))

    def test_cli_position_below_is_bilingual(self):
        rc = self.engine.main(
            [self.src, "-o", self.out, "-e", "Fake", "--no-cache",
             "--position", "below"])
        self.assertEqual(rc, 0)
        with zipfile.ZipFile(self.out) as archive:
            body = "\n".join(
                archive.read(n).decode("utf-8") for n in archive.namelist()
                if n.endswith((".xhtml", ".html")))
        # Bilingual keeps the original and adds the translation → two copies.
        self.assertEqual(body.count("Hello"), 2)


if __name__ == "__main__":
    unittest.main()
