#!/usr/bin/env python3
"""WF06 — chapter selection: title, case, ambiguity and unknown chapters."""
import json
import os

import harness as H

NAME = "WF06 — chapter selection edge cases"
DESCRIPTION = ("resolve a unique title (case/space insensitive), reject an "
               "ambiguous title, and never write an empty book on a miss")


def run(env):
    engine, workspace = env.engine, env.workspace
    book = str(workspace.book)

    chapters = H.mcp(engine, "list_chapters", {"input": book})["chapters"]
    target = H.unique_chapter(chapters)
    needle = target["name"].lower()
    H.check(needle, "the sample has no chapter title to test")
    plan = H.mcp(engine, "plan_translation",
                 {"input": book, "engine": "E2E",
                  "chapters": f"  {target['name'].upper()}  "})
    H.check(plan["chapters"] == [target["index"]],
            f"case/space-insensitive title failed: {plan['chapters']}")

    management = [c for c in chapters if "management" in c["name"].lower()]
    if len(management) >= 2:
        info = H.mcp_error(engine, "plan_translation",
                           {"input": book, "engine": "E2E",
                            "chapters": "management"}, "ambiguous")
        H.check("list_chapters" in info["message"],
                "the ambiguity error should tell the agent what to do next")
    else:
        env.log("note: this book has no ambiguous titles, ambiguity check skipped")

    H.mcp_error(engine, "plan_translation",
                {"input": book, "engine": "E2E", "chapters": 999},
                "not_found")
    H.mcp_error(engine, "plan_translation",
                {"input": book, "engine": "E2E", "chapters": "zzz"},
                "not_found")

    output = os.path.join(str(workspace.out), "never.epub")
    code, stdout, stderr = H.cli(engine, [
        book, "-o", output, "-e", "E2E", "--chapters", "999", "--json"])
    H.check(code == 1, f"a bad selection should exit 1, got {code}")
    payload = json.loads(stdout)
    H.check(payload["ok"] is False, f"expected ok=false: {payload}")
    H.check(payload["error"]["code"] == "not_found",
            f"error code={payload['error']['code']}")
    H.check("matched nothing" in stderr, "the CLI should explain the failure")
    H.check(not os.path.exists(output),
            "a failed chapter selection must not create an output file")
    env.log(f"{len(chapters)} chapters; ambiguous pair: "
            f"{[c['index'] for c in management]}")


if __name__ == "__main__":
    raise SystemExit(H.run_single(NAME, run))
