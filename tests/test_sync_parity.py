"""Parity contract: the generated monofile must match a fresh sync.

Skipped when the desktop checkout (source of truth) is not available — e.g. in
CI, where only this repository is checked out.
"""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESKTOP = ROOT.parent / "noesis-ebook-translator"
SYNC = ROOT / "tools" / "sync_from_desktop.py"
OUTPUT = ROOT / "noesis_ebook_translator_engine.py"


def _load_sync():
    spec = importlib.util.spec_from_file_location("sync_from_desktop", SYNC)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(DESKTOP.is_dir(), "desktop repository not present")
class TestSyncParity(unittest.TestCase):
    def test_generated_file_is_up_to_date(self):
        sync = _load_sync()
        expected = sync.build_text(DESKTOP)
        actual = OUTPUT.read_text(encoding="utf-8")
        self.assertEqual(
            actual, expected,
            "noesis_ebook_translator_engine.py is stale; run "
            "`python tools/sync_from_desktop.py`")

    def test_engine_source_manifest(self):
        import json

        meta = json.loads((ROOT / "ENGINE_SOURCE.json").read_text(encoding="utf-8"))
        self.assertIn("desktop_commit", meta)
        self.assertIn("engines/__init__.py", meta.get("overrides", []))


if __name__ == "__main__":
    unittest.main()
