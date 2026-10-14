"""CLI tests for chapter selection and content export (offline)."""
import os
import tempfile
import unittest

from tests.fixtures import build_rich_epub, load_engine, register_fake_engine


class TestCliChaptersAndExport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = load_engine()
        register_fake_engine(cls.engine)

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="noesis-engine-cli-")
        self.epub = build_rich_epub(os.path.join(self.tmp, "rich.epub"))

    def test_list_chapters(self):
        self.assertEqual(self.engine.main(["--list-chapters", self.epub]), 0)

    def test_export_figures(self):
        out = os.path.join(self.tmp, "figs")
        rc = self.engine.main(
            [self.epub, "--export-only", "figures", "--export-format", "img", "-o", out])
        self.assertEqual(rc, 0)
        self.assertTrue(any(f.endswith(".png") for f in os.listdir(out)))

    def test_export_tables_csv(self):
        out = os.path.join(self.tmp, "tabs")
        rc = self.engine.main(
            [self.epub, "--export-only", "tables", "--export-format", "csv", "-o", out])
        self.assertEqual(rc, 0)
        self.assertTrue(os.listdir(out))

    def test_export_text(self):
        target = os.path.join(self.tmp, "book.txt")
        rc = self.engine.main([self.epub, "--export-only", "text", "-o", target])
        self.assertEqual(rc, 0)
        self.assertIn("Opening paragraph", open(target, encoding="utf-8").read())

    def test_preview_offline(self):
        self.assertEqual(
            self.engine.main([self.epub, "--preview", "2", "-e", "Fake"]), 0)

    def test_translate_selected_chapter_to_html(self):
        out = os.path.join(self.tmp, "c3.html")
        rc = self.engine.main([
            self.epub, "-e", "Fake", "--chapters", "c3.xhtml",
            "--export-format", "html", "-o", out, "--no-cache"])
        self.assertEqual(rc, 0)
        html = open(out, encoding="utf-8").read()
        self.assertIn("IT&lt;", html)
        # only chapter 3 was translated/exported
        self.assertNotIn("Opening paragraph.", html)


if __name__ == "__main__":
    unittest.main()
