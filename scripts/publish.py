#!/usr/bin/env python3
"""Part 2: lock a snapshot and put it on Netlify.

Uses the Netlify API (no Node, no drag-and-drop after the first token).
Never prints tokens or the Publish PIN.
"""
from __future__ import annotations

import getpass
import os
import sys
import webbrowser
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from export_publish import copy_site, snapshot_stripped  # noqa: E402
from netlify_deploy import (  # noqa: E402
    NetlifyAuthError,
    create_site,
    deploy_zip,
    make_public,
    site_url,
    zip_dir,
)
from paths import DB, load_env, upsert_env  # noqa: E402
from publish_crypto import encrypt_index  # noqa: E402


def _ask_secret(prompt: str) -> str:
    print("  (nothing will appear as you type or paste — that is normal)")
    try:
        return getpass.getpass(prompt).strip()
    except EOFError:
        return ""


def build_locked(out: Path, password: str) -> Path:
    if not DB.exists():
        raise SystemExit("No database yet. Run install.bat first (or copy ideas.sqlite into data\\).")
    print("Building locked search copy …")
    plain = snapshot_stripped(DB)
    blob = encrypt_index(plain, password)
    copy_site(out)
    dest = out / "ideas.sqlite.enc"
    dest.write_bytes(blob)
    print(f"wrote {out}")
    return dest


def ask_netlify_token() -> str:
    print()
    print("One-time Netlify token (so you do not have to drag a folder):")
    print("  1. Open https://app.netlify.com/user/applications#personal-access-tokens")
    print("  2. New access token → generate")
    print("  3. Paste it ONCE, then press Enter")
    webbrowser.open("https://app.netlify.com/user/applications#personal-access-tokens")
    token = _ask_secret("NETLIFY_AUTH_TOKEN: ")
    if token:
        upsert_env("NETLIFY_AUTH_TOKEN", token)
        print("Saved Netlify token in data/.env (value not printed).")
    return token


def main() -> int:
    out = ROOT / "publish"
    env = load_env()
    password = env.get("THAT_POST_PUBLISH_PASSWORD") or os.environ.get("THAT_POST_PUBLISH_PASSWORD") or ""
    if not password:
        password = _ask_secret("Publish PIN (exactly 4 digits, not 1234): ")
        if password:
            upsert_env("THAT_POST_PUBLISH_PASSWORD", password)
            print("Saved Publish PIN in data/.env (value not printed).")
    if not password:
        raise SystemExit("Need a 4-digit Publish PIN.")
    if not (password.isdigit() and len(password) == 4):
        raise SystemExit("Publish PIN must be exactly 4 digits.")
    if password == "1234":
        raise SystemExit("Do not reuse the local PIN 1234 for a public copy.")

    build_locked(out, password)

    token = env.get("NETLIFY_AUTH_TOKEN") or os.environ.get("NETLIFY_AUTH_TOKEN") or ""
    if not token:
        token = ask_netlify_token()
    if not token:
        print()
        print("No token — open the publish folder and drag it onto Netlify Drop.")
        print("  https://app.netlify.com/drop")
        webbrowser.open("https://app.netlify.com/drop")
        if os.name == "nt":
            os.startfile(out)  # type: ignore[attr-defined]
        return 0

    site_id = env.get("NETLIFY_SITE_ID") or os.environ.get("NETLIFY_SITE_ID") or ""
    for _attempt in range(3):
        try:
            if not site_id:
                print("Creating a Netlify site …")
                info = create_site(token)
                site_id = str(info.get("id") or "")
                if not site_id:
                    raise SystemExit("Netlify did not return a site id.")
                upsert_env("NETLIFY_SITE_ID", site_id)
                url = site_url(info)
                if url:
                    print(f"Site {url}")
            print("Uploading …")
            info = deploy_zip(token, site_id, zip_dir(out))
            url = site_url(info) or info.get("deploy_ssl_url") or info.get("ssl_url") or ""
            if not make_public(token, site_id):
                print("Could not flip Netlify ‘Make public’ from here.")
                print("If the phone asks you to log into Netlify, open the site in the")
                print("dashboard → Visitor access → Project visibility → Make public.")
            print("Published.")
            if url:
                print(url)
                webbrowser.open(str(url))
            else:
                print("Open the site from your Netlify dashboard if the URL did not print.")
            print("Phone: open that URL and type the 4-digit Publish PIN.")
            return 0
        except NetlifyAuthError:
            print()
            print("Netlify rejected the saved token (Access Denied).")
            print("Generate a NEW token and paste it once. Typing is invisible.")
            upsert_env("NETLIFY_SITE_ID", "")
            site_id = ""
            token = ask_netlify_token()
            if not token:
                return 1
    print("Still Access Denied. Check the token in the Netlify dashboard.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
