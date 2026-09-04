#!/usr/bin/env python3
"""Read-only local host for That Post search page. Bind loopback only.

The page searches in the browser (sqlite-wasm) against a snapshot of
ideas.sqlite. /api/stats and /api/search remain as a server-side check.
"""
from __future__ import annotations

import base64
import os
import secrets
import sqlite3
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import search_ideas  # noqa: E402
from paths import DB, load_env  # noqa: E402

SKILL = SCRIPTS.parent
GUI = SKILL / "gui"
GUI_HTML = GUI / "index.html"
GUI_APP = GUI / "app.js"
GUI_ASSETS = GUI / "assets"
JSWASM = GUI / "jswasm"
TYPE_FLAGS = ("bookmark", "post", "reply", "repost", "like")
DEFAULT_PAGE_PASSWORD = "1234"
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


def page_password() -> str:
    env = load_env()
    return (
        os.environ.get("THAT_POST_PASSWORD")
        or env.get("THAT_POST_PASSWORD")
        or os.environ.get("THE_POST_PASSWORD")
        or env.get("THE_POST_PASSWORD")
        or DEFAULT_PAGE_PASSWORD
    )


def _basic_password(header: str) -> str:
    if not header or not header.lower().startswith("basic "):
        return ""
    try:
        raw = base64.b64decode(header.split(" ", 1)[1].strip()).decode("utf-8")
    except Exception:
        return ""
    if ":" not in raw:
        return ""
    return raw.split(":", 1)[1]


@app.middleware("http")
async def password_gate(request: Request, call_next):
    expected = page_password()
    got = _basic_password(request.headers.get("authorization") or "")
    if not expected or not secrets.compare_digest(got, expected):
        return Response(
            "Password required",
            status_code=401,
            headers={
                "WWW-Authenticate": 'Basic realm="That Post"',
                "Cache-Control": "no-store",
            },
        )
    return await call_next(request)


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
