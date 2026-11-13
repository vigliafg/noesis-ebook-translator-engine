"""AgentAPI tests: discovery, planning, read/export and the job lifecycle."""
import os
import unittest
import zipfile

from tests.agent_fixtures import EngineSandbox, add_slow_engine


class TestAgentApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sandbox = EngineSandbox()
        cls.sandbox.__enter__()
        cls.engine = cls.sandbox.engine
        cls.tmp = cls.sandbox.tmp
        cls.book = cls.sandbox.book
        cls.engine._agent_configure(
            roots=[cls.tmp], enforce_roots=False, configure_log=False)

    @classmethod
    def tearDownClass(cls):
        cls.engine._agent_configure(
            roots=None, read_only=False, enforce_roots=False,
            configure_log=False)
        cls.sandbox.__exit__(None, None, None)

    # -- discovery ------------------------------------------------------
    def test_capabilities(self):
        payload = self.engine.agent_capabilities()
        self.assertEqual(payload["api_version"], "1.0")
        self.assertTrue(payload["cache_dir"].startswith(self.tmp))
        self.assertGreater(payload["engines"], 10)
        self.assertIn("settings_schema", payload)
        self.assertTrue(payload["features"]["jobs"])

    def test_list_engines_includes_the_fake_engine(self):
        payload = self.engine.agent_list_engines()
        names = {item["name"] for item in payload["engines"]}
        self.assertIn("Fake", names)
        fake = next(item for item in payload["engines"]
                    if item["name"] == "Fake")
        self.assertTrue(fake["free"])
        self.assertFalse(fake["need_api_key"])

    def test_list_chapters(self):
        payload = self.engine.agent_list_chapters(self.book)
        self.assertGreaterEqual(payload["count"], 1)
        self.assertEqual(payload["chapters"][0]["index"], 1)
        self.assertTrue(payload["chapters"][0]["href"])
        self.assertTrue(payload["book_id"])

    def test_inspect_book(self):
        payload = self.engine.agent_inspect_book(self.book, engine="Fake")
        self.assertEqual(payload["title"], "Engine Sample")
        self.assertGreaterEqual(payload["segments"], 1)
        self.assertGreaterEqual(payload["chars"], 1)
        self.assertIsInstance(payload["cache"], dict)
        self.assertIsInstance(payload["interrupted_runs"], list)

    # -- reading --------------------------------------------------------
    def test_read_chapter_and_pagination(self):
        full = self.engine.agent_read_chapter(self.book, 1)
        self.assertIn("Hello world", full["text"])
        self.assertFalse(full["truncated"])
        self.assertIsNone(full["next_offset"])

        chunk = self.engine.agent_read_chapter(self.book, 1, offset=0, limit=10)
        self.assertEqual(len(chunk["text"]), 10)
        self.assertTrue(chunk["truncated"])
        self.assertEqual(chunk["next_offset"], 10)

        tail = self.engine.agent_read_chapter(
            self.book, 1, offset=chunk["next_offset"], limit=10)
        self.assertNotEqual(tail["text"], chunk["text"])

    def test_read_unknown_chapter(self):
        with self.assertRaises(self.engine.AgentError) as ctx:
            self.engine.agent_read_chapter(self.book, 99)
        self.assertEqual(ctx.exception.code, "not_found")

    # -- planning -------------------------------------------------------
    def test_plan_translation(self):
        payload = self.engine.agent_plan(self.book, engine="Fake")
        self.assertGreater(payload["segments"], 0)
        self.assertGreater(payload["chars"], 0)
        self.assertEqual(payload["cost_usd"], None)   # Fake has no price
        self.assertIn("price unknown", " ".join(payload["warnings"]))
        self.assertTrue(payload["tokens"]["estimated"])
        self.assertTrue(payload["per_chapter"])

    def test_plan_cost_uses_the_bundled_catalog(self):
        price = self.engine.provider_catalog.price("openai", "gpt-4o-mini")
        if price is None:
            self.skipTest("model not in the bundled price snapshot")
        payload = self.engine.agent_plan(
            self.book, engine="ChatGPT", model="gpt-4o-mini")
        self.assertEqual(payload["provider"], "openai")
        self.assertEqual(payload["price_per_million_usd"],
                         {"input": price[0], "output": price[1]})
        self.assertIsNotNone(payload["cost_usd"])
        self.assertGreater(payload["cost_usd"], 0)

    def test_unknown_engine_is_rejected(self):
        with self.assertRaises(self.engine.AgentError) as ctx:
            self.engine.agent_plan(self.book, engine="NoSuchEngine")
        self.assertEqual(ctx.exception.code, "unknown_engine")

    # -- chapter-scoped workflow ---------------------------------------
    def _corpus(self):
        from tests.fixtures import ROOT

        return str(ROOT / "tests" / "data" / "corpus" / "descent_of_man.epub")

    def test_plan_scopes_to_the_selected_chapter(self):
        whole = self.engine.agent_plan(self._corpus(), engine="Fake")
        one = self.engine.agent_plan(self._corpus(), engine="Fake",
                                     chapters="2")
        self.assertGreater(whole["segments"], one["segments"])
        self.assertEqual(one["chapters"], [2])
        self.assertGreater(one["segments"], 0)

    def test_chapter_selection_by_unique_title(self):
        plan = self.engine.agent_plan(
            self._corpus(), engine="Fake",
            chapters="Preface to the Second Edition.")
        self.assertEqual(plan["chapters"], [3])

    def test_ambiguous_chapter_title_is_rejected(self):
        with self.assertRaises(self.engine.AgentError) as ctx:
            self.engine.agent_plan(self._corpus(), engine="Fake",
                                   chapters="contents")
        self.assertEqual(ctx.exception.code, "ambiguous")

    def test_unknown_chapter_selection_is_rejected(self):
        with self.assertRaises(self.engine.AgentError) as ctx:
            self.engine.agent_plan(self._corpus(), engine="Fake",
                                   chapters="999")
        self.assertEqual(ctx.exception.code, "not_found")
        with self.assertRaises(self.engine.AgentError) as ctx:
            self.engine.agent_translate_now({
                "input": self._corpus(), "engine": "Fake",
                "chapters": "no such chapter", "cache": False,
            })
        self.assertEqual(ctx.exception.code, "not_found")

    def test_translate_one_chapter_only(self):
        output = os.path.join(self.tmp, "chapter-2.epub")
        payload = self.engine.agent_translate_now({
            "input": self._corpus(), "output": output, "engine": "Fake",
            "chapters": "2", "cache": False,
        })
        self.assertEqual(payload["chapters"], [2])
        self.assertEqual(payload["target_lang"], "Italian")
        self.assertTrue(os.path.isfile(output))
        with zipfile.ZipFile(output) as archive:
            body = "\n".join(
                archive.read(name).decode("utf-8", "replace")
                for name in archive.namelist()
                if name.endswith((".xhtml", ".html")))
        self.assertIn("IT&lt;", body)

    # -- path policy ----------------------------------------------------
    def test_roots_confine_paths_only_when_enforced(self):
        self.engine._agent_configure(
            roots=[self.tmp], enforce_roots=True, configure_log=False)
        try:
            with self.assertRaises(self.engine.AgentError) as ctx:
                self.engine.agent_list_chapters("/etc/hostname")
            self.assertEqual(ctx.exception.code, "permission_denied")

            link = os.path.join(self.tmp, "escape.epub")
            if not os.path.lexists(link):
                os.symlink("/etc/hostname", link)
            with self.assertRaises(self.engine.AgentError):
                self.engine.agent_list_chapters(link)
        finally:
            self.engine._agent_configure(
                roots=[self.tmp], enforce_roots=False, configure_log=False)

    def test_cache_store_is_allowed_outside_the_book_roots(self):
        self.engine._agent_configure(
            roots=[self.tmp], enforce_roots=True, configure_log=False)
        try:
            probe = os.path.join(
                self.engine.TranslationCache.cache_path, "probe.db")
            with open(probe, "wb"):
                pass
            self.assertEqual(self.engine._agent_cache_path(probe), probe)
            with self.assertRaises(self.engine.AgentError) as ctx:
                self.engine._agent_cache_path("/etc/hostname")
            self.assertEqual(ctx.exception.code, "permission_denied")
        finally:
            self.engine._agent_configure(
                roots=[self.tmp], enforce_roots=False, configure_log=False)

    def test_missing_file(self):
        with self.assertRaises(self.engine.AgentError) as ctx:
            self.engine.agent_list_chapters(
                os.path.join(self.tmp, "missing.epub"))
        self.assertEqual(ctx.exception.code, "not_found")

    # -- export ---------------------------------------------------------
    def test_export_text(self):
        target = os.path.join(self.tmp, "export.txt")
        payload = self.engine.agent_export(
            self.book, kind="chapters", fmt="txt", output=target)
        self.assertEqual(payload["count"], 1)
        self.assertTrue(os.path.isfile(target))
        with open(target, encoding="utf-8") as handle:
            self.assertIn("Hello world", handle.read())

    def test_export_figures_treats_a_file_output_as_its_directory(self):
        from tests.fixtures import ROOT

        corpus = ROOT / "tests" / "data" / "corpus" / "descent_of_man.epub"
        target = os.path.join(self.tmp, "figures", "figure.png")
        payload = self.engine.agent_export(
            str(corpus), kind="figures", fmt="img", output=target)
        self.assertGreaterEqual(payload["count"], 1)
        for path in payload["files"]:
            self.assertEqual(os.path.dirname(path),
                             os.path.join(self.tmp, "figures"))
            self.assertTrue(os.path.isfile(path))

    # -- jobs -----------------------------------------------------------
    def test_translate_now(self):
        output = os.path.join(self.tmp, "now.epub")
        payload = self.engine.agent_translate_now({
            "input": self.book, "output": output, "engine": "Fake",
            "cache": False,
        })
        self.assertTrue(os.path.isfile(output))
        self.assertEqual(payload["output"], output)
        self.assertGreaterEqual(payload["segments"], 1)

    def test_job_lifecycle_and_cancel(self):
        engine = self.engine
        add_slow_engine(engine, delay=0.15)
        output = os.path.join(self.tmp, "job.epub")
        job = engine.agent_start_translation({
            "input": self.book, "output": output, "engine": "Slow",
            "cache": False,
        })
        self.assertIn(job["state"], ("queued", "running"))

        with self.assertRaises(engine.AgentError) as ctx:
            engine.agent_start_translation({
                "input": self.book, "output": output + ".2",
                "engine": "Slow", "cache": False,
            })
        self.assertEqual(ctx.exception.code, "busy")

        snapshot = engine.agent_cancel_job(job["job_id"], wait_seconds=10)
        self.assertEqual(snapshot["state"], "cancelled")
        self.assertIsNone(snapshot["result"])
        self.assertTrue(any(event["type"] == "cancel"
                            for event in snapshot["events"]))

    def test_job_completes_and_reports_events(self):
        output = os.path.join(self.tmp, "job-ok.epub")
        job = self.engine.agent_start_translation({
            "input": self.book, "output": output, "engine": "Fake",
            "cache": False,
        })
        snapshot = self.engine.agent_collect_job(job["job_id"],
                                                 wait_seconds=30)
        self.assertEqual(snapshot["state"], "done")
        self.assertEqual(snapshot["result"]["output"], output)
        self.assertTrue(os.path.isfile(output))
        self.assertTrue(any(event["type"] == "plan"
                            for event in snapshot["events"]))
        # Cursor paging returns only the new events.
        cursor = snapshot["next_cursor"]
        later = self.engine.agent_job_status(job["job_id"], after=cursor)
        self.assertEqual(later["events"], [])

    def test_unknown_job(self):
        with self.assertRaises(self.engine.AgentError) as ctx:
            self.engine.agent_job_status("does-not-exist")
        self.assertEqual(ctx.exception.code, "not_found")


if __name__ == "__main__":
    unittest.main()
