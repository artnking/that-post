#!/usr/bin/env python3
"""Publish snapshot: strip raw_json, no app PIN. Uses a temp DB, not live ideas.sqlite."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))


def test_publish_strips_raw_json_and_is_not_encrypted(tmp_path, monkeypatch):
    from export_publish import copy_site, snapshot_stripped

    src = tmp_path / "ideas.sqlite"
    con = sqlite3.connect(src)
    con.execute(
        "CREATE TABLE bookmarks (id TEXT PRIMARY KEY, text TEXT, raw_json TEXT, summary TEXT)"
    )
    con.execute(
        "INSERT INTO bookmarks VALUES ('1', 'fertility note', '{\"secret\":true}', 'about TFR')"
    )
    con.commit()
    con.close()

    plain = snapshot_stripped(src)
    assert plain[:16] == b"SQLite format 3\x00"
    assert plain[18:20] == b"\x01\x01"
    assert b"secret" not in plain

    dest = tmp_path / "publish"
    import export_publish as exp

    monkeypatch.setattr(exp, "GUI", Path(__file__).resolve().parents[1] / "gui")
    copy_site(dest)
    (dest / "ideas.sqlite").write_bytes(plain)
    assert (dest / "index.html").is_file()
    assert (dest / "app.js").is_file()
    cfg = (dest / "config.js").read_text(encoding="utf-8")
    assert "encrypted: false" in cfg
    assert "./ideas.sqlite" in cfg
    assert not (dest / "ideas.sqlite.enc").exists()
    html = (dest / "index.html").read_text(encoding="utf-8")
    assert "./app.js" in html
    assert "./config.js" in html
    headers = (dest / "_headers").read_text(encoding="utf-8")
    assert "/ideas.sqlite" in headers
