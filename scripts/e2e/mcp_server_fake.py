#!/usr/bin/env python3
"""Test-only MCP stdio server with the offline ``E2E`` engines registered.

The production server (``engine --mcp``) only knows the real engines. An agent
cannot translate offline with a fake engine, so the E2E workflows start this
wrapper instead: it loads the same generated engine, registers ``E2E`` /
``E2E-Slow`` exactly like ``tests/fixtures.py``, and then calls the real
``serve_mcp`` — same transport, same tools, same validation.

    python scripts/e2e/mcp_server_fake.py --root /path/to/books
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import harness as H  # noqa: E402 - after the path setup


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", default=[])
    parser.add_argument("--read-only", action="store_true")
    parser.add_argument("--config-dir")
    parser.add_argument("--cache-dir")
    args = parser.parse_args(argv)
    engine = H.load_engine()          # registers E2E and E2E-Slow
    return engine.serve_mcp(
        roots=args.root, config_dir=args.config_dir,
        cache_dir=args.cache_dir, read_only=args.read_only)


if __name__ == "__main__":
    raise SystemExit(main())
