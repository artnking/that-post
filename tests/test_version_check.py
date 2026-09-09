"""Compare That Post versions against a GitHub release payload."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from version_check import current_version, is_newer, parse_tag, summarize_release, zip_url


def test_current_version_reads_version_file(tmp_path):
    (tmp_path / "VERSION").write_text("1.4.4\n", encoding="utf-8")
    assert current_version(tmp_path) == "1.4.4"


def test_parse_tag_strips_v():
    assert parse_tag("v1.4.3") == (1, 4, 3)
    assert parse_tag("1.4.3") == (1, 4, 3)


def test_newer_release_is_detected():
    assert is_newer("v1.4.4", "1.4.3") is True
    assert is_newer("v1.4.3", "1.4.3") is False
    assert is_newer("v1.4.2", "1.4.3") is False


def test_zip_url_prefers_that_post_asset():
    release = {
        "tag_name": "v1.4.4",
        "html_url": "https://github.com/artnking/that-post/releases/tag/v1.4.4",
        "body": "Donate popup",
        "assets": [
            {"name": "source.zip", "browser_download_url": "https://example/source.zip"},
            {
                "name": "that-post-pc-2026-09-06.zip",
                "browser_download_url": "https://example/that-post-pc-2026-09-06.zip",
            },
        ],
    }
    assert zip_url(release) == "https://example/that-post-pc-2026-09-06.zip"


def test_summarize_release_marks_update():
    release = {
        "tag_name": "v1.4.4",
        "html_url": "https://github.com/artnking/that-post/releases/tag/v1.4.4",
        "body": "notes",
        "assets": [
            {
                "name": "that-post.zip",
                "browser_download_url": "https://example/that-post.zip",
            }
        ],
    }
    out = summarize_release(release, current="1.4.3")
    assert out["newer"] is True
    assert out["latest"] == "1.4.4"
    assert out["zip_url"] == "https://example/that-post.zip"
    assert out["html_url"].endswith("v1.4.4")
