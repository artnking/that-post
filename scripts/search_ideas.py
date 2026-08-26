#!/usr/bin/env python3
"""Parameterized FTS5 + filter search over Ideas on X. Never interpolates SQL."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable

DB = Path.home() / ".hermes" / "ideas-on-x" / "ideas.sqlite"

FIELDS = (
    "id",
    "created_at",
    "author_username",
    "author_name",
    "url",
    "summary",
    "keywords",
    "text",
    "enriched_at",
    "folder",
    "bookmark_category",
    "is_bookmark",
    "is_post",
    "is_reply",
    "is_repost",
    "is_like",
)
TYPE_FLAGS = ("bookmark", "post", "reply", "repost", "like")
TYPE_COL = {
    "bookmark": "is_bookmark",
    "post": "is_post",
    "reply": "is_reply",
    "repost": "is_repost",
    "like": "is_like",
}


def connect(db: Path | None = None) -> sqlite3.Connection:
    path = Path(db or DB)
    if not path.exists():
        raise FileNotFoundError(path)
    con = sqlite3.connect(str(path))
    con.row_factory = sqlite3.Row
    return con


def _clamp_limit(limit: int) -> int:
    try:
        n = int(limit)
    except (TypeError, ValueError):
        n = 25
    return max(1, min(100, n))


def _type_clause(types: Iterable[str] | None) -> tuple[str, list]:
    if types is None:
        return "", []
    wanted = [t for t in types if t in TYPE_COL]
    if not wanted:
        return " AND 0 ", []
    if set(wanted) >= set(TYPE_FLAGS):
        return "", []
    parts = [f"b.{TYPE_COL[t]} = 1" for t in wanted]
    return " AND (" + " OR ".join(parts) + ") ", []


def _date_clause(date_from: str | None, date_to: str | None, include_undated: bool) -> tuple[str, dict]:
    params: dict[str, Any] = {
        "date_from": date_from or None,
        "date_to": date_to or None,
        "include_undated": 1 if include_undated else 0,
    }
    sql = """
      AND (
        (
          b.created_at IS NOT NULL AND b.created_at != ''
          AND (:date_from IS NULL OR b.created_at >= :date_from)
          AND (:date_to IS NULL OR b.created_at <= :date_to)
        )
        OR (
          :include_undated = 1 AND (b.created_at IS NULL OR b.created_at = '')
        )
      )
    """
    return sql, params


def _order(sort: str, fts: bool) -> str:
    if sort == "oldest":
        return " ORDER BY CASE WHEN b.created_at IS NULL OR b.created_at = '' THEN 1 ELSE 0 END, b.created_at ASC "
    if sort == "newest":
        return " ORDER BY CASE WHEN b.created_at IS NULL OR b.created_at = '' THEN 1 ELSE 0 END, b.created_at DESC "
    if fts:
        return " ORDER BY rank "
    return " ORDER BY CASE WHEN b.created_at IS NULL OR b.created_at = '' THEN 1 ELSE 0 END, b.created_at DESC "


def _row(r: sqlite3.Row) -> dict:
    out = {k: r[k] for k in r.keys() if k != "raw_json"}
    text = out.get("text") or ""
    out["snippet"] = text.replace("\n", " ")[:280]
    return out


def search(
    q: str = "",
    date_from: str | None = None,
    date_to: str | None = None,
    include_undated: bool = True,
    enriched_only: bool = False,
    author: str = "",
    category: str = "",
    types: Iterable[str] | None = None,
    limit: int = 25,
    sort: str = "relevance",
    db: Path | None = None,
) -> list[dict]:
    limit = _clamp_limit(limit)
    q = (q or "").strip()
    author = (author or "").strip()
    category = (category or "").strip()
    type_sql, _ = _type_clause(types)
    date_sql, date_params = _date_clause(date_from, date_to, include_undated)
    extra = ""
    params: dict[str, Any] = dict(date_params)
    params["limit"] = limit
    if author:
        extra += " AND b.author_username LIKE :author_like "
        params["author_like"] = f"%{author}%"
    if category:
        extra += " AND b.bookmark_category = :category "
        params["category"] = category
    if enriched_only:
        extra += " AND b.enriched_at IS NOT NULL AND b.enriched_at != '' "
    cols = ", ".join(f"b.{c}" for c in FIELDS)
    con = connect(db)
    try:
        if q:
            sql = f"""
            SELECT {cols}
            FROM bookmarks_fts f
            JOIN bookmarks b ON b.rowid = f.rowid
            WHERE bookmarks_fts MATCH :q
            {date_sql} {extra} {type_sql}
            {_order(sort, True)}
            LIMIT :limit
            """
            params["q"] = q
            try:
                rows = list(con.execute(sql, params))
            except sqlite3.OperationalError:
                like = f"%{q}%"
                params.pop("q", None)
                params["like"] = like
                sql = f"""
                SELECT {cols}
                FROM bookmarks b
                WHERE (b.text LIKE :like OR IFNULL(b.summary,'') LIKE :like OR IFNULL(b.keywords,'') LIKE :like)
                {date_sql} {extra} {type_sql}
                {_order(sort, False)}
                LIMIT :limit
                """
                rows = list(con.execute(sql, params))
        else:
            sql = f"""
            SELECT {cols}
            FROM bookmarks b
            WHERE 1=1
            {date_sql} {extra} {type_sql}
            {_order(sort, False)}
            LIMIT :limit
            """
            rows = list(con.execute(sql, params))
    finally:
        con.close()
    return [_row(r) for r in rows]


def stats(db: Path | None = None) -> dict:
    con = connect(db)
    try:
        total = con.execute("SELECT COUNT(*) FROM bookmarks").fetchone()[0]
        enriched = con.execute(
            "SELECT COUNT(*) FROM bookmarks WHERE enriched_at IS NOT NULL AND enriched_at != ''"
        ).fetchone()[0]
        undated = con.execute(
            "SELECT COUNT(*) FROM bookmarks WHERE created_at IS NULL OR created_at = ''"
        ).fetchone()[0]
        mn, mx = con.execute(
            "SELECT MIN(created_at), MAX(created_at) FROM bookmarks WHERE created_at IS NOT NULL AND created_at != ''"
        ).fetchone()
        authors = [
            r[0]
            for r in con.execute(
                "SELECT DISTINCT author_username FROM bookmarks "
                "WHERE IFNULL(author_username,'') != '' ORDER BY 1"
            )
        ]
        categories = [
            r[0]
            for r in con.execute(
                "SELECT DISTINCT bookmark_category FROM bookmarks "
                "WHERE IFNULL(bookmark_category,'') != '' ORDER BY 1"
            )
        ]
        counts = {}
        for flag, col in TYPE_COL.items():
            counts[f"is_{flag}"] = con.execute(f"SELECT COUNT(*) FROM bookmarks WHERE {col}=1").fetchone()[0]
    finally:
        con.close()
    return {
        "total": total,
        "enriched": enriched,
        "undated": undated,
        "min_date": mn,
        "max_date": mx,
        "authors": authors,
        "categories": categories,
        **counts,
    }
