#!/usr/bin/env python3
"""Zip the publish folder and deploy it with the Netlify API. Never prints tokens."""
from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

API = "https://api.netlify.com/api/v1"
UA = "ThatPost (that-post-install)"


def zip_dir(folder: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in folder.rglob("*"):
            if not path.is_file():
                continue
            zf.write(path, path.relative_to(folder).as_posix())
    return buf.getvalue()


class NetlifyAuthError(Exception):
    """Token rejected (HTTP 401)."""


def _request(method: str, url: str, token: str, data: bytes | None = None, content_type: str = "") -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": UA,
    }
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")[:400]
        if e.code == 401:
            raise NetlifyAuthError("Access Denied") from None
        raise SystemExit(f"Netlify HTTP {e.code}: {err}") from None
    return json.loads(raw) if raw else {}


def create_site(token: str) -> dict:
    return _request(
        "POST",
        f"{API}/sites",
        token,
        data=b"{}",
        content_type="application/json",
    )


def deploy_zip(token: str, site_id: str, zipped: bytes) -> dict:
    return _request(
        "POST",
        f"{API}/sites/{site_id}/deploys",
        token,
        data=zipped,
        content_type="application/zip",
    )


def site_url(info: dict) -> str:
    return str(
        info.get("ssl_url")
        or info.get("deploy_ssl_url")
        or info.get("url")
        or ""
    )


def make_public(token: str, site_id: str) -> bool:
    """Best-effort: new Netlify teams default sites to private."""
    bodies = (
        {"visibility": "public"},
        {"published": True},
        {"password": ""},
    )
    url = f"{API}/sites/{site_id}"
    for body in bodies:
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": UA,
            "Content-Type": "application/json",
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode(),
            headers=headers,
            method="PATCH",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                r.read()
            return True
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise NetlifyAuthError("Access Denied") from None
            continue
        except OSError:
            continue
    return False
