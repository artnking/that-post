#!/usr/bin/env python3
"""Load X bookmark JSON (seed) and live API pages into SQLite FTS5.

Sources: bookmarks, own posts/replies/reposts, likes, bookmark folders.
A row is one tweet id. Type flags can overlap (liked AND bookmarked).
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
DATA = HOME / ".hermes" / "ideas-on-x"
DB = DATA / "ideas.sqlite"
STATE = DATA / "state.json"
SEED_DIR = HOME / ".hermes" / "skills" / "OpenClaw skills" / "X bookmarks"
ENV = HOME / ".hermes" / ".env"

TWEET_FIELDS = (
    "created_at,author_id,public_metrics,conversation_id,attachments,"
    "entities,in_reply_to_user_id,referenced_tweets,note_tweet"
)
EXPANSIONS = "author_id,attachments.media_keys,referenced_tweets.id"
USER_FIELDS = "username,name"
MEDIA_FIELDS = "url,preview_image_url,type,alt_text"


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if not ENV.exists():
        return out
    for line in ENV.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


SCHEMA = """
CREATE TABLE IF NOT EXISTS bookmarks (
    id TEXT PRIMARY KEY,
    author_id TEXT,
    author_username TEXT,
    author_name TEXT,
    created_at TEXT,
    folder TEXT,
    text TEXT,
    url TEXT,
    summary TEXT,
    keywords TEXT,
    image_notes TEXT,
    reply_notes TEXT,
    raw_json TEXT,
    ingested_at TEXT,
    enriched_at TEXT
);
CREATE VIRTUAL TABLE IF NOT EXISTS bookmarks_fts USING fts5(
    id UNINDEXED,
    text,
    summary,
    keywords,
    image_notes,
    reply_notes,
    author_username,
    folder
);
CREATE TRIGGER IF NOT EXISTS bookmarks_ai AFTER INSERT ON bookmarks BEGIN
  INSERT INTO bookmarks_fts(rowid, id, text, summary, keywords, image_notes, reply_notes, author_username, folder)
  VALUES (new.rowid, new.id, new.text, new.summary, new.keywords, new.image_notes, new.reply_notes, new.author_username, new.folder);
END;
CREATE TRIGGER IF NOT EXISTS bookmarks_ad AFTER DELETE ON bookmarks BEGIN
  DELETE FROM bookmarks_fts WHERE rowid = old.rowid;
END;
CREATE TRIGGER IF NOT EXISTS bookmarks_au AFTER UPDATE ON bookmarks BEGIN
  DELETE FROM bookmarks_fts WHERE rowid = old.rowid;
  INSERT INTO bookmarks_fts(rowid, id, text, summary, keywords, image_notes, reply_notes, author_username, folder)
  VALUES (new.rowid, new.id, new.text, new.summary, new.keywords, new.image_notes, new.reply_notes, new.author_username, new.folder);
END;
"""

NEW_COLUMNS = [
    ("is_bookmark", "INTEGER NOT NULL DEFAULT 0"),
    ("is_post", "INTEGER NOT NULL DEFAULT 0"),
    ("is_reply", "INTEGER NOT NULL DEFAULT 0"),
    ("is_repost", "INTEGER NOT NULL DEFAULT 0"),
    ("is_like", "INTEGER NOT NULL DEFAULT 0"),
    ("bookmark_category", "TEXT"),
]


def migrate(con: sqlite3.Connection) -> None:
    cols = {r[1] for r in con.execute("PRAGMA table_info(bookmarks)")}
    added = []
    for name, decl in NEW_COLUMNS:
        if name not in cols:
            con.execute(f"ALTER TABLE bookmarks ADD COLUMN {name} {decl}")
            added.append(name)
    if "is_bookmark" in added:
        # Existing rows were bookmarks-only.
        con.execute("UPDATE bookmarks SET is_bookmark = 1")
    con.commit()


def connect() -> sqlite3.Connection:
    DATA.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SCHEMA)
    migrate(con)
    return con


def tweet_text(tweet: dict) -> str:
    note = tweet.get("note_tweet") or {}
    if isinstance(note, dict) and (note.get("text") or "").strip():
        return note["text"]
    return tweet.get("text") or ""


def classify_own(tweet: dict) -> dict[str, int]:
    refs = tweet.get("referenced_tweets") or []
    types = {r.get("type") for r in refs if isinstance(r, dict)}
    if "retweeted" in types:
        return {"is_repost": 1}
    if tweet.get("in_reply_to_user_id") or "replied_to" in types:
        return {"is_reply": 1}
    return {"is_post": 1}


def upsert(
    con: sqlite3.Connection,
    tweet: dict,
    users: dict[str, dict],
    folder: str | None = None,
    flags: dict[str, int] | None = None,
) -> None:
    flags = flags or {}
    tid = str(tweet["id"])
    author_id = tweet.get("author_id")
    user = users.get(str(author_id) if author_id else "", {})
    username = user.get("username") or ""
    url = f"https://x.com/{username}/status/{tid}" if username else f"https://x.com/i/web/status/{tid}"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    is_bookmark = 1 if flags.get("is_bookmark") else 0
    is_post = 1 if flags.get("is_post") else 0
    is_reply = 1 if flags.get("is_reply") else 0
    is_repost = 1 if flags.get("is_repost") else 0
    is_like = 1 if flags.get("is_like") else 0
    category = (flags.get("bookmark_category") or folder or "") or None
    text = tweet_text(tweet)
    con.execute(
        """
        INSERT INTO bookmarks (
            id, author_id, author_username, author_name, created_at, folder, bookmark_category,
            text, url, raw_json, ingested_at,
            is_bookmark, is_post, is_reply, is_repost, is_like
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            author_id=excluded.author_id,
            author_username=COALESCE(NULLIF(excluded.author_username,''), bookmarks.author_username),
            author_name=COALESCE(NULLIF(excluded.author_name,''), bookmarks.author_name),
            created_at=COALESCE(excluded.created_at, bookmarks.created_at),
            folder=COALESCE(excluded.folder, bookmarks.folder),
            bookmark_category=COALESCE(excluded.bookmark_category, bookmarks.bookmark_category),
            text=CASE WHEN length(excluded.text) >= length(IFNULL(bookmarks.text,''))
                 THEN excluded.text ELSE bookmarks.text END,
            url=excluded.url,
            raw_json=excluded.raw_json,
            ingested_at=excluded.ingested_at,
            is_bookmark=CASE WHEN excluded.is_bookmark=1 THEN 1 ELSE bookmarks.is_bookmark END,
            is_post=CASE WHEN excluded.is_post=1 THEN 1 ELSE bookmarks.is_post END,
            is_reply=CASE WHEN excluded.is_reply=1 THEN 1 ELSE bookmarks.is_reply END,
            is_repost=CASE WHEN excluded.is_repost=1 THEN 1 ELSE bookmarks.is_repost END,
            is_like=CASE WHEN excluded.is_like=1 THEN 1 ELSE bookmarks.is_like END
        """,
        (
            tid,
            author_id,
            username,
            user.get("name") or "",
            tweet.get("created_at"),
            category,
            category,
            text,
            url,
            json.dumps(tweet, ensure_ascii=False),
            now,
            is_bookmark,
            is_post,
            is_reply,
            is_repost,
            is_like,
        ),
    )


def ingest_payload(
    con: sqlite3.Connection,
    payload: dict,
    folder: str | None = None,
    flags: dict[str, int] | None = None,
) -> int:
    users = {u["id"]: u for u in (payload.get("includes") or {}).get("users") or []}
    n = 0
    for tweet in payload.get("data") or []:
        if not isinstance(tweet, dict) or not tweet.get("id"):
            continue
        if "text" not in tweet and "note_tweet" not in tweet:
            # ID-only folder rows — skip; hydrate via /2/tweets
            continue
        row_flags = dict(flags or {})
        upsert(con, tweet, users, folder, row_flags)
        n += 1
    return n


def ingest_seed(con: sqlite3.Connection) -> int:
    total = 0
    if not SEED_DIR.is_dir():
        print(f"no seed dir {SEED_DIR}")
        return 0
    for path in sorted(SEED_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        n = ingest_payload(con, payload, flags={"is_bookmark": 1})
        print(f"seed {path.name}: {n} rows")
        total += n
    return total


def auth_pair() -> tuple[str, str]:
    env = load_env()
    token = env.get("X_BEARER_TOKEN") or os.environ.get("X_BEARER_TOKEN")
    if not token:
        raise SystemExit("X_BEARER_TOKEN missing in ~/.hermes/.env — do not paste it in chat")
    user_id = env.get("X_USER_ID") or os.environ.get("X_USER_ID")
    if not user_id:
        me = x_get(token, "/users/me", {})
        user_id = (me.get("data") or {}).get("id")
        if not user_id:
            raise SystemExit("X_USER_ID missing and /users/me failed")
    return token, user_id


def x_get(token: str, path: str, params: dict[str, str], timeout: int = 60) -> dict:
    url = "https://api.x.com/2" + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    last_err = ""
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            last_err = e.read().decode(errors="replace")[:400]
            if e.code == 429:
                wait = 20 * (attempt + 1)
                print(f"rate limited {path} — sleep {wait}s")
                time.sleep(wait)
                req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
                continue
            raise SystemExit(f"X API HTTP {e.code} {path} {last_err}")
        except TimeoutError:
            print(f"timeout {path} attempt {attempt + 1}")
            time.sleep(5)
    raise SystemExit(f"X API failed {path} {last_err[:200]}")


def paginate(token: str, path: str, params: dict[str, str], label: str, con: sqlite3.Connection, flags: dict[str, int]) -> int:
    total = 0
    next_token = None
    page = 0
    while True:
        q = dict(params)
        if next_token:
            q["pagination_token"] = next_token
        payload = x_get(token, path, q)
        n = ingest_payload(con, payload, flags=flags)
        total += n
        page += 1
        print(f"{label} page {page} +{n} rows={total}")
        next_token = (payload.get("meta") or {}).get("next_token")
        con.commit()
        if not next_token:
            break
    return total


def ingest_live(con: sqlite3.Connection) -> int:
    token, user_id = auth_pair()
    params = {
        "max_results": "100",
        "tweet.fields": TWEET_FIELDS,
        "expansions": EXPANSIONS,
        "user.fields": USER_FIELDS,
        "media.fields": MEDIA_FIELDS,
    }
    return paginate(token, f"/users/{user_id}/bookmarks", params, "bookmarks", con, {"is_bookmark": 1})


def ingest_posts(con: sqlite3.Connection) -> int:
    token, user_id = auth_pair()
    params = {
        "max_results": "100",
        "tweet.fields": TWEET_FIELDS,
        "expansions": EXPANSIONS,
        "user.fields": USER_FIELDS,
        "media.fields": MEDIA_FIELDS,
    }
    total = 0
    next_token = None
    page = 0
    path = f"/users/{user_id}/tweets"
    while True:
        q = dict(params)
        if next_token:
            q["pagination_token"] = next_token
        payload = x_get(token, path, q)
        users = {u["id"]: u for u in (payload.get("includes") or {}).get("users") or []}
        n = 0
        for tweet in payload.get("data") or []:
            flags = classify_own(tweet)
            upsert(con, tweet, users, flags=flags)
            n += 1
        total += n
        page += 1
        print(f"posts page {page} +{n} rows={total}")
        next_token = (payload.get("meta") or {}).get("next_token")
        con.commit()
        if not next_token:
            break
    return total


def ingest_likes(con: sqlite3.Connection) -> int:
    token, user_id = auth_pair()
    params = {
        "max_results": "100",
        "tweet.fields": TWEET_FIELDS,
        "expansions": EXPANSIONS,
        "user.fields": USER_FIELDS,
        "media.fields": MEDIA_FIELDS,
    }
    return paginate(token, f"/users/{user_id}/liked_tweets", params, "likes", con, {"is_like": 1})


def lookup_tweets(token: str, ids: list[str]) -> dict:
    if not ids:
        return {"data": [], "includes": {}}
    params = {
        "ids": ",".join(ids),
        "tweet.fields": TWEET_FIELDS,
        "expansions": EXPANSIONS,
        "user.fields": USER_FIELDS,
        "media.fields": MEDIA_FIELDS,
    }
    return x_get(token, "/tweets", params)


def ingest_folders(con: sqlite3.Connection) -> int:
    """Folder endpoint returns tweet ids only (cap ~20 per folder, no pagination)."""
    token, user_id = auth_pair()
    payload = x_get(token, f"/users/{user_id}/bookmarks/folders", {"max_results": "100"})
    folders = payload.get("data") or []
    print(f"folders listed {len(folders)}")
    tagged = 0
    for folder in folders:
        fid = str(folder.get("id") or "")
        name = (folder.get("name") or "").strip()
        if not fid or not name:
            continue
        listing = x_get(token, f"/users/{user_id}/bookmarks/folders/{fid}", {"max_results": "100"})
        ids = [str(x.get("id")) for x in (listing.get("data") or []) if x.get("id")]
        print(f"folder {name!r} ids {len(ids)}")
        for i in range(0, len(ids), 100):
            batch = ids[i : i + 100]
            looked = lookup_tweets(token, batch)
            n = ingest_payload(
                con,
                looked,
                folder=name,
                flags={"is_bookmark": 1, "bookmark_category": name},
            )
            # ID-only leftovers (deleted tweets): still stamp category if row exists
            returned = {str(t["id"]) for t in (looked.get("data") or []) if t.get("id")}
            for tid in batch:
                if tid not in returned:
                    con.execute(
                        """
                        UPDATE bookmarks
                        SET folder = COALESCE(folder, ?),
                            bookmark_category = COALESCE(bookmark_category, ?),
                            is_bookmark = 1
                        WHERE id = ?
                        """,
                        (name, name, tid),
                    )
                    if con.execute("SELECT changes()").fetchone()[0]:
                        n += 1
            tagged += n
            con.commit()
    return tagged


def write_state(**kw) -> None:
    st = {}
    if STATE.exists():
        st = json.loads(STATE.read_text(encoding="utf-8"))
    st.update(kw)
    STATE.write_text(json.dumps(st, indent=2), encoding="utf-8")


def print_counts(con: sqlite3.Connection) -> None:
    n, u = con.execute("SELECT COUNT(*), COUNT(DISTINCT id) FROM bookmarks").fetchone()
    print(f"db {DB}")
    print(f"rows {n} distinct {u}")
    for col in ("is_bookmark", "is_post", "is_reply", "is_repost", "is_like"):
        c = con.execute(f"SELECT COUNT(*) FROM bookmarks WHERE {col}=1").fetchone()[0]
        print(f"  {col} {c}")
    cats = con.execute(
        "SELECT COUNT(*) FROM bookmarks WHERE IFNULL(bookmark_category,'') != ''"
    ).fetchone()[0]
    print(f"  with_category {cats}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", action="store_true")
    p.add_argument("--live", action="store_true", help="live bookmarks")
    p.add_argument("--posts", action="store_true", help="own posts, replies, reposts")
    p.add_argument("--likes", action="store_true")
    p.add_argument("--folders", action="store_true", help="bookmark folder names")
    p.add_argument("--all", action="store_true", help="live + posts + likes + folders")
    args = p.parse_args()
    if args.all:
        args.live = args.posts = args.likes = args.folders = True
    if not any([args.seed, args.live, args.posts, args.likes, args.folders]):
        args.seed = True
    con = connect()
    if args.seed:
        ingest_seed(con)
    if args.live:
        ingest_live(con)
    if args.posts:
        ingest_posts(con)
    if args.likes:
        ingest_likes(con)
    if args.folders:
        ingest_folders(con)
    con.commit()
    print_counts(con)
    n = con.execute("SELECT COUNT(*) FROM bookmarks").fetchone()[0]
    write_state(last_ingest=datetime.now(timezone.utc).isoformat(timespec="seconds"), rows=n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
