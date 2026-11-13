"""End-to-end MCP stdio test: spawn the engine as a real subprocess."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

from tests.agent_fixtures import EngineSandbox
from tests.fixtures import ENGINE_PATH, build_sample_epub


def _frame(payload) -> bytes:
    """One NDJSON frame, the MCP stdio wire format."""
    return json.dumps(payload).encode("utf-8") + b"\n"


def _parse_frames(raw: bytes) -> list:
    import json as _json

    return [_json.loads(line) for line in raw.decode("utf-8").splitlines()
            if line.strip()]


class TestMcpStdio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The sandbox is only used for its temporary directory; the engine runs
        # in its own process.
        cls.sandbox = EngineSandbox()
        cls.sandbox.__enter__()
        cls.tmp = cls.sandbox.tmp
        cls.book = build_sample_epub(os.path.join(cls.tmp, "stdio.epub"))

    @classmethod
    def tearDownClass(cls):
        cls.sandbox.__exit__(None, None, None)

    def test_stdio_session(self):
        config = os.path.join(self.tmp, "stdio-config")
        env = dict(os.environ)
        env["NOESIS_CONFIG_DIR"] = config
        env["PYTHONIOENCODING"] = "utf-8"
        payload = b"".join([
            _frame({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {"protocolVersion": "2025-06-18",
                               "capabilities": {},
                               "clientInfo": {"name": "test", "version": "0"}}}),
            _frame({"jsonrpc": "2.0", "method": "notifications/initialized"}),
            _frame({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
            _frame({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                    "params": {"name": "inspect_book",
                               "arguments": {"input": self.book}}}),
            _frame({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                    "params": {"name": "read_chapter",
                               "arguments": {"input": self.book,
                                             "chapter": 1, "limit": 8}}}),
            _frame({"jsonrpc": "2.0", "id": 5, "method": "resources/list"}),
        ])
        proc = subprocess.Popen(
            [sys.executable, str(ENGINE_PATH), "--mcp", "--root", self.tmp],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=env)
        out, err = proc.communicate(payload, timeout=180)
        self.assertEqual(proc.returncode, 0, err.decode("utf-8", "replace"))
        messages = _parse_frames(out)
        self.assertEqual([message.get("id") for message in messages],
                         [1, 2, 3, 4, 5])
        self.assertEqual(messages[0]["result"]["protocolVersion"],
                         "2025-06-18")
        self.assertGreaterEqual(len(messages[1]["result"]["tools"]), 10)
        inspected = messages[2]["result"]["structuredContent"]
        self.assertTrue(inspected["ok"])
        self.assertEqual(inspected["title"], "Engine Sample")
        chapter = messages[3]["result"]["structuredContent"]
        self.assertEqual(len(chapter["text"]), 8)
        self.assertGreaterEqual(len(messages[4]["result"]["resources"]), 2)

    def test_read_only_mode_refuses_writes(self):
        env = dict(os.environ)
        env["NOESIS_CONFIG_DIR"] = os.path.join(self.tmp, "ro-config")
        env["PYTHONIOENCODING"] = "utf-8"
        target = os.path.join(self.tmp, "ro.epub")
        payload = b"".join([
            _frame({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {"protocolVersion": "2025-06-18"}}),
            _frame({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                    "params": {"name": "start_translation",
                               "arguments": {"input": self.book,
                                             "output": target,
                                             "engine": "Google(Free)New"}}}),
        ])
        proc = subprocess.Popen(
            [sys.executable, str(ENGINE_PATH), "--mcp", "--root", self.tmp,
             "--read-only"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=env)
        out, err = proc.communicate(payload, timeout=120)
        self.assertEqual(proc.returncode, 0, err.decode("utf-8", "replace"))
        messages = _parse_frames(out)
        result = messages[1]["result"]
        self.assertTrue(result["isError"])
        self.assertEqual(result["structuredContent"]["error"]["code"],
                         "permission_denied")
        self.assertFalse(os.path.exists(target))


if __name__ == "__main__":
    unittest.main()
