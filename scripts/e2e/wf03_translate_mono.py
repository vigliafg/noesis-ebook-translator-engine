#!/usr/bin/env python3
"""WF03 — translate one chapter with the machine-readable CLI."""
import os

import harness as H

NAME = "WF03 — translate one chapter (--json)"
DESCRIPTION = ("CLI --json on a single chapter: output path, marker presence, "
               "source text preserved, metadata retained, scoped document set")


def run(env):
    engine, workspace = env.engine, env.workspace
    book = str(workspace.book)
    output = str(workspace.out / "chapter-it.epub")
    target = H.translation_target(engine, book)

    payload = H.read_json(engine, [
        book, "-o", output, "-e", "E2E", "-s", "English", "-t", "Italian",
        "--chapters", str(target["index"]), "--no-cache", "--json"],
        label="translate --json")
    H.check(payload["output"] == output, f"output={payload['output']}")
    H.check(payload["engine"] == "E2E", "engine was not echoed back")
    H.check(payload["source_lang"] == "English", "source language changed")
    H.check(payload["target_lang"] == "Italian", "target language changed")
    H.check(payload["chapters"] == [target["index"]],
            f"chapters={payload['chapters']}")
    H.check(payload["segments"] > 0, "nothing was reported as translated")
    H.check(os.path.isfile(output), "the output EPUB was not written")
    env.log(f"chapter {target['index']} ({target['name']}): "
            f"{payload['segments']} segments in {payload['seconds']}s")

    body = H.book_text(output)
    H.check(H.MARKER in body, "the translation marker is missing")
    H.check(body.count(H.MARKER) >= payload["segments"] // 2,
            "far fewer translated segments than planned")
    phrase = H.source_phrase(engine, book, chapter=target["index"])
    H.check(phrase in body, f"source text was lost: {phrase!r}")

    source_title = engine.book_meta(book)["title"]
    output_title = engine.book_meta(output)["title"]
    H.check(output_title == source_title,
            f"metadata changed: {source_title!r} -> {output_title!r}")
    H.check(H.doc_count(output) < H.doc_count(workspace.book),
            "the output was not restricted to the selected chapter")

    with open(output, "rb") as handle:
        H.check(handle.read(2) == b"PK", "the output is not a ZIP/EPUB")


if __name__ == "__main__":
    raise SystemExit(H.run_single(NAME, run))
