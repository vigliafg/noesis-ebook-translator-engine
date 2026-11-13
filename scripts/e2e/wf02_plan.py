#!/usr/bin/env python3
"""WF02 — plan a translation before spending anything (tokens, cost, duration)."""
import harness as H

NAME = "WF02 — plan and estimate"
DESCRIPTION = ("whole-book and chapter plans, title→index resolution, cost "
               "fields, CLI --dry-run parity and an explicit not-found error")


def run(env):
    engine, workspace = env.engine, env.workspace
    book = str(workspace.book)

    whole = H.mcp(engine, "plan_translation", {"input": book, "engine": "E2E"})
    H.check(whole["segments"] > 0 and whole["chars"] > 0,
            "the plan is empty")
    H.check(whole["cost_usd"] is None, "E2E has no price, cost must be null")
    H.check(any("price unknown" in warning for warning in whole["warnings"]),
            "a null cost must be explained in warnings")
    H.check(whole["tokens"]["input"] > 0 and whole["tokens"]["output"] > 0,
            "token estimates are missing")
    H.check(whole["chapters"] == "all", "the whole-book plan should say 'all'")
    env.log(f"whole book: {whole['segments']} segments, {whole['chars']} chars, "
            f"{whole['tokens']['input']} input tokens")

    chapters = H.mcp(engine, "list_chapters", {"input": book})["chapters"]
    target = H.unique_chapter(chapters)
    part = H.mcp(engine, "plan_translation",
                 {"input": book, "engine": "E2E",
                  "chapters": target["name"]})
    H.check(part["chapters"] == [target["index"]],
            f"title did not resolve to the index: {part['chapters']}")
    H.check(0 < part["segments"] < whole["segments"],
            "the chapter plan was not scoped to the chapter")
    H.check(part["chars"] < whole["chars"], "the chapter plan has all the text")
    env.log(f"chapter {target['index']}: {part['segments']} segments")

    dry = H.read_json(engine, [book, "--dry-run"], label="CLI --dry-run")
    H.check(dry["segments"] == whole["segments"],
            f"CLI plan ({dry['segments']}) != MCP plan ({whole['segments']})")
    H.check(dry["chapters"] == "all", "CLI --dry-run lost the selection")
    H.check("output" not in dry, "--dry-run must not produce an output path")

    H.mcp_error(engine, "plan_translation",
                {"input": book, "engine": "E2E", "chapters": 999},
                "not_found")


if __name__ == "__main__":
    raise SystemExit(H.run_single(NAME, run))
