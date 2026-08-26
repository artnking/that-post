#!/usr/bin/env python3
"""Weekly Ideas on X sync: refresh token, ingest live sources, enrich new rows.

Never prints tokens or tweet text.
"""
from __future__ import annotations

import argparse
import sqlite3
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from ingest_bookmarks import (  # noqa: E402
    DB,
    connect,
    ingest_folders,
    ingest_likes,
    ingest_live,
    ingest_posts,
    write_state,
)
from refresh_x_token import refresh  # noqa: E402

ENRICH = SCRIPTS / "enrich_bookmarks.py"
PY = Path(sys.executable)


def counts(con: sqlite3.Connection) -> dict[str, int]:
    n = con.execute("SELECT COUNT(*) FROM bookmarks").fetchone()[0]
    flags = {}
    for col in ("is_bookmark", "is_post", "is_reply", "is_repost", "is_like"):
        flags[col] = con.execute(f"SELECT COUNT(*) FROM bookmarks WHERE {col}=1").fetchone()[0]
    flags["category"] = con.execute(
        "SELECT COUNT(*) FROM bookmarks WHERE IFNULL(bookmark_category,'') != ''"
    ).fetchone()[0]
    flags["unenriched"] = con.execute(
        "SELECT COUNT(*) FROM bookmarks WHERE enriched_at IS NULL AND IFNULL(text,'') != ''"
    ).fetchone()[0]
    flags["total"] = n
    return flags


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--skip-enrich", action="store_true")
    p.add_argument("--enrich-limit", type=int, default=200)
    args = p.parse_args()

    rc = refresh()
    if rc != 0:
        print("sync AUTH_FAIL")
        print("run auth_x.py on the PC and click Allow")
        return 2

    con = connect()
    before = counts(con)
    try:
        ingest_live(con)
        ingest_posts(con)
        ingest_likes(con)
        ingest_folders(con)
        con.commit()
    except SystemExit as e:
        print("sync FAIL")
        print(str(e)[:300])
        return 1
    except Exception as e:
        print("sync FAIL")
        print(f"{type(e).__name__}")
        return 1

    after = counts(con)
    new = after["total"] - before["total"]
    print("sync ok")
    print(f"before {before['total']}  after {after['total']}  new {new}")
    print(
        f"  bookmark={after['is_bookmark']} post={after['is_post']} "
        f"reply={after['is_reply']} repost={after['is_repost']} "
        f"like={after['is_like']}  category={after['category']}"
    )

    enriched = 0
    if not args.skip_enrich and after["unenriched"] > 0:
        limit = max(1, min(args.enrich_limit, after["unenriched"]))
        r = subprocess.run(
            [str(PY), str(ENRICH), "--limit", str(limit)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        tail = (r.stdout or "").strip().splitlines()
        last = tail[-1] if tail else ""
        if last.startswith("enriched "):
            print(last)
            try:
                enriched = int(last.split()[1].split("/")[0])
            except (IndexError, ValueError):
                enriched = 0
        elif r.returncode != 0:
            print("enrich FAIL")
            err = (r.stderr or r.stdout or "")[-200:]
            print(err.replace("\n", " ")[:200])
        else:
            print("enriched 0")
    else:
        print("enriched 0")

    write_state(last_sync=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(timespec="seconds"), rows=after["total"])
    con.close()
    if new == 0 and enriched == 0:
        print("no new rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
