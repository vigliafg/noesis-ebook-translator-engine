"""The generated engine exposes all engines and works offline."""
import unittest

from tests.fixtures import load_engine, register_fake_engine


class TestGeneratedEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = load_engine()
        register_fake_engine(cls.engine)

    def test_version_and_all_engines(self):
        names = set(self.engine.engine_names())
        for expected in (
                "Google(Free)New", "Gemini", "ChatGPT", "Claude", "DeepSeek",
                "OpenRouter", "DeepL", "MicrosoftEdge(Free)", "Youdao", "Baidu"):
            self.assertIn(expected, names, expected)

    def test_module_is_self_contained(self):
        # The monofile must not depend on a real ``calibre`` package.
        import sys

        self.assertNotIn("calibre.utils.localization", sys.modules)

    def test_list_engines_cli(self):
        self.assertEqual(self.engine.main(["--list-engines"]), 0)

    def test_version_cli(self):
        self.assertEqual(self.engine.main(["--version"]), 0)


if __name__ == "__main__":
    unittest.main()
