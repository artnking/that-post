#!/usr/bin/env python3
"""FTS5 search over That Post."""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
import sys

sys.path.insert(0, str(SCRIPTS))
from paths import DB  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--sql", default="")
    p.add_argument("--limit", type=int, default=15)
    args = p.parse_args()
    if not DB.exists():
        raise SystemExit(f"no db yet: {DB}  (run ingest_bookmarks.py --seed)")
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    if args.sql:
        rows = list(con.execute(args.sql))
        for r in rows:
            print(dict(r) if isinstance(r, sqlite3.Row) else r)
        return 0
    if not args.query.strip():
        n = con.execute("SELECT COUNT(*) FROM bookmarks").fetchone()[0]
        enr = con.execute("SELECT COUNT(*) FROM bookmarks WHERE enriched_at IS NOT NULL").fetchone()[0]
        print(f"bookmarks {n}  enriched {enr}")
        return 0
    q = args.query
    sql = """
    SELECT b.id, b.created_at, b.author_username, b.folder, b.url,
           b.summary, b.keywords, b.text
    FROM bookmarks_fts f
    JOIN bookmarks b ON b.rowid = f.rowid
    WHERE bookmarks_fts MATCH ?
    ORDER BY rank
    LIMIT ?
    """
    try:
        rows = list(con.execute(sql, (q, args.limit)))
    except sqlite3.OperationalError:
        # fallback substring if MATCH syntax fails
        like = f"%{q}%"
        rows = list(
            con.execute(
                """
                SELECT id, created_at, author_username, folder, url, summary, keywords, text
                FROM bookmarks
                WHERE text LIKE ? OR summary LIKE ? OR keywords LIKE ?
                LIMIT ?
                """,
                (like, like, like, args.limit),
            )
        )
    if not rows:
        print("no hits")
        return 0
    for r in rows:
        print("---")
        print(f"{r['created_at'] or '?'}  @{r['author_username'] or '?'}  {r['id']}")
        print(r["url"] or "")
        if r["folder"]:
            print("folder:", r["folder"])
        if r["summary"]:
            print("summary:", r["summary"])
        if r["keywords"]:
            print("keywords:", r["keywords"])
        text = (r["text"] or "").replace("\n", " ")
        print("tweet:", text[:280])
    print(f"\n{len(rows)} hit(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
