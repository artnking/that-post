#!/usr/bin/env python3
"""One-time X OAuth 2.0 login for Ideas on X (Windows).

Never prints tokens. Writes X_BEARER_TOKEN to ~/.hermes/.env.

Setup (you do this in the browser, not in chat):
1. https://developer.x.com/en/portal/dashboard
2. App: XURL access from Hermes
3. User authentication: OAuth 2.0 ON
4. Callback / redirect URI exactly: http://127.0.0.1:8080/callback
5. App permissions: Read. Scopes: tweet.read users.read bookmark.read offline.access
6. Copy Client ID and Client Secret into:
     %USERPROFILE%\\.hermes\\ideas-on-x\\x_oauth.json
   using x_oauth.example.json as the shape.

Then run this script on the PC. A browser window opens. Approve. Done.
"""
from __future__ import annotations

import base64
import hashlib
import http.server
import json
import os
import secrets
import threading
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

HOME = Path.home()
DATA = HOME / ".hermes" / "ideas-on-x"
OAUTH_FILE = DATA / "x_oauth.json"
ENV_FILE = HOME / ".hermes" / ".env"
REDIRECT = "http://127.0.0.1:8080/callback"
SCOPES = "tweet.read users.read bookmark.read like.read offline.access"
AUTHORIZE = "https://twitter.com/i/oauth2/authorize"
TOKEN_URL = "https://api.twitter.com/2/oauth2/token"


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def load_client() -> tuple[str, str]:
    if not OAUTH_FILE.exists():
        raise SystemExit(
            f"Missing {OAUTH_FILE}\n"
            "Create it from x_oauth.example.json with client_id and client_secret.\n"
            "Do not put those values in Telegram."
        )
    data = json.loads(OAUTH_FILE.read_text(encoding="utf-8"))
    cid = (data.get("client_id") or "").strip()
    secret = (data.get("client_secret") or "").strip()
    if not cid or not secret or "PASTE" in cid or "PASTE" in secret:
        raise SystemExit(f"Fill client_id and client_secret in {OAUTH_FILE}")
    return cid, secret


def upsert_env(key: str, value: str) -> None:
    lines: list[str] = []
    if ENV_FILE.exists():
        lines = ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    found = False
    out = []
    for line in lines:
        if line.startswith(f"{key}=") or line.startswith(f"#{key}="):
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        if out and out[-1].strip():
            out.append("")
        out.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    client_id, client_secret = load_client()
    verifier = b64url(secrets.token_bytes(32))
    challenge = b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    state = secrets.token_urlsafe(16)
    box: dict[str, str] = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_a, **_k):
            return

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/callback":
                self.send_error(404)
                return
            qs = urllib.parse.parse_qs(parsed.query)
            if qs.get("state", [""])[0] != state:
                self.send_error(400, "state mismatch")
                return
            if "error" in qs:
                box["error"] = qs["error"][0]
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"X login failed. You can close this tab.")
                return
            box["code"] = qs.get("code", [""])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<html><body><p>Ideas on X is connected. You can close this tab.</p></body></html>")

    httpd = http.server.HTTPServer(("127.0.0.1", 8080), Handler)
    thread = threading.Thread(target=httpd.handle_request, daemon=True)
    thread.start()

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT,
        "scope": SCOPES,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    url = AUTHORIZE + "?" + urllib.parse.urlencode(params)
    print("Opening X login in your browser…")
    print("If it does not open, paste this into Chrome (on this PC):")
    print(url)
    webbrowser.open(url)
    thread.join(timeout=180)
    httpd.server_close()
    if box.get("error"):
        raise SystemExit(f"X returned error: {box['error']}")
    if not box.get("code"):
        raise SystemExit("No login code (timed out). Run again and approve in the browser within 3 minutes.")

    body = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "code": box["code"],
            "redirect_uri": REDIRECT,
            "client_id": client_id,
            "code_verifier": verifier,
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
    except Exception as e:
        err = e.read().decode() if hasattr(e, "read") else str(e)
        raise SystemExit(f"Token exchange failed (no secrets shown): {type(e).__name__} {err[:300]}")

    access = tok.get("access_token") or ""
    refresh = tok.get("refresh_token") or ""
    if not access:
        raise SystemExit("X did not return an access token. Check app type is Confidential client + callback URI.")
    upsert_env("X_BEARER_TOKEN", access)
    if refresh:
        upsert_env("X_REFRESH_TOKEN", refresh)
    print(f"OK — saved X_BEARER_TOKEN to {ENV_FILE} (length {len(access)}, value not printed)")
    if refresh:
        print(f"OK — saved X_REFRESH_TOKEN (length {len(refresh)})")
    # smoke test without printing profile names if we can
    try:
        req2 = urllib.request.Request(
            "https://api.twitter.com/2/users/me",
            headers={"Authorization": f"Bearer {access}"},
        )
        with urllib.request.urlopen(req2, timeout=20) as r:
            me = json.loads(r.read().decode())
        uid = (me.get("data") or {}).get("id")
        if uid:
            upsert_env("X_USER_ID", uid)
            print("OK — login works (user id saved, handle not printed)")
    except Exception:
        print("Token saved. Profile check skipped — ingest --live will verify.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
