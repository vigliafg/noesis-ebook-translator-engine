"""TUI smoke test driving the real Textual app (skipped without textual)."""
import argparse
import unittest

from tests.fixtures import build_sample_epub, load_engine

try:
    import textual  # noqa: F401
    _HAS_TEXTUAL = True
except Exception:  # noqa: BLE001 - optional dependency
    _HAS_TEXTUAL = False


class TestTuiInitialValues(unittest.TestCase):
    def test_none_gives_empty_dict(self):
        engine = load_engine()
        self.assertEqual(engine._tui_initial(None), {})

    def test_cli_values_are_carried_over(self):
        engine = load_engine()
        args = argparse.Namespace(
            input="libro.epub", engine="Fake", source="English",
            target="German", position="above", no_cache=True, batch=True,
            api_key="k", model="m")
        initial = engine._tui_initial(args)
        self.assertEqual(initial["input"], "libro.epub")
        self.assertEqual(initial["engine"], "Fake")
        self.assertEqual(initial["target"], "German")
        self.assertEqual(initial["position"], "above")
        self.assertFalse(initial["cache"])
        self.assertTrue(initial["batch"])
        self.assertEqual(initial["api_key"], "k")
        self.assertEqual(initial["model"], "m")

    def test_gui_receives_args(self):
        engine = load_engine()
        captured = {}

        def fake_run_tui(args=None):
            captured["args"] = args
            return 0

        original = engine.run_tui
        engine.run_tui = fake_run_tui
        try:
            rc = engine.main(["-gui", "libro.epub", "-t", "German"])
        finally:
            engine.run_tui = original
        self.assertEqual(rc, 0)
        self.assertEqual(captured["args"].input, "libro.epub")
        self.assertEqual(captured["args"].target, "German")


@unittest.skipUnless(_HAS_TEXTUAL, "textual not installed")
class TestTui(unittest.IsolatedAsyncioTestCase):
    async def test_app_composes_with_widgets(self):
        engine = load_engine()
        app_class = engine._make_tui_app()
        self.assertIsNotNone(app_class)
        app = app_class()
        async with app.run_test() as pilot:
            await pilot.pause()
            from textual.widgets import Button, Input, ProgressBar, Select

            self.assertIsNotNone(app.query_one("#input", Input))
            self.assertIsNotNone(app.query_one("#engine", Select))
            self.assertIsNotNone(app.query_one("#run", Button))
            self.assertIsNotNone(app.query_one("#progress", ProgressBar))

    async def test_widgets_are_prefilled_from_cli(self):
        engine = load_engine()
        app_class = engine._make_tui_app({
            "input": "/tmp/libro.epub", "engine": "DeepSeek",
            "source": "English", "target": "German", "position": "above",
            "cache": False, "batch": True, "api_key": "segreta", "model": "m",
        })
        app = app_class()
        async with app.run_test() as pilot:
            await pilot.pause()
            from textual.widgets import Checkbox, Input, Select

            self.assertEqual(
                app.query_one("#input", Input).value, "/tmp/libro.epub")
            self.assertEqual(app.query_one("#engine", Select).value, "DeepSeek")
            self.assertEqual(app.query_one("#target", Input).value, "German")
            self.assertEqual(
                app.query_one("#position", Select).value, "above")
            self.assertFalse(app.query_one("#cache", Checkbox).value)
            self.assertTrue(app.query_one("#batch", Checkbox).value)
            self.assertEqual(app.query_one("#model", Input).value, "m")


if __name__ == "__main__":
    unittest.main()
