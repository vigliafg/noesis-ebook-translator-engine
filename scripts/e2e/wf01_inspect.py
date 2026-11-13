#!/usr/bin/env python3
"""WF01 — discover and inspect the book (no translation, no network)."""
import harness as H

NAME = "WF01 — discover and inspect"
DESCRIPTION = ("capabilities, fake engines, chapter table, metadata, segment "
               "counts and empty cache")


def run(env):
    engine, workspace = env.engine, env.workspace
    book = str(workspace.book)

    caps = H.mcp(engine, "capabilities")
    H.check(caps["api_version"] == "1.0", f"api_version={caps['api_version']}")
    H.check(caps["root_confinement"] is True, "the MCP server must confine paths")
    H.check(str(workspace.dir) in caps["roots"],
            f"workspace missing from roots: {caps['roots']}")
    H.check(caps["read_only"] is False, "this workflow expects a writable server")
    env.log(f"server {caps['server']} {caps['engine_version']} "
            f"protocol {caps['mcp_protocol']}")

    engines = H.mcp(engine, "list_engines")
    names = {item["name"] for item in engines["engines"]}
    H.check({"E2E", "E2E-Slow"} <= names,
            f"fake engines missing from the catalog: {sorted(names)}")
    H.check(engines["count"] == len(engines["engines"]), "engine count mismatch")

    info = H.mcp(engine, "inspect_book", {"input": book, "engine": "E2E"})
    H.check(info["title"], "inspect_book returned no title")
    H.check(info["chapter_count"] >= 3,
            f"too few chapters: {info['chapter_count']}")
    H.check(info["segments"] > 50, f"too few segments: {info['segments']}")
    H.check(info["chars"] > 1000, f"too few characters: {info['chars']}")
    H.check(isinstance(info["cache"], dict), "cache block is not an object")
    H.check(info["interrupted_runs"] == [], "a fresh workspace has no interrupted run")
    env.log(f"{info['chapter_count']} chapters, {info['segments']} segments, "
            f"{info['chars']} chars")

    listing = H.mcp(engine, "list_chapters", {"input": book})
    indexes = [chapter["index"] for chapter in listing["chapters"]]
    H.check(indexes == list(range(1, listing["count"] + 1)),
            "chapter indexes are not contiguous and 1-based")
    H.check(all(chapter["name"] is not None for chapter in listing["chapters"]),
            "a chapter has no name")

    chapter = H.mcp(engine, "read_chapter", {"input": book, "chapter": 1,
                                             "limit": 200})
    H.check(chapter["text"], "read_chapter returned no text")
    H.check(chapter["total_chars"] >= len(chapter["text"]),
            "pagination totals are inconsistent")


if __name__ == "__main__":
    raise SystemExit(H.run_single(NAME, run))
