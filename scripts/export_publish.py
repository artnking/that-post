#!/usr/bin/env python3
"""Part 2: build a static folder for Netlify Drop.

Copies the search page + a locked index (raw JSON stripped, AES-GCM).
Does not publish. Does not print the password. Never includes .env or x_oauth.json.
"""
from __future__ import annotations

import argparse
import getpass
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))
from paths import DB as DEFAULT_DB  # noqa: E402
from publish_crypto import KDF_ITERS, encrypt_index  # noqa: E402

GUI = ROOT / "gui"


def snapshot_stripped(src: Path) -> bytes:
    if not src.exists():
        raise SystemExit(f"no database: {src}")
    fd, dest = tempfile.mkstemp(prefix="that-post-pub-", suffix=".sqlite")
    os.close(fd)
    os.remove(dest)
    con = sqlite3.connect(str(src))
    try:
        con.execute("VACUUM INTO ?", (dest,))
    finally:
        con.close()
    d = sqlite3.connect(dest)
    try:
        cols = {r[1] for r in d.execute("PRAGMA table_info(bookmarks)")}
        if "raw_json" in cols:
            d.execute("UPDATE bookmarks SET raw_json = NULL")
            d.commit()
        d.execute("VACUUM")
        d.commit()
    finally:
        d.close()
    data = Path(dest).read_bytes()
    Path(dest).unlink(missing_ok=True)
    if data[18:20] != b"\x01\x01":
        raise SystemExit("publish snapshot is still WAL-mode; sqlite-wasm cannot open it")
    return data


def copy_site(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    jsw = out / "jswasm"
    if jsw.exists():
        shutil.rmtree(jsw)
    shutil.copytree(GUI / "jswasm", jsw)
    assets = GUI / "assets"
    if assets.is_dir():
        dest_assets = out / "assets"
        if dest_assets.exists():
            shutil.rmtree(dest_assets)
        shutil.copytree(assets, dest_assets)
    shutil.copy2(GUI / "app.js", out / "app.js")
    html = (GUI / "index.html").read_text(encoding="utf-8")
    html = html.replace('src="/app.js"', 'src="./app.js"')
    html = html.replace(
        '<script type="module" src="./app.js"></script>',
        '<script src="./config.js"></script>\n  <script type="module" src="./app.js"></script>',
    )
    (out / "index.html").write_text(html, encoding="utf-8")
    (out / "config.js").write_text(
        "window.THAT_POST = { dbUrl: \"./ideas.sqlite.enc\", encrypted: true, kdfIters: %d };\n"
        % KDF_ITERS,
        encoding="utf-8",
    )
    (out / "_headers").write_text(
        "/*\n"
        "  X-Robots-Tag: noindex, nofollow\n"
        "  Referrer-Policy: no-referrer\n"
        "\n"
        "/\n"
        "  Cache-Control: no-store\n"
        "\n"
        "/index.html\n"
        "  Cache-Control: no-store\n"
        "\n"
        "/*.wasm\n"
        "  Content-Type: application/wasm\n"
        "\n"
        "/ideas.sqlite.enc\n"
        "  Cache-Control: no-store\n",
        encoding="utf-8",
    )
    (out / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--out", type=Path, default=ROOT / "publish")
    p.add_argument("--password", default="", help="prefer env THAT_POST_PUBLISH_PASSWORD")
    args = p.parse_args()
    password = (
        args.password
        or os.environ.get("THAT_POST_PUBLISH_PASSWORD")
        or getpass.getpass("Publish PIN (exactly 4 digits, not 1234): ")
    )
    if not (password.isdigit() and len(password) == 4):
        raise SystemExit("Publish PIN must be exactly 4 digits.")
    if password == "1234":
        raise SystemExit("Do not reuse the local PIN 1234 for a public copy.")
    print("Building stripped index …")
    plain = snapshot_stripped(args.db)
    print(f"stripped snapshot {len(plain)} bytes")
    blob = encrypt_index(plain, password)
    copy_site(args.out)
    dest = args.out / "ideas.sqlite.enc"
    dest.write_bytes(blob)
    print(f"wrote {args.out}")
    print(f"locked index {dest} ({len(blob)} bytes)")
    print("Preview: python scripts/serve_publish.py")
    print("Then drag the publish folder onto https://app.netlify.com/drop")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
