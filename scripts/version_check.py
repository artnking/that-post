"""Compare this install's version to a GitHub Releases payload."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any

GITHUB_LATEST = "https://api.github.com/repos/artnking/that-post/releases/latest"
ROOT = Path(__file__).resolve().parent.parent


def current_version(root: Path | None = None) -> str:
    path = (root or ROOT) / "VERSION"
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return "0"


def parse_tag(tag: str) -> tuple[int, ...]:
    s = (tag or "").strip()
    if s.lower().startswith("v"):
        s = s[1:]
    parts: list[int] = []
    for bit in s.split("."):
        n = ""
        for ch in bit:
            if ch.isdigit():
                n += ch
            else:
                break
        parts.append(int(n) if n else 0)
    return tuple(parts or (0,))


def is_newer(latest: str, current: str) -> bool:
    return parse_tag(latest) > parse_tag(current)


def zip_url(release: dict[str, Any]) -> str:
    assets = release.get("assets") or []
    preferred = None
    fallback = None
    for a in assets:
        name = (a.get("name") or "").lower()
        url = a.get("browser_download_url") or ""
        if not url:
            continue
        if fallback is None:
            fallback = url
        if "that-post" in name and name.endswith(".zip"):
            preferred = url
            break
    return preferred or fallback or ""


def summarize_release(release: dict[str, Any], current: str) -> dict[str, Any]:
    tag = (release.get("tag_name") or "").strip()
    latest = tag[1:] if tag.lower().startswith("v") else tag
    return {
        "current": current,
        "latest": latest,
        "newer": is_newer(tag, current),
        "html_url": release.get("html_url") or "",
        "zip_url": zip_url(release),
        "notes": (release.get("body") or "").strip(),
    }


def fetch_latest() -> dict[str, Any]:
    req = urllib.request.Request(
        GITHUB_LATEST,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "ThatPost-update-check",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))
