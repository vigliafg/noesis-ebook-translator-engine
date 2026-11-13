"""MCP protocol tests: dispatch, framing and the stdio loop (in memory)."""
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stderr

from tests.agent_fixtures import EngineSandbox


def _frame(payload) -> bytes:
    """One NDJSON frame (the MCP stdio wire format)."""
    return json.dumps(payload).encode("utf-8") + b"\n"


def _parse_frames(raw: bytes) -> list:
    return [json.loads(line) for line in raw.decode("utf-8").splitlines()
            if line.strip()]


class TestMcpProtocol(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sandbox = EngineSandbox()
        cls.sandbox.__enter__()
        cls.engine = cls.sandbox.engine
        cls.tmp = cls.sandbox.tmp
        cls.book = cls.sandbox.book
        cls.engine._agent_configure(
            roots=[cls.tmp], enforce_roots=True, configure_log=False)

    @classmethod
    def tearDownClass(cls):
        cls.engine._agent_configure(
            roots=None, read_only=False, enforce_roots=False,
            configure_log=False)
        cls.sandbox.__exit__(None, None, None)

    def call(self, message):
        return self.engine._mcp_dispatch(message)

    def tool(self, name, arguments=None, message_id=1):
        return self.call({
            "jsonrpc": "2.0", "id": message_id, "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        })

    # -- handshake ------------------------------------------------------
    def test_initialize(self):
        response = self.call({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18",
                       "capabilities": {}, "clientInfo": {"name": "t",
                                                          "version": "0"}},
        })
        result = response["result"]
        self.assertEqual(result["protocolVersion"], "2025-06-18")
        self.assertEqual(result["serverInfo"]["name"], "noesis-ebook-translator")
        self.assertIn("tools", result["capabilities"])
        self.assertIn("instructions", result)

    def test_initialize_negotiates_a_known_version(self):
        response = self.call({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-03-26"},
        })
        self.assertEqual(response["result"]["protocolVersion"], "2025-03-26")
        response = self.call({
            "jsonrpc": "2.0", "id": 2, "method": "initialize",
            "params": {"protocolVersion": "1999-01-01"},
        })
        self.assertEqual(response["result"]["protocolVersion"], "2025-06-18")

    def test_ping_and_unknown_method(self):
        self.assertEqual(self.call({"jsonrpc": "2.0", "id": 1,
                                    "method": "ping"})["result"], {})
        error = self.call({"jsonrpc": "2.0", "id": 2,
                           "method": "nope"})["error"]
        self.assertEqual(error["code"], -32601)
        self.assertIsNone(self.call({"jsonrpc": "2.0",
                                     "method": "nope"}))

    def test_batches_are_rejected(self):
        error = self.call([{"jsonrpc": "2.0", "id": 1, "method": "ping"}])
        self.assertEqual(error["error"]["code"], -32600)

    # -- tools ----------------------------------------------------------
    def test_tools_list(self):
        result = self.call({"jsonrpc": "2.0", "id": 1,
                            "method": "tools/list"})["result"]
        names = [tool["name"] for tool in result["tools"]]
        self.assertIn("capabilities", names)
        self.assertIn("plan_translation", names)
        self.assertIn("start_translation", names)
        for tool in result["tools"]:
            self.assertNotIn("handler", tool)
            self.assertIn("inputSchema", tool)
            self.assertIn("annotations", tool)
        by_name = {tool["name"]: tool for tool in result["tools"]}
        self.assertTrue(by_name["read_chapter"]["annotations"]["readOnlyHint"])
        self.assertFalse(by_name["start_translation"]["annotations"]
                         ["readOnlyHint"])
        self.assertTrue(by_name["dismiss_interrupted_run"]["annotations"]
                        ["destructiveHint"])

    def test_tools_call_capabilities(self):
        response = self.tool("capabilities")
        structured = response["result"]["structuredContent"]
        self.assertTrue(structured["ok"])
        self.assertTrue(structured["root_confinement"])
        self.assertEqual(structured["roots"], [self.tmp])

    def test_tools_call_read_chapter(self):
        response = self.tool("read_chapter",
                             {"input": self.book, "chapter": 1, "limit": 12})
        structured = response["result"]["structuredContent"]
        self.assertTrue(structured["ok"])
        self.assertEqual(len(structured["text"]), 12)
        self.assertTrue(structured["truncated"])
        self.assertIn("text", response["result"]["content"][0])

    def test_tools_call_error_is_reported_as_is_error(self):
        response = self.tool("read_chapter",
                             {"input": "/etc/hostname", "chapter": 1})
        result = response["result"]
        self.assertTrue(result["isError"])
        self.assertFalse(result["structuredContent"]["ok"])
        self.assertEqual(result["structuredContent"]["error"]["code"],
                         "permission_denied")

    def test_unknown_tool_is_a_protocol_error(self):
        error = self.tool("nope")["error"]
        self.assertEqual(error["code"], -32602)

    def test_progress_notifications_while_waiting(self):
        output = os.path.join(self.tmp, "progress-job.epub")
        out = io.BytesIO()
        connection = self.engine._McpConnection(out)
        response = self.engine._mcp_dispatch({
            "jsonrpc": "2.0", "id": 9, "method": "tools/call",
            "params": {
                "name": "start_translation",
                "arguments": {"input": self.book, "output": output,
                              "engine": "Fake", "cache": False,
                              "wait_seconds": 30},
                "_meta": {"progressToken": "tok-1"},
            },
        }, conn=connection)
        self.assertEqual(response["result"]["structuredContent"]["state"],
                         "done")
        notifications = [json.loads(line) for line in
                         out.getvalue().decode("utf-8").splitlines()
                         if line.strip()]
        self.assertTrue(notifications)
        for notification in notifications:
            self.assertEqual(notification["method"],
                             "notifications/progress")
            self.assertEqual(notification["params"]["progressToken"], "tok-1")
        self.assertTrue(any(float(item["params"]["progress"]) >= 1.0
                            for item in notifications))

    def test_configure_engine_tool(self):
        response = self.tool("configure_engine",
                             {"engine": "ChatGPT", "model": "gpt-4o-mini"})
        structured = response["result"]["structuredContent"]
        self.assertTrue(structured["ok"])
        self.assertTrue(structured["api_key_set"] is False)
        preference = self.engine.get_engine_preference("ChatGPT")
        self.assertEqual(preference.get("model"), "gpt-4o-mini")

    def test_cache_status_and_interrupted_runs_tools(self):
        status = self.tool("cache_status", {"input": self.book})
        structured = status["result"]["structuredContent"]
        self.assertTrue(structured["ok"])
        self.assertIn("coverage", structured)
        runs = self.tool("interrupted_runs", {})
        self.assertTrue(runs["result"]["structuredContent"]["ok"])

    def test_export_tables_tool(self):
        response = self.tool("export_book", {
            "input": self.book, "kind": "tables", "format": "csv",
            "output": os.path.join(self.tmp, "tables-out"),
        })
        self.assertFalse(response["result"].get("isError"))
        self.assertTrue(response["result"]["structuredContent"]["ok"])

    def test_plan_tool(self):
        response = self.tool("plan_translation",
                             {"input": self.book, "engine": "Fake",
                              "chapters": 1})
        structured = response["result"]["structuredContent"]
        self.assertTrue(structured["ok"])
        self.assertGreater(structured["segments"], 0)
        self.assertEqual(structured["chapters"], [1])

    def test_start_translation_with_wait(self):
        output = os.path.join(self.tmp, "mcp-job.epub")
        response = self.tool("start_translation", {
            "input": self.book, "output": output, "engine": "Fake",
            "cache": False, "wait_seconds": 30,
        })
        structured = response["result"]["structuredContent"]
        self.assertEqual(structured["state"], "done")
        self.assertTrue(os.path.isfile(output))

    # -- resources / prompts -------------------------------------------
    def test_resources(self):
        book_uri = "noesis://book/" + self.engine._agent_register_book(self.book)
        listing = self.call({"jsonrpc": "2.0", "id": 1,
                             "method": "resources/list"})["result"]
        uris = [item["uri"] for item in listing["resources"]]
        self.assertIn("noesis://capabilities", uris)
        self.assertIn("noesis://engines", uris)
        self.assertIn(book_uri, uris)
        self.assertIn(book_uri + "/toc", uris)
        content = self.call({
            "jsonrpc": "2.0", "id": 2, "method": "resources/read",
            "params": {"uri": book_uri},
        })["result"]["contents"][0]
        self.assertEqual(content["mimeType"], "application/json")
        self.assertIn("Engine Sample", content["text"])

        templates = self.call({"jsonrpc": "2.0", "id": 3,
                               "method": "resources/templates/list"})
        self.assertIn("chapter", templates["result"]["resourceTemplates"][0]
                      ["uriTemplate"])

    def test_unknown_resource(self):
        error = self.call({"jsonrpc": "2.0", "id": 1, "method": "resources/read",
                           "params": {"uri": "noesis://nope"}})["error"]
        self.assertEqual(error["code"], -32602)

    def test_prompts(self):
        listing = self.call({"jsonrpc": "2.0", "id": 1,
                             "method": "prompts/list"})["result"]
        names = [item["name"] for item in listing["prompts"]]
        self.assertIn("translate_book", names)
        prompt = self.call({
            "jsonrpc": "2.0", "id": 2, "method": "prompts/get",
            "params": {"name": "translate_book",
                       "arguments": {"input": self.book,
                                     "target_lang": "German"}},
        })["result"]
        text = prompt["messages"][0]["content"]["text"]
        self.assertIn("German", text)
        self.assertIn("plan_translation", text)

    # -- manifest parity ------------------------------------------------
    def test_describe_matches_tools_list(self):
        describe = self.engine.agent_describe()
        listing = self.call({"jsonrpc": "2.0", "id": 1,
                             "method": "tools/list"})["result"]
        self.assertEqual(describe["tools"], listing["tools"])
        self.assertEqual(describe["resources"][0]["uri"],
                         "noesis://capabilities")

    # -- framing --------------------------------------------------------
    def test_read_message_accepts_content_length_framing(self):
        payload = {"jsonrpc": "2.0", "id": 7, "method": "ping"}
        body = json.dumps(payload).encode("utf-8")
        data = b"Content-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body
        stream = io.BytesIO(data)
        self.assertEqual(self.engine._mcp_read_message(stream), payload)
        self.assertIsNone(self.engine._mcp_read_message(stream))

    def test_read_message_ndjson(self):
        stream = io.BytesIO(b'{"jsonrpc":"2.0","id":1,"method":"ping"}\n')
        self.assertEqual(self.engine._mcp_read_message(stream)["method"], "ping")
        self.assertIsNone(self.engine._mcp_read_message(stream))

    def test_stdio_loop(self):
        data = b"".join([
            _frame({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {"protocolVersion": "2025-06-18"}}),
            _frame({"jsonrpc": "2.0", "method": "notifications/initialized"}),
            _frame({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
        ])
        out = io.BytesIO()
        rc = self.engine.serve_mcp(
            roots=[self.tmp], stdin=io.BytesIO(data), stdout=out,
            verbose=False)
        self.assertEqual(rc, 0)
        messages = _parse_frames(out.getvalue())
        self.assertEqual([message["id"] for message in messages], [1, 2])
        self.assertEqual(messages[0]["result"]["protocolVersion"],
                         "2025-06-18")
        self.assertTrue(messages[1]["result"]["tools"])

    def test_serve_mcp_refuses_a_terminal(self):
        class _Terminal:
            def isatty(self):
                return True

        original = sys.stdin
        sys.stdin = _Terminal()
        try:
            with redirect_stderr(io.StringIO()) as err:
                rc = self.engine.serve_mcp(roots=[self.tmp])
        finally:
            sys.stdin = original
        self.assertEqual(rc, 2)
        self.assertIn("--mcp", err.getvalue())


if __name__ == "__main__":
    unittest.main()
