"""Interoperability with the official MCP client (skipped if mcp is absent).

The runtime has **no** MCP dependency: this test is the only place that imports
the reference SDK, so CI can validate the hand-written server against it
without shipping it. Install it with ``pip install mcp`` and run the suite; the
test skips itself when the package is missing.
"""
import asyncio
import os
import tempfile
import unittest

from tests.fixtures import ENGINE_PATH

try:                                           # pragma: no cover - optional
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except Exception:                              # noqa: BLE001 - optional SDK
    ClientSession = None
    StdioServerParameters = None
    stdio_client = None


CORPUS = ENGINE_PATH.parent / "tests" / "data" / "corpus" / "descent_of_man.epub"


def _server_command() -> tuple[str, list]:
    python = os.environ.get("NOESIS_TEST_SERVER_PYTHON") or os.sys.executable
    return python, [str(ENGINE_PATH), "--mcp", "--root", str(CORPUS.parent)]


@unittest.skipUnless(ClientSession is not None, "mcp SDK not installed")
class TestMcpInterop(unittest.TestCase):
    def test_official_client_roundtrip(self):
        python, args = _server_command()
        env = dict(os.environ)
        env["NOESIS_CONFIG_DIR"] = tempfile.mkdtemp(prefix="noesis-interop-")
        env["PYTHONIOENCODING"] = "utf-8"

        async def run():
            params = StdioServerParameters(command=python, args=args, env=env)
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    init = await session.initialize()
                    tools = await session.list_tools()
                    capabilities = await session.call_tool("capabilities", {})
                    chapters = await session.call_tool(
                        "list_chapters", {"input": str(CORPUS)})
                    resources = await session.list_resources()
                    prompts = await session.list_prompts()
                    return init, tools, capabilities, chapters, resources, \
                        prompts

        init, tools, capabilities, chapters, resources, prompts = \
            asyncio.run(run())
        self.assertEqual(init.server_info.name, "noesis-ebook-translator")
        names = [tool.name for tool in tools.tools]
        self.assertIn("plan_translation", names)
        self.assertIn("start_translation", names)
        self.assertFalse(capabilities.is_error)
        self.assertTrue(capabilities.structured_content["ok"])
        self.assertFalse(chapters.is_error)
        structured = chapters.structured_content
        self.assertGreaterEqual(structured["count"], 10)
        self.assertTrue(any("/book/" in str(item.uri)
                            for item in resources.resources))
        self.assertTrue(any(item.name == "translate_book"
                            for item in prompts.prompts))


if __name__ == "__main__":
    unittest.main()
