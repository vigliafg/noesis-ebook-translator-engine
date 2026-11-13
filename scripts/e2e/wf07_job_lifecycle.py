#!/usr/bin/env python3
"""WF07 — job lifecycle: start, poll with a cursor, collect, cancel, busy."""
import time

import harness as H

NAME = "WF07 — job lifecycle and polling"
DESCRIPTION = ("start_translation without blocking, incremental job_status "
               "events, collect_job, cursor semantics and the single-job rule")


def run(env):
    engine, workspace = env.engine, env.workspace
    book = str(workspace.book)
    output = str(workspace.out / "job.epub")
    target = H.translation_target(engine, book)

    job = H.mcp(engine, "start_translation", {
        "input": book, "output": output, "engine": "E2E",
        "chapters": target["index"], "cache": False, "wait_seconds": 0,
    })
    job_id = job["job_id"]
    H.check(job_id, "start_translation returned no job id")
    H.check(job["state"] in ("queued", "running", "done"),
            f"unexpected initial state {job['state']}")

    events, cursor, snapshot = [], 0, job
    deadline = time.time() + 120
    while snapshot["state"] in ("queued", "running") and time.time() < deadline:
        snapshot = H.mcp(engine, "job_status",
                         {"job_id": job_id, "after": cursor})
        events.extend(snapshot["events"])
        cursor = snapshot["next_cursor"]
        time.sleep(0.01)
    H.check(snapshot["state"] == "done",
            f"job ended as {snapshot['state']}: {snapshot['error']}")
    H.check(any(event["type"] == "plan" for event in events),
            "no plan event was recorded")
    H.check(any(event["type"] == "progress" for event in events),
            "no progress event was recorded")
    H.check(snapshot["progress"]["fraction"] >= 1.0,
            f"progress={snapshot['progress']}")

    final = H.mcp(engine, "collect_job", {"job_id": job_id, "wait_seconds": 5})
    H.check(final["state"] == "done", "collect_job disagrees with the job")
    H.check(final["result"]["output"] == output, "collect_job lost the output")
    later = H.mcp(engine, "job_status",
                  {"job_id": job_id, "after": final["next_cursor"]})
    H.check(later["events"] == [], "the cursor returned old events")
    env.log(f"job {job_id}: {len(events)} events, "
            f"{snapshot['result']['segments']} segments")

    slow = H.mcp(engine, "start_translation", {
        "input": book, "output": str(workspace.out / "slow.epub"),
        "engine": "E2E-Slow", "chapters": target["index"],
        "cache": False, "wait_seconds": 0,
    })
    H.mcp_error(engine, "start_translation", {
        "input": book, "output": str(workspace.out / "busy.epub"),
        "engine": "E2E-Slow", "chapters": target["index"], "cache": False,
    }, "busy")
    cancelled = H.mcp(engine, "cancel_job",
                      {"job_id": slow["job_id"], "wait_seconds": 30})
    H.check(cancelled["state"] == "cancelled",
            f"cancel_job ended as {cancelled['state']}")


if __name__ == "__main__":
    raise SystemExit(H.run_single(NAME, run))
