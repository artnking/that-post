#!/usr/bin/env python3
"""Part 1 first run: venv, optional X ingest, local search page.

If data/ideas.sqlite already has posts (copied from another machine), skip
X login, download, and enrich. Never prints tokens or secrets.
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from getpass import getpass
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
REQ = ROOT / "requirements.txt"
VENV = ROOT / ".venv"


def venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def in_our_venv() -> bool:
    try:
        return Path(sys.prefix).resolve() == VENV.resolve()
    except OSError:
        return False


def run(cmd: list[str], **kw) -> int:
    print("+", " ".join(str(c) for c in cmd))
    return subprocess.call(cmd, **kw)


def ensure_venv() -> None:
    if in_our_venv():
        return
    py = venv_python()
    if not py.exists():
        print("Creating .venv …")
        rc = run([sys.executable, "-m", "venv", str(VENV)])
        if rc != 0:
            raise SystemExit(
                "Could not create .venv. Need Python 3.11+. "
                "On Linux Mint/Ubuntu: sudo apt install python3-venv python3-pip"
            )
    print("Re-running inside .venv …")
    raise SystemExit(run([str(py), str(Path(__file__).resolve()), *sys.argv[1:]]))


def db_rows(db: Path) -> int:
    if not db.exists():
        return 0
    try:
        return int(sqlite3.connect(str(db)).execute("SELECT COUNT(*) FROM bookmarks").fetchone()[0])
    except sqlite3.Error:
        return 0


def start_search() -> int:
    gui = [sys.executable, str(SCRIPTS / "launch_gui.py")]
    print()
    print("Starting the local search page …")
    print("  http://127.0.0.1:8790/")
    if os.name == "nt":
        print("A second window will stay open for the search page. Leave it running.")
        subprocess.Popen(gui, creationflags=subprocess.CREATE_NEW_CONSOLE)
        print()
        print("http://127.0.0.1:8790/")
        return 0
    return run(gui)


def main() -> int:
    if sys.version_info < (3, 11):
        raise SystemExit(f"Python 3.11+ required (this is {sys.version.split()[0]})")
    ensure_venv()
    sys.path.insert(0, str(SCRIPTS))
    from paths import DATA, DB, OAUTH_FILE, load_env  # noqa: E402

    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "seed").mkdir(exist_ok=True)

    print("Installing Python packages …")
    rc = run([sys.executable, "-m", "pip", "install", "-q", "-r", str(REQ)])
    if rc != 0:
        return rc

    rows = db_rows(DB)
    if rows > 0:
        print()
        print(f"Found an existing index ({rows} posts). Skipping X download and AI.")
        print("To refresh later:  .venv\\Scripts\\python scripts\\sync_x.py")
        return start_search()

    if not OAUTH_FILE.exists():
        print()
        print(f"Missing {OAUTH_FILE}")
        print("Either copy ideas.sqlite into data\\ (skip download), or copy")
        print("x_oauth.json into data\\ and run this again.")
        print("Do not paste secrets into chat.")
        return 2

    env = load_env()
    if not env.get("X_BEARER_TOKEN"):
        print()
        print("A browser window will ask you to sign in to X and click Allow.")
        print("That is X’s login page. This script never asks for your password.")
        rc = run([sys.executable, str(SCRIPTS / "auth_x.py")])
        if rc != 0:
            print("X login did not finish. Run install again and Allow within 3 minutes.")
            return rc
    else:
        print("X login already saved in data/.env (value not printed).")

    print()
    print("Downloading recent bookmarks, posts, and likes …")
    rc = run([sys.executable, str(SCRIPTS / "ingest_bookmarks.py"), "--all"])
    rows = db_rows(DB)
    if rows == 0:
        print("Ingest failed and the index is empty.")
        return rc or 1
    if rc != 0:
        print(f"Ingest stopped early, but {rows} posts are already in the index.")

    env = load_env()
    if not env.get("OPENROUTER_API_KEY"):
        print()
        print("OpenRouter makes search-by-idea work (gemini-3.5-flash-lite).")
        print("Add $5 of credits at https://openrouter.ai/ — this run uses well under $1.")
        print("Paste an API key once (nothing shows). Enter skips — you can run enrich.bat later.")
        try:
            key = getpass("OPENROUTER_API_KEY: ").strip()
        except EOFError:
            key = ""
        if key:
            from paths import upsert_env

            upsert_env("OPENROUTER_API_KEY", key)
            env = load_env()

    if env.get("OPENROUTER_API_KEY"):
        print()
        print("Summarizing posts with google/gemini-3.5-flash-lite …")
        run([sys.executable, str(SCRIPTS / "enrich_bookmarks.py"), "--limit", "5000"])
    else:
        print("No OpenRouter key — skipping summaries. Run enrich.bat later.")

    return start_search()


if __name__ == "__main__":
    raise SystemExit(main())
