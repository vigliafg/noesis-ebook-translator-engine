#!/usr/bin/env python3
"""WF04 — bilingual output on one chapter (original above, translation below)."""
import harness as H

NAME = "WF04 — bilingual chapter (--position below)"
DESCRIPTION = ("run monolingual and bilingual on the same chapter, prove that "
               "the bilingual file keeps the original *and* the translation")


def run(env):
    engine, workspace = env.engine, env.workspace
    book = str(workspace.book)
    mono = str(workspace.out / "mono.epub")
    bilingual = str(workspace.out / "bi.epub")
    target = H.translation_target(engine, book)
    selection = ["--chapters", str(target["index"]), "--no-cache"]
    env.log(f"chapter {target['index']} ({target['name']}): "
            f"{target['segments']} segments")

    H.read_json(engine, [book, "-o", mono, "-e", "E2E", *selection,
                         "--json"], label="monolingual")
    payload = H.read_json(engine, [
        book, "-o", bilingual, "-e", "E2E", *selection,
        "--position", "below", "--json"], label="bilingual")
    H.check(payload["position"] == "below",
            f"position={payload['position']}")
    H.check(payload["chapters"] == [target["index"]],
            f"chapters={payload['chapters']}")

    mono_text = H.plain_text(mono)
    bi_text = H.plain_text(bilingual)
    H.check(len(bi_text) > 1.5 * len(mono_text),
            "the bilingual file is not substantially longer than the mono one")
    H.check(H.MARKER in bi_text and H.END_MARKER in bi_text,
            "the translation marker is missing from the bilingual file")

    phrase = H.source_phrase(engine, book, chapter=target["index"])
    H.check(mono_text.count(phrase) == 1,
            "the monolingual file should contain the original exactly once")
    H.check(bi_text.count(phrase) >= 2,
            "the bilingual file must keep the original and add the translation")

    H.check(H.doc_count(bilingual) == H.doc_count(mono),
            "mono and bilingual runs produced different document sets")
    H.check(H.doc_count(bilingual) < H.doc_count(workspace.book),
            "the bilingual run was not restricted to the selected chapter")
    env.log(f"mono {len(mono_text)} chars, bilingual {len(bi_text)} chars")


if __name__ == "__main__":
    raise SystemExit(H.run_single(NAME, run))
