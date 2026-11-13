#!/usr/bin/env python3
"""WF05 — translate one chapter through the MCP job API."""
import harness as H

NAME = "WF05 — translate one chapter (MCP job)"
DESCRIPTION = ("select a chapter, start a job with wait_seconds, verify the "
               "output only contains that chapter and that it is translated")


def run(env):
    engine, workspace = env.engine, env.workspace
    book = str(workspace.book)
    output = str(workspace.out / "chapter.epub")

    chapters = H.mcp(engine, "list_chapters", {"input": book})["chapters"]
    target = chapters[min(2, len(chapters) - 1)]
    H.check(target["index"] > 1, "the target chapter should not be the first")

    job = H.mcp(engine, "start_translation", {
        "input": book, "output": output, "engine": "E2E",
        "chapters": target["index"], "source_lang": "English",
        "target_lang": "Italian", "cache": False,
        "wait_seconds": 120,
    })
    H.check(job["state"] == "done", f"job ended as {job['state']}: {job['error']}")
    H.check(job["result"]["output"] == output, "job wrote another file")
    H.check(job["result"]["chapters"] == [target["index"]],
            f"job chapters={job['result']['chapters']}")

    H.check(H.doc_count(output) < H.doc_count(workspace.book),
            "the output was not restricted to the selected chapter")
    H.check(H.doc_count(output) >= 1, "the output has no document")

    read = H.mcp(engine, "read_chapter", {"input": output, "chapter": 1})
    H.check(H.MARKER in read["text"],
            "the selected chapter was not translated")
    H.check(read["total_chars"] > 0, "the selected chapter is empty")
    env.log(f"chapter {target['index']} {target['name']!r}: "
            f"{job['result']['segments']} segments, {H.doc_count(output)} docs")


if __name__ == "__main__":
    raise SystemExit(H.run_single(NAME, run))
