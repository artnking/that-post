#!/usr/bin/env python3
"""Publish lock: strip raw_json, encrypt, decrypt. Uses a temp DB, not live ideas.sqlite."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))


def test_encrypt_roundtrip_and_strip(tmp_path, monkeypatch):
    from export_publish import snapshot_stripped
    from publish_crypto import decrypt_index, encrypt_index

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

    pw = "correct-horse"
    blob = encrypt_index(plain, pw)
    assert blob.startswith(b"THATPOST1")
    out = decrypt_index(blob, pw)
    assert out == plain
    with pytest.raises(Exception):
        decrypt_index(blob, "wrong-password-1")

    dest = tmp_path / "publish"
    import export_publish as exp

    monkeypatch.setattr(exp, "GUI", Path(__file__).resolve().parents[1] / "gui")
    exp.copy_site(dest)
    assert (dest / "index.html").is_file()
    assert (dest / "app.js").is_file()
    assert (dest / "config.js").is_file()
    assert "encrypted: true" in (dest / "config.js").read_text(encoding="utf-8")
    html = (dest / "index.html").read_text(encoding="utf-8")
    assert "./app.js" in html
    assert "./config.js" in html
