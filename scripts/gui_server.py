#!/usr/bin/env python3
"""Read-only local host for That Post search page. Bind loopback only.

The page searches in the browser (sqlite-wasm) against a snapshot of
ideas.sqlite. /api/stats and /api/search remain as a server-side check.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, Response

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import search_ideas  # noqa: E402
from paths import DB  # noqa: E402

SKILL = SCRIPTS.parent
GUI = SKILL / "gui"
GUI_HTML = GUI / "index.html"
GUI_APP = GUI / "app.js"
GUI_DONATE = GUI / "donate.html"
GUI_ASSETS = GUI / "assets"
JSWASM = GUI / "jswasm"
TYPE_FLAGS = ("bookmark", "post", "reply", "repost", "like")
ASSET_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
JSWASM_TYPES = {
    "index.mjs": "text/javascript",
    "sqlite3.wasm": "application/wasm",
    "sqlite3-opfs-async-proxy.js": "text/javascript",
}

app = FastAPI(title="That Post", docs_url=None, redoc_url=None)


@app.get("/")
def index():
    if not GUI_HTML.exists():
        raise HTTPException(500, "gui/index.html missing")
    return FileResponse(GUI_HTML, headers={"Cache-Control": "no-store"})


@app.get("/app.js")
def app_js():
    if not GUI_APP.exists():
        raise HTTPException(500, "gui/app.js missing")
    return FileResponse(
        GUI_APP,
        media_type="text/javascript",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/donate.html")
def donate_page():
    if not GUI_DONATE.exists():
        raise HTTPException(404, "gui/donate.html missing")
    return FileResponse(GUI_DONATE, headers={"Cache-Control": "no-store"})


@app.get("/update/check")
def update_check():
    from version_check import current_version, fetch_latest, summarize_release

    try:
        release = fetch_latest()
    except Exception:
        raise HTTPException(502, "Could not reach GitHub") from None
    return JSONResponse(
        summarize_release(release, current_version()),
        headers={"Cache-Control": "no-store"},
    )


@app.get("/assets/{name}")
def asset_file(name: str):
    if "/" in name or "\\" in name or name.startswith("."):
        raise HTTPException(404)
    path = GUI_ASSETS / name
    media = ASSET_TYPES.get(path.suffix.lower())
    if not media or not path.is_file():
        raise HTTPException(404)
    return FileResponse(
        path,
        media_type=media,
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/jswasm/{name}")
def jswasm_file(name: str):
    media = JSWASM_TYPES.get(name)
    if not media:
        raise HTTPException(404)
    path = JSWASM / name
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(
        path,
        media_type=media,
        headers={"Cache-Control": "public, max-age=86400"},
    )


def _snapshot_bytes() -> bytes:
    """Non-WAL copy. sqlite-wasm cannot open WAL-mode files."""
    fd, dest = tempfile.mkstemp(prefix="that-post-", suffix=".sqlite")
    os.close(fd)
    os.remove(dest)
    con = sqlite3.connect(str(DB))
    try:
        con.execute("VACUUM INTO ?", (str(dest),))
    finally:
        con.close()
    try:
        data = Path(dest).read_bytes()
    finally:
        Path(dest).unlink(missing_ok=True)
    if len(data) < 100 or data[18:20] != b"\x01\x01":
        raise HTTPException(500, "snapshot is not a rollback-journal SQLite file")
    return data


@app.get("/ideas.sqlite")
def ideas_sqlite():
    if not DB.exists():
        raise HTTPException(404, "no database yet")
    data = _snapshot_bytes()
    return Response(
        content=data,
        media_type="application/vnd.sqlite3",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": "inline; filename=ideas.sqlite",
        },
    )


@app.get("/api/stats")
def api_stats():
    return search_ideas.stats()


@app.get("/api/search")
def api_search(
    q: str = "",
    date_from: str | None = None,
    date_to: str | None = None,
    include_undated: bool = True,
    enriched_only: bool = False,
    author: str = "",
    category: list[str] | None = Query(default=None),
    types: list[str] | None = Query(default=None),
    limit: int = 25,
    offset: int = 0,
    sort: str = "relevance",
):
    if types:
        types = [t for t in types if t in TYPE_FLAGS]
    return search_ideas.search_page(
        q=q,
        date_from=date_from or None,
        date_to=date_to or None,
        include_undated=include_undated,
        enriched_only=enriched_only,
        author=author,
        category=category,
        types=types,
        limit=limit,
        offset=offset,
        sort=sort,
    )
