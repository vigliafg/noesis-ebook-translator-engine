"""Shared sandbox for the agent/MCP tests: temp config + cache + fake engine."""
from __future__ import annotations

import os
import tempfile

from tests.fixtures import build_sample_epub, load_engine, register_fake_engine


class EngineSandbox:
    """Isolate the shared engine module's config/cache in a temporary tree."""

    def __init__(self):
        self.tmp = tempfile.mkdtemp(prefix="noesis-agent-")
        self.engine = load_engine()

    def __enter__(self) -> "EngineSandbox":
        engine = self.engine
        self._config_dir = engine.config_dir
        self._plugin_dir = getattr(engine, "plugin_dir", engine.config_dir)
        cache = engine.TranslationCache
        self._cache = (cache.dir_path, cache.cache_path, cache.temp_path)
        config_dir = os.path.join(self.tmp, "config")
        cache_dir = os.path.join(self.tmp, "cache-store")
        os.makedirs(config_dir, exist_ok=True)
        self.config_dir = config_dir
        self.cache_store = cache_dir
        engine.config_dir = config_dir
        engine.plugin_dir = config_dir
        cache.dir_path = cache_dir
        cache.cache_path = os.path.join(cache_dir, "cache")
        cache.temp_path = os.path.join(cache_dir, "temp")
        os.makedirs(cache.cache_path, exist_ok=True)
        os.makedirs(cache.temp_path, exist_ok=True)
        engine.log.level = engine.Log.ERROR
        register_fake_engine(engine)
        self.book = build_sample_epub(os.path.join(self.tmp, "book.epub"))
        return self

    def __exit__(self, *exc_info) -> bool:
        engine = self.engine
        engine.config_dir = self._config_dir
        engine.plugin_dir = self._plugin_dir
        cache = engine.TranslationCache
        cache.dir_path, cache.cache_path, cache.temp_path = self._cache
        return False


def add_slow_engine(engine, delay: float = 0.2) -> str:
    """Register an engine that sleeps per segment (for cancel/busy tests)."""
    if any(getattr(item, "name", None) == "Slow" for item in engine.builtin_engines):
        return "Slow"

    class SlowEngine(engine.Base):
        name = "Slow"
        alias = "Slow"
        free = True
        need_api_key = False
        lang_codes = engine.Base.load_lang_codes(engine.google)
        endpoint = ""

        def translate(self, content):
            import time as _time
            _time.sleep(delay)
            return "SLOW<" + content + ">"

    engine.builtin_engines = tuple(engine.builtin_engines) + (SlowEngine,)
    return "Slow"
