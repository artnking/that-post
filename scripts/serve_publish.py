#!/usr/bin/env python3
"""Loopback preview of the Part 2 publish folder. Bind 127.0.0.1:8791 only."""
from __future__ import annotations

import argparse
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "127.0.0.1"
PORT = 8791


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dir", type=Path, default=ROOT / "publish")
    p.add_argument("--port", type=int, default=PORT)
    args = p.parse_args()
    publish = args.dir
    if not publish.exists():
        raise SystemExit("no publish folder — run python scripts/export_publish.py first")

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(publish), **kw)

        def guess_type(self, path):
            if str(path).endswith(".wasm"):
                return "application/wasm"
            if str(path).endswith(".mjs"):
                return "text/javascript"
            return super().guess_type(path)

        def log_message(self, fmt, *a):
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % a))

    httpd = ThreadingHTTPServer((HOST, args.port), Handler)
    print(f"That Post publish preview  http://{HOST}:{args.port}/   Ctrl+C to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
