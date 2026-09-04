#!/usr/bin/env python3
from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from netlify_deploy import zip_dir  # noqa: E402


def test_zip_dir_uses_relative_paths(tmp_path):
    (tmp_path / "index.html").write_text("ok", encoding="utf-8")
    sub = tmp_path / "assets"
    sub.mkdir()
    (sub / "bg-phone.jpg").write_bytes(b"\xff\xd8\xff")
    blob = zip_dir(tmp_path)
    assert blob[:2] == b"PK"
    import zipfile, io

    names = zipfile.ZipFile(io.BytesIO(blob)).namelist()
    assert "index.html" in names
    assert "assets/bg-phone.jpg" in names
    assert not any(n.startswith("/") for n in names)
