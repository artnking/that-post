#!/usr/bin/env python3
"""Start That Post on 127.0.0.1:8790. Default: open Chrome. --no-open for autostart."""
from __future__ import annotations

import argparse
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8790
URL = f"http://{HOST}:{PORT}/"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--no-open", action="store_true", help="do not open a browser tab")
    args = p.parse_args()
    if HOST != "127.0.0.1":
        raise SystemExit("refusing to bind anything but 127.0.0.1")
    import uvicorn

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    config = uvicorn.Config(
        "gui_server:app",
        host=HOST,
        port=PORT,
        log_level="warning",
    )
    server = uvicorn.Server(config)

    import threading

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    ok = False
    for _ in range(50):
        try:
            with urllib.request.urlopen(URL + "api/stats", timeout=1) as r:
                if r.status == 200:
                    ok = True
                    break
        except urllib.error.HTTPError:
            time.sleep(0.1)
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.1)
    if not ok:
        raise SystemExit("server did not become ready on 127.0.0.1:8790")
    print(f"That Post  {URL}   Ctrl+C to stop")
    if not args.no_open:
        webbrowser.open(URL)
    try:
        while thread.is_alive():
            thread.join(0.5)
    except KeyboardInterrupt:
        server.should_exit = True
        print("stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
