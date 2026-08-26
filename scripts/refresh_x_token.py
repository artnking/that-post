#!/usr/bin/env python3
"""Refresh the X user token. No browser. Never prints token values.

Exit 0 on success, 2 on AUTH_FAIL.
"""
from __future__ import annotations

import base64
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from auth_x import ENV_FILE, TOKEN_URL, load_client, upsert_env  # noqa: E402
from ingest_bookmarks import load_env  # noqa: E402


def refresh() -> int:
    try:
        client_id, client_secret = load_client()
    except SystemExit as e:
        print("sync AUTH_FAIL")
        print(str(e)[:200])
        return 2
    env = load_env()
    refresh_tok = env.get("X_REFRESH_TOKEN") or ""
    if not refresh_tok:
        print("sync AUTH_FAIL")
        print("run auth_x.py on the PC and click Allow")
        return 2
    body = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_tok,
            "client_id": client_id,
        }
    ).encode()
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    req = urllib.request.Request(
        TOKEN_URL,
        data=body,
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            tok = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        err = e.read().decode(errors="replace")[:200]
        print("sync AUTH_FAIL")
        print(f"refresh HTTP {e.code}")
        return 2
    except Exception as e:
        print("sync AUTH_FAIL")
        print(type(e).__name__)
        return 2
    access = tok.get("access_token") or ""
    new_refresh = tok.get("refresh_token") or refresh_tok
    if not access:
        print("sync AUTH_FAIL")
        print("no access token in refresh response")
        return 2
    upsert_env("X_BEARER_TOKEN", access)
    if new_refresh:
        upsert_env("X_REFRESH_TOKEN", new_refresh)
    try:
        req2 = urllib.request.Request(
            "https://api.x.com/2/users/me",
            headers={"Authorization": f"Bearer {access}"},
        )
        with urllib.request.urlopen(req2, timeout=20) as r:
            me = json.loads(r.read().decode())
        uid = (me.get("data") or {}).get("id")
        if uid:
            upsert_env("X_USER_ID", uid)
    except Exception:
        print("token saved; profile check skipped")
        return 0
    print(f"refresh ok (access len {len(access)}, value not printed)")
    return 0


def main() -> int:
    return refresh()


if __name__ == "__main__":
    raise SystemExit(main())
