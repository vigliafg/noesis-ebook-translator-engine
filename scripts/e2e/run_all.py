#!/usr/bin/env python3
"""Run the ten Rosen end-to-end workflows (offline, no API key).

Usage::

    python scripts/e2e/run_all.py
    python scripts/e2e/run_all.py --only wf05 --only wf10 --verbose
    python scripts/e2e/run_all.py --book /path/to/another.epub --keep
    python scripts/e2e/run_all.py --list

The first run derives a small sample EPUB from the real Rosen text in
``../noesis-ebook-translator/corpus1`` (cached in ``scripts/e2e/.cache/``).
"""
from __future__ import annotations

import argparse
import importlib
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import harness as H  # noqa: E402 - after the path setup

WORKFLOWS = [
    "wf01_inspect",
    "wf02_plan",
    "wf03_translate_mono",
    "wf04_translate_bilingual",
    "wf05_chapter_job",
    "wf06_chapter_selection",
    "wf07_job_lifecycle",
    "wf08_cancel_resume",
    "wf09_export",
    "wf10_mcp_stdio",
]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", action="append", default=[],
                        metavar="NEEDLE",
                        help="run only workflows whose name matches (repeatable)")
    parser.add_argument("--book", help="EPUB to use instead of Rosen")
    parser.add_argument("--keep", action="store_true",
                        help="keep every temporary workspace")
    parser.add_argument("--force-sample", action="store_true",
                        help="rebuild the derived sample")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--list", action="store_true",
                        help="list the workflows and exit")
    args = parser.parse_args(argv)

    selected = [name for name in WORKFLOWS
                if not args.only or any(needle in name
                                        for needle in args.only)]
    if args.list:
        for name in selected:
            module = importlib.import_module(name)
            print(f"{name:28s} {module.NAME}")
            print(f"{'':28s} {module.DESCRIPTION}")
        return 0
    if not selected:
        parser.error("no workflow matched --only")

    engine = H.load_engine()
    source = H.find_source(args.book)
    sample = H.ensure_sample(engine, source, force=args.force_sample)
    print(f"source : {source}")
    print(f"sample : {sample} ({sample.stat().st_size // 1024} KB)")
    print(f"run    : {len(selected)} workflow(s)\n")

    failures = []
    started = time.time()
    for position, name in enumerate(selected, 1):
        module = importlib.import_module(name)
        workspace = H.Workspace(engine, sample, name)
        env = H.Env(engine, workspace, source, sample,
                    "rosen" in source.name.lower(), args.verbose)
        print(f"[{position}/{len(selected)}] {module.NAME}")
        workflow_started = time.time()
        try:
            module.run(env)
        except Exception as exc:                       # noqa: BLE001
            failures.append((module.NAME, exc))
            print(f"  FAIL  {exc}  ({time.time() - workflow_started:.2f}s)")
            if args.verbose or not isinstance(exc, H.WorkflowFailure):
                traceback.print_exc()
        else:
            print(f"  PASS  ({time.time() - workflow_started:.2f}s)")
        finally:
            workspace.close(keep=args.keep)

    elapsed = time.time() - started
    print(f"\n{'=' * 60}")
    if failures:
        print(f"{len(failures)}/{len(selected)} workflow(s) FAILED "
              f"in {elapsed:.1f}s")
        for name, exc in failures:
            print(f"  - {name}: {exc}")
        return 1
    print(f"all {len(selected)} workflow(s) passed in {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
