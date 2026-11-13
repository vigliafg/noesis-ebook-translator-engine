#!/usr/bin/env python3
"""WF10 — real MCP stdio agent session (protocol, read-only, full translation)."""
import json
import os
import subprocess
import sys

import harness as H

NAME = "WF10 — MCP stdio agent session"
DESCRIPTION = ("two real subprocesses: the production server in read-only mode "
               "(protocol/resources/prompts) and the offline-engine wrapper "
               "translating + exporting over NDJSON")


def _talk(command, requests, environment, timeout=300):
    """Run one MCP stdio session and split responses from notifications."""
    payload = b"".join(H.ndjson(request) for request in requests)
    process = subprocess.Popen(
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, env=environment)
    stdout, stderr = process.communicate(payload, timeout=timeout)
    H.check(process.returncode == 0,
            f"MCP server exited {process.returncode}: "
            f"{stderr.decode('utf-8', 'replace')[-3000:]}")
    text = stdout.decode("utf-8")
    H.check("Content-Length" not in text,
            "stdout must use NDJSON, not Content-Length framing")
    H.check(b"jsonrpc" not in stderr,
            "protocol frames leaked to stderr")
    messages = [json.loads(line) for line in text.splitlines() if line.strip()]
    responses = {message["id"]: message
                 for message in messages if "id" in message}
    notifications = [message for message in messages if "id" not in message]
    return responses, notifications


def run(env):
    engine, workspace = env.engine, env.workspace
    book = str(workspace.book)
    environment = dict(os.environ)
    environment["NOESIS_CONFIG_DIR"] = str(workspace.dir / "stdio-config")
    environment["PYTHONIOENCODING"] = "utf-8"
    target = H.translation_target(engine, book)

    # ── Phase 1: the real binary, read-only: what any MCP client can do ──
    read_only = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                    "clientInfo": {"name": "e2e", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "inspect_book", "arguments": {"input": book}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "read_chapter",
                    "arguments": {"input": book, "chapter": 1, "limit": 120}}},
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call",
         "params": {"name": "plan_translation",
                    "arguments": {"input": book}}},
        {"jsonrpc": "2.0", "id": 6, "method": "resources/list"},
        {"jsonrpc": "2.0", "id": 7, "method": "prompts/list"},
        {"jsonrpc": "2.0", "id": 8, "method": "tools/call",
         "params": {"name": "start_translation",
                    "arguments": {"input": book,
                                  "output": str(workspace.out / "no.epub"),
                                  "engine": "Google(Free)New"}}},
    ]
    responses, _notifications = _talk(
        [sys.executable, str(H.ENGINE_PATH), "--mcp", "--root",
         str(workspace.dir), "--read-only"],
        read_only, environment)
    H.check(sorted(responses) == list(range(1, 9)),
            f"expected responses 1..8, got {sorted(responses)}")
    H.check(responses[1]["result"]["protocolVersion"] == "2025-06-18",
            "wrong protocol version")
    H.check(responses[1]["result"]["serverInfo"]["name"] ==
            "noesis-ebook-translator", "wrong server name")
    tools = [tool["name"] for tool in responses[2]["result"]["tools"]]
    H.check("inspect_book" in tools and "start_translation" in tools,
            f"missing tools: {tools}")
    info = responses[3]["result"]["structuredContent"]
    H.check(info["ok"] and info["title"], "inspect_book failed over stdio")
    H.check(responses[4]["result"]["structuredContent"]["text"],
            "read_chapter failed over stdio")
    H.check(responses[5]["result"]["structuredContent"]["segments"] > 0,
            "plan_translation failed over stdio")
    resources = [item["uri"] for item in responses[6]["result"]["resources"]]
    H.check(any("/book/" in uri for uri in resources),
            f"the inspected book is not a resource: {resources}")
    prompts = [item["name"] for item in responses[7]["result"]["prompts"]]
    H.check("translate_book" in prompts, f"missing prompts: {prompts}")
    blocked = responses[8]["result"]
    H.check(blocked.get("isError") is True, "read-only must refuse the write")
    H.check(blocked["structuredContent"]["error"]["code"] == "permission_denied",
            f"error={blocked['structuredContent']['error']}")
    H.check(not os.path.exists(str(workspace.out / "no.epub")),
            "read-only mode wrote an output file")

    # ── Phase 2: the same protocol with offline engines: full agent run ───
    translated = str(workspace.out / "stdio.epub")
    markdown = str(workspace.out / "stdio.md")
    session = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                    "clientInfo": {"name": "e2e", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "inspect_book",
                    "arguments": {"input": book, "engine": "E2E"}}},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "plan_translation",
                    "arguments": {"input": book, "engine": "E2E",
                                  "chapters": target["index"]}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "start_translation",
                    "arguments": {"input": book, "output": translated,
                                  "engine": "E2E",
                                  "chapters": target["index"],
                                  "cache": False, "wait_seconds": 120},
                    "_meta": {"progressToken": "wf10"}}},
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call",
         "params": {"name": "export_book",
                    "arguments": {"input": translated, "kind": "chapters",
                                  "format": "md", "output": markdown}}},
        {"jsonrpc": "2.0", "id": 6, "method": "tools/call",
         "params": {"name": "read_chapter",
                    "arguments": {"input": translated, "chapter": 1,
                                  "limit": 160}}},
        {"jsonrpc": "2.0", "id": 7, "method": "resources/list"},
    ]
    responses, notifications = _talk(
        [sys.executable, str(H.HERE / "mcp_server_fake.py"), "--root",
         str(workspace.dir), "--config-dir",
         str(workspace.dir / "stdio-config-2"), "--cache-dir",
         str(workspace.dir / "stdio-cache")],
        session, environment)
    H.check(sorted(responses) == list(range(1, 8)),
            f"expected responses 1..7, got {sorted(responses)}")
    inspected = responses[2]["result"]["structuredContent"]
    H.check(inspected["ok"] and inspected["title"],
            "inspect_book failed in the writable session")
    plan = responses[3]["result"]["structuredContent"]
    H.check(plan["ok"] and plan["segments"] > 0, "plan failed over stdio")
    H.check(plan["chapters"] == [target["index"]],
            f"plan lost the chapter selection: {plan['chapters']}")
    job = responses[4]["result"]["structuredContent"]
    H.check(job["state"] == "done", f"job over stdio ended as {job['state']}")
    H.check(job["result"]["output"] == translated, "wrong output over stdio")
    H.check(os.path.isfile(translated), "the stdio run wrote no EPUB")
    exported = responses[5]["result"]["structuredContent"]
    H.check(exported["ok"] and exported["count"] >= 1, "export failed over stdio")
    H.check(os.path.isfile(markdown), "the markdown export is missing")
    with open(markdown, encoding="utf-8") as handle:
        H.check(H.MARKER in handle.read(), "the exported text is not translated")
    chapter = responses[6]["result"]["structuredContent"]
    H.check(chapter["ok"] and H.MARKER in chapter["text"],
            "the translated chapter cannot be read back")
    book_resources = [item["uri"] for item in responses[7]["result"]["resources"]]
    H.check(any("/book/" in uri for uri in book_resources),
            f"the translated book is not a resource: {book_resources}")
    progress = [item for item in notifications
                if item.get("method") == "notifications/progress"]
    H.check(progress, "no progress notification reached the client")
    H.check(all(item["params"]["progressToken"] == "wf10"
                for item in progress), "wrong progress token")
    H.check(any(float(item["params"]["progress"]) >= 1.0 for item in progress),
            "progress never reached 100%")
    env.log(f"read-only: {len(tools)} tools; writable: {len(notifications)} "
            f"notifications, {job['result']['segments']} segments")


if __name__ == "__main__":
    raise SystemExit(H.run_single(NAME, run))
