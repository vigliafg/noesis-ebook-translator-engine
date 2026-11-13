#!/usr/bin/env python3
"""WF08 — cancel mid-run, keep the cache, simulate a crash, resume with --resume."""
import json
import os
import time

import harness as H

NAME = "WF08 — cancel, crash marker and resume"
DESCRIPTION = ("cancel a one-chapter job, prove the cache kept the paid work, "
               "mark it as interrupted, then resume it from the CLI")


def run(env):
    engine, workspace = env.engine, env.workspace
    book = str(workspace.book)
    output = str(workspace.out / "resume.epub")
    target = H.translation_target(engine, book)
    env.log(f"chapter {target['index']} ({target['name']}): "
            f"{target['segments']} segments")

    # Make the chapter last ~1.5s whatever its size: long enough to cancel,
    # short enough to resume quickly (Rosen and the fallback corpus).
    delay = max(0.005, 1.5 / max(int(target["segments"]), 1))
    previous = os.environ.get("NOESIS_E2E_DELAY")
    os.environ["NOESIS_E2E_DELAY"] = f"{delay:.4f}"
    try:
        job = H.mcp(engine, "start_translation", {
            "input": book, "output": output, "engine": "E2E-Slow",
            "chapters": target["index"], "cache": True, "wait_seconds": 0,
        })
        time.sleep(0.15)
        snapshot = H.mcp(engine, "cancel_job",
                         {"job_id": job["job_id"], "wait_seconds": 60})
        H.check(snapshot["state"] == "cancelled",
                f"job ended as {snapshot['state']}")
        status = H.mcp(engine, "cache_status", {"input": book})
        H.check(status["segments_total"] > 0,
                "the cancelled run left no plan in the cache")
        done_before = status["segments_done"]
        env.log(f"cancelled with {done_before}/"
                f"{status['segments_total']} segments cached")
        if done_before == 0:
            env.log("note: the cancel landed before the first segment landed")

        database = H.simulate_crash(engine)
        runs = H.mcp(engine, "interrupted_runs", {"input": book})
        H.check(runs["count"] >= 1, "the crashed run was not detected")
        run = runs["runs"][0]
        H.check(os.path.abspath(run["input_path"]) == os.path.abspath(book),
                "interrupted_runs reported another book")
        H.check(run["engine"] == "E2E-Slow", f"engine={run['engine']}")
        H.check(run["output_path"] == output, f"output={run['output_path']}")
        H.check(run["chapters"] == [target["index"]],
                f"chapters={run['chapters']}")

        code, stdout, stderr = H.cli(engine, [book, "--resume", "--json"])
        H.check(code == 0, f"--resume failed with rc={code}\n{stderr[-3000:]}")
        H.check("Resuming" in stderr, f"no resume banner: {stderr[:300]}")
        payload = json.loads(stdout)
        H.check(payload["output"] == output,
                f"--resume wrote elsewhere: {payload['output']}")
        H.check(payload["engine"] == "E2E-Slow",
                f"--resume lost the engine: {payload['engine']}")
        H.check(payload["chapters"] == [target["index"]],
                f"--resume lost the chapter: {payload['chapters']}")
        H.check(os.path.isfile(output), "the resumed output was not written")

        status = H.mcp(engine, "cache_status", {"input": book})
        H.check(status["segments_done"] >= done_before,
                "the cache shrank after the resume")
        H.check(status["coverage"] is not None and status["coverage"] > 0.99,
                f"coverage after resume={status['coverage']}")
        runs_after = H.mcp(engine, "interrupted_runs", {"input": book})
        H.check(runs_after["count"] == 0,
                "the finished run is still offered as interrupted")
        env.log(f"resumed from {database.name}; coverage "
                f"{status['segments_done']}/{status['segments_total']}")
    finally:
        if previous is None:
            os.environ.pop("NOESIS_E2E_DELAY", None)
        else:
            os.environ["NOESIS_E2E_DELAY"] = previous


if __name__ == "__main__":
    raise SystemExit(H.run_single(NAME, run))
