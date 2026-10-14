"""TUI smoke test driving the real Textual app (skipped without textual)."""
import unittest

from tests.fixtures import load_engine

try:
    import textual  # noqa: F401
    _HAS_TEXTUAL = True
except Exception:  # noqa: BLE001 - optional dependency
    _HAS_TEXTUAL = False


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


if __name__ == "__main__":
    unittest.main()
