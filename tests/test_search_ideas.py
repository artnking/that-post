#!/usr/bin/env python3
"""Temp-db tests for search_ideas. Do not touch the live ideas.sqlite."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

SCHEMA = """
CREATE TABLE bookmarks (
    id TEXT PRIMARY KEY,
    author_id TEXT,
    author_username TEXT,
    author_name TEXT,
    created_at TEXT,
    folder TEXT,
    bookmark_category TEXT,
    text TEXT,
    url TEXT,
    summary TEXT,
    keywords TEXT,
    image_notes TEXT,
    reply_notes TEXT,
    raw_json TEXT,
    ingested_at TEXT,
    enriched_at TEXT,
    is_bookmark INTEGER NOT NULL DEFAULT 0,
    is_post INTEGER NOT NULL DEFAULT 0,
    is_reply INTEGER NOT NULL DEFAULT 0,
    is_repost INTEGER NOT NULL DEFAULT 0,
    is_like INTEGER NOT NULL DEFAULT 0
);
CREATE VIRTUAL TABLE bookmarks_fts USING fts5(
    id UNINDEXED,
    text,
    summary,
    keywords,
    image_notes,
    reply_notes,
    author_username,
    folder
);
CREATE TRIGGER bookmarks_ai AFTER INSERT ON bookmarks BEGIN
  INSERT INTO bookmarks_fts(rowid, id, text, summary, keywords, image_notes, reply_notes, author_username, folder)
  VALUES (new.rowid, new.id, new.text, new.summary, new.keywords, new.image_notes, new.reply_notes, new.author_username, new.folder);
END;
"""


def _insert(con, **kw):
    keys = [
        "id",
        "author_username",
        "author_name",
        "created_at",
        "folder",
        "bookmark_category",
        "text",
        "url",
        "summary",
        "keywords",
        "raw_json",
        "enriched_at",
        "is_bookmark",
        "is_post",
        "is_reply",
        "is_repost",
        "is_like",
    ]
    defaults = {
        "author_username": "",
        "author_name": "",
        "created_at": None,
        "folder": None,
        "bookmark_category": None,
        "text": "",
        "url": "",
        "summary": "",
        "keywords": "",
        "raw_json": '{"secret":true}',
        "enriched_at": None,
        "is_bookmark": 1,
        "is_post": 0,
        "is_reply": 0,
        "is_repost": 0,
        "is_like": 0,
    }
    defaults.update(kw)
    con.execute(
        f"INSERT INTO bookmarks ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})",
        [defaults[k] for k in keys],
    )


@pytest.fixture
def db(tmp_path, monkeypatch):
    import search_ideas

    path = tmp_path / "ideas.sqlite"
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    _insert(
        con,
        id="1",
        author_username="Will_Tanner_1",
        created_at="2026-08-14T23:32:00.000Z",
        text="Fertility is low because fertility is a referendum",
        summary="declining fertility rates indictment",
        keywords="fertility, TFR",
        url="https://x.com/Will_Tanner_1/status/1",
        enriched_at="2026-08-26T00:00:00+00:00",
        is_bookmark=1,
        bookmark_category="Fertility",
        folder="Fertility",
    )
    _insert(
        con,
        id="2",
        author_username="other",
        created_at="2024-01-01T00:00:00.000Z",
        text="unrelated Tesla battery chemistry",
        url="https://x.com/i/web/status/2",
        is_like=1,
        is_bookmark=0,
    )
    _insert(
        con,
        id="3",
        author_username="seed",
        created_at=None,
        text="undated seed fertility collapse note",
        url="https://x.com/i/web/status/3",
        is_bookmark=1,
    )
    con.commit()
    con.close()
    monkeypatch.setattr(search_ideas, "DB", path)
    return path


def test_fts_fertility_returns_fertility_row_not_unrelated(db):
    import search_ideas

    rows = search_ideas.search(q="fertility")
    ids = [r["id"] for r in rows]
    assert "1" in ids
    assert "2" not in ids


def test_empty_q_date_range_excludes_out_of_range(db):
    import search_ideas

    rows = search_ideas.search(q="", date_from="2026-01-01", date_to="2026-12-31", include_undated=False)
    ids = [r["id"] for r in rows]
    assert ids == ["1"]


def test_include_undated_false_drops_null_created_at(db):
    import search_ideas

    rows = search_ideas.search(q="fertility", include_undated=False)
    assert "3" not in [r["id"] for r in rows]


def test_include_undated_true_keeps_null_created_at(db):
    import search_ideas

    rows = search_ideas.search(q="fertility", include_undated=True)
    assert "3" in [r["id"] for r in rows]


def test_enriched_only_drops_empty_enriched_at(db):
    import search_ideas

    rows = search_ideas.search(q="", enriched_only=True, include_undated=True)
    assert [r["id"] for r in rows] == ["1"]


def test_author_will_matches_handle(db):
    import search_ideas

    rows = search_ideas.search(q="", author="Will", include_undated=True)
    assert [r["id"] for r in rows] == ["1"]


def test_category_list_filters_bookmarks(db):
    import search_ideas

    rows = search_ideas.search(
        q="", include_undated=True, types=["bookmark"], category=["Fertility"]
    )
    assert [r["id"] for r in rows] == ["1"]


def test_category_none_matches_uncategorized_bookmarks(db):
    import search_ideas

    rows = search_ideas.search(
        q="", include_undated=True, types=["bookmark"], category=["__none__"]
    )
    assert [r["id"] for r in rows] == ["3"]


def test_category_real_plus_none_unions(db):
    import search_ideas

    rows = search_ideas.search(
        q="",
        include_undated=True,
        types=["bookmark"],
        category=["Fertility", "__none__"],
        sort="newest",
    )
    assert [r["id"] for r in rows] == ["1", "3"]


def test_limit_2_returns_two(db):
    import search_ideas

    rows = search_ideas.search(q="", include_undated=True, limit=2, sort="oldest")
    assert len(rows) == 2


def test_limit_0_returns_all(db):
    import search_ideas

    rows = search_ideas.search(q="", include_undated=True, limit=0)
    assert len(rows) == 3


def test_offset_skips_first(db):
    import search_ideas

    first = search_ideas.search(q="", include_undated=True, limit=1, offset=0, sort="oldest")
    second = search_ideas.search(q="", include_undated=True, limit=1, offset=1, sort="oldest")
    assert first[0]["id"] != second[0]["id"]


def test_search_page_total(db):
    import search_ideas

    page = search_ideas.search_page(q="", include_undated=True, limit=1, sort="oldest")
    assert page["total"] == 3
    assert page["hits"] == 1
    assert page["offset"] == 0


def test_bad_match_syntax_falls_back_to_like(db):
    import search_ideas

    rows = search_ideas.search(q='AND AND "')
    # fallback LIKE should not crash; may be empty
    assert isinstance(rows, list)


def test_results_have_no_raw_json(db):
    import search_ideas

    rows = search_ideas.search(q="fertility")
    assert rows
    for r in rows:
        assert "raw_json" not in r


def test_stats_counts(db):
    import search_ideas

    st = search_ideas.stats()
    assert st["total"] == 3
    assert st["enriched"] == 1
    assert st["undated"] == 1
    assert st["min_date"].startswith("2024-01-01")
    assert st["max_date"].startswith("2026-08-14")
    assert "Will_Tanner_1" in st["authors"]
    assert "Fertility" in st["categories"]
    assert st["is_bookmark"] == 2
    assert st["is_like"] == 1
