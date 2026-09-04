#!/usr/bin/env python3
"""Stand-alone enrich: OpenRouter + gemini-3.5-flash-lite. Resume-safe.

Run after install.bat. Does not touch X login. Never prints the API key.
"""
from __future__ import annotations

import os
import subprocess
import sys
from getpass import getpass
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
VENV = ROOT / ".venv"


def venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def main() -> int:
    sys.path.insert(0, str(SCRIPTS))
    from paths import load_env, upsert_env  # noqa: E402

    env = load_env()
    key = (env.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if not key:
        print()
        print("Enrichment uses gemini-3.5-flash-lite via OpenRouter.")
        print("That is what makes search-by-idea work (topics and concepts, not only keywords).")
        print("  1. https://openrouter.ai/  — add $5 of credits (this run uses well under $1)")
        print("  2. Create an API key")
        print("  3. Paste it ONCE here (nothing will show). Never paste it into chat.")
        try:
            key = getpass("OPENROUTER_API_KEY: ").strip()
        except EOFError:
            key = ""
        if not key:
            raise SystemExit("No OpenRouter key — enrich skipped. Run enrich.bat later.")
        upsert_env("OPENROUTER_API_KEY", key)
        print("Saved OpenRouter key in data/.env (value not printed).")

    py = Path(sys.executable)
    print()
    print("Summarizing posts with google/gemini-3.5-flash-lite …")
    return subprocess.call(
        [str(py), str(SCRIPTS / "enrich_bookmarks.py"), "--limit", "5000"]
    )


if __name__ == "__main__":
    raise SystemExit(main())
