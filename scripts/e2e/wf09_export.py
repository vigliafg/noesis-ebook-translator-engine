#!/usr/bin/env python3
"""WF09 — export the translated book and its assets in several formats."""
import os

import harness as H

NAME = "WF09 — export chapters, tables and figures"
DESCRIPTION = ("translate one chapter, export markdown/txt from it, and extract "
               "the Rosen table and figure with non-empty files")


def run(env):
    engine, workspace = env.engine, env.workspace
    book = str(workspace.book)
    translated = str(workspace.out / "translated.epub")
    target = H.translation_target(engine, book)

    job = H.mcp(engine, "start_translation", {
        "input": book, "output": translated, "engine": "E2E",
        "chapters": target["index"], "cache": False, "wait_seconds": 120,
    })
    H.check(job["state"] == "done", f"translation ended as {job['state']}")
    env.log(f"translated chapter {target['index']} "
            f"({job['result']['segments']} segments)")

    markdown = workspace.out / "book.md"
    payload = H.mcp(engine, "export_book", {
        "input": translated, "kind": "chapters", "format": "md",
        "output": str(markdown),
    })
    H.check(payload["count"] >= 1 and markdown.is_file(), "no markdown written")
    text = markdown.read_text(encoding="utf-8")
    H.check(H.MARKER in text, "the markdown export lost the translation")

    chapter_txt = workspace.out / "chapter.txt"
    scoped = H.mcp(engine, "export_book", {
        "input": translated, "kind": "chapters", "format": "txt",
        "output": str(chapter_txt), "chapters": 1,
    })
    H.check(scoped["count"] == 1, f"scoped export wrote {scoped['count']} files")
    H.check(chapter_txt.is_file() and chapter_txt.stat().st_size > 0,
            "the scoped text export is empty")

    tables = H.mcp(engine, "export_book", {
        "input": book, "kind": "tables", "format": "csv",
        "output": str(workspace.out / "tables"),
    })
    figures = H.mcp(engine, "export_book", {
        "input": book, "kind": "figures", "format": "img",
        "output": str(workspace.out / "figures"),
    })
    for path in tables["files"] + figures["files"]:
        H.check(os.path.getsize(path) > 0, f"empty export file: {path}")
    if env.is_rosen:
        H.check(tables["count"] >= 1, "the Rosen sample should carry a table")
        H.check(figures["count"] >= 1, "the Rosen sample should carry a figure")
    else:
        env.log(f"fallback book: {tables['count']} tables, "
                f"{figures['count']} figures")
    env.log(f"{payload['count']} markdown files, {tables['count']} tables, "
            f"{figures['count']} figures")


if __name__ == "__main__":
    raise SystemExit(H.run_single(NAME, run))
