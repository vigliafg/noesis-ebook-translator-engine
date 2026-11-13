"""CLI JSON contract tests (the agent-facing command line)."""
import io
import json
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout

from tests.agent_fixtures import EngineSandbox


class TestCliJson(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sandbox = EngineSandbox()
        cls.sandbox.__enter__()
        cls.engine = cls.sandbox.engine
        cls.tmp = cls.sandbox.tmp
        cls.book = cls.sandbox.book

    @classmethod
    def tearDownClass(cls):
        cls.sandbox.__exit__(None, None, None)

    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = self.engine.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_describe_is_a_single_json_document(self):
        code, out, _err = self.run_cli(["--describe"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["server"]["protocol"], "2025-06-18")
        self.assertGreaterEqual(len(payload["tools"]), 10)

    def test_list_engines_json(self):
        code, out, _err = self.run_cli(["--list-engines", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertIn("engines", payload)
        self.assertIn("Fake", {item["name"] for item in payload["engines"]})

    def test_list_chapters_json(self):
        code, out, _err = self.run_cli(
            [self.book, "--list-chapters", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["title"], "Engine Sample")
        self.assertGreaterEqual(payload["count"], 1)

    def test_dry_run(self):
        code, out, _err = self.run_cli([self.book, "--dry-run"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertGreater(payload["segments"], 0)
        self.assertNotIn("output", payload)

    def test_translate_json(self):
        target = os.path.join(self.tmp, "cli-json.epub")
        code, out, _err = self.run_cli([
            self.book, "-o", target, "-e", "Fake", "--no-cache", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["output"], target)
        self.assertTrue(os.path.isfile(target))
        self.assertGreaterEqual(payload["segments"], 1)
        self.assertIn("engine", payload)

    def test_json_stream(self):
        target = os.path.join(self.tmp, "cli-stream.epub")
        code, out, _err = self.run_cli([
            self.book, "-o", target, "-e", "Fake", "--no-cache",
            "--json-stream"])
        self.assertEqual(code, 0)
        events = [json.loads(line) for line in out.splitlines() if line.strip()]
        self.assertTrue(events)
        self.assertEqual(events[-1]["type"], "result")
        self.assertTrue(any(event["type"] == "progress" for event in events))
        self.assertTrue(os.path.isfile(target))

    def test_error_is_json(self):
        missing = os.path.join(self.tmp, "missing.epub")
        code, out, err = self.run_cli([missing, "-e", "Fake", "--json"])
        self.assertEqual(code, 1)
        payload = json.loads(out)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "not_found")
        self.assertIn("not found", err)

    def test_unknown_chapter_is_an_error_not_an_empty_book(self):
        target = os.path.join(self.tmp, "never.epub")
        code, out, err = self.run_cli([
            self.book, "-o", target, "--chapters", "999", "-e", "Fake",
            "--json"])
        self.assertEqual(code, 1)
        payload = json.loads(out)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "not_found")
        self.assertFalse(os.path.exists(target))
        self.assertIn("matched nothing", err)

    def test_resume_without_run_still_translates(self):
        target = os.path.join(self.tmp, "cli-resume.epub")
        code, out, err = self.run_cli([
            self.book, "-o", target, "-e", "Fake", "--no-cache",
            "--resume", "--json"])
        self.assertEqual(code, 0)
        self.assertIn("No interrupted run", err)
        self.assertTrue(os.path.isfile(target))

    def test_export_json(self):
        target = os.path.join(self.tmp, "cli-export.md")
        code, out, _err = self.run_cli([
            self.book, "--export-only", "text", "--export-format", "md",
            "-o", target, "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["count"], 1)
        self.assertTrue(os.path.isfile(target))

    def test_preview_json(self):
        code, out, _err = self.run_cli([
            self.book, "-e", "Fake", "--preview", "2", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertGreaterEqual(payload["count"], 1)
        self.assertFalse(payload["writes"])

    def test_cache_and_config_directories_are_applied(self):
        cache = os.path.join(self.tmp, "cli-cache")
        config = os.path.join(self.tmp, "cli-config")
        try:
            code, out, _err = self.run_cli([
                "--cache-dir", cache, "--config-dir", config,
                "--list-engines", "--json"])
            self.assertEqual(code, 0)
            json.loads(out)
            self.assertEqual(
                os.path.realpath(self.engine.TranslationCache.dir_path),
                os.path.realpath(cache))
            self.assertEqual(os.path.realpath(self.engine.config_dir),
                             os.path.realpath(config))
            self.assertTrue(os.path.isdir(os.path.join(cache, "cache")))
        finally:
            self.engine._agent_configure(
                config_dir_path=self.sandbox.config_dir,
                cache_dir_path=self.sandbox.cache_store,
                configure_log=False)


if __name__ == "__main__":
    unittest.main()
