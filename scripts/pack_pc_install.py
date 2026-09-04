#!/usr/bin/env python3
"""Zip Part 1 for a clean PC/VM. Never includes the live DB, tokens, or x_oauth.json."""
from __future__ import annotations

import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "dist"
SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    ".pytest_cache",
    "__pycache__",
    "data",
    "dist",
    "publish",
}
SKIP_FILE_NAMES = {
    ".env",
    "x_oauth.json",
    "local-art.md",
    "ideas.sqlite",
    "ideas.sqlite-wal",
    "ideas.sqlite-shm",
}


def keep(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if any(part in SKIP_DIR_NAMES for part in rel.parts):
        return False
    if path.name in SKIP_FILE_NAMES:
        return False
    if path.suffix in {".pyc", ".pyo"}:
        return False
    return True


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dest = OUT_DIR / f"that-post-pc-{date.today().isoformat()}.zip"
    count = 0
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("data/.gitkeep", "")
        for path in ROOT.rglob("*"):
            if not path.is_file() or not keep(path):
                continue
            zf.write(path, path.relative_to(ROOT).as_posix())
            count += 1
    print(f"wrote {dest}")
    print(f"files {count}")
    print("Copy x_oauth.json onto the VM separately, into data/.")
    print("Do not zip the live ideas.sqlite.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
