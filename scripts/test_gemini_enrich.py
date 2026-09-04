#!/usr/bin/env python3
"""One-off test: enrich a COPY of the index via Google AI Studio (not OpenRouter).

Does not touch data/ideas.sqlite. Does not write the API key to disk.
Paste the key in the console this script opens — nothing shows as you type.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime, timezone
from getpass import getpass
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from paths import DATA, DB  # noqa: E402

COPY_DB = DATA / "ideas.gemini-test.sqlite"
LOG = DATA / "logs" / "gemini-enrich-test.log"
SYSTEM = """You index X (Twitter) bookmarks for later search-by-idea.
Given one post (and optional notes), write JSON only:
{"summary": "one paragraph, what the idea is, not a restatement of every word",
 "keywords": ["keyword", "..."]}
Keywords: topics, people, products, events, concrete nouns. 8-25 items.
No hashtags required. No markdown. JSON only."""
DEFAULT_MODEL = "gemini-3.5-flash-lite"


class GeminiHTTPError(Exception):
    def __init__(self, status: int, message: str, retry_after: float | None = None):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.retry_after = retry_after


def log(msg: str) -> None:
    line = f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}  {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def copy_and_strip(src: Path, dest: Path) -> dict[str, int]:
    if not src.exists():
        raise SystemExit(f"Live DB missing: {src}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    for extra in (Path(str(dest) + "-wal"), Path(str(dest) + "-shm")):
        if extra.exists():
            extra.unlink()
    src_con = sqlite3.connect(str(src))
    dst_con = sqlite3.connect(str(dest))
    try:
        src_con.backup(dst_con)
    finally:
        src_con.close()
    before = int(dst_con.execute("SELECT COUNT(*) FROM bookmarks").fetchone()[0])
    had = int(
        dst_con.execute(
            "SELECT COUNT(*) FROM bookmarks WHERE IFNULL(enriched_at,'') != ''"
        ).fetchone()[0]
    )
    dst_con.execute(
        "UPDATE bookmarks SET summary = NULL, keywords = NULL, enriched_at = NULL"
    )
    dst_con.commit()
    left = int(
        dst_con.execute(
            "SELECT COUNT(*) FROM bookmarks WHERE IFNULL(enriched_at,'') != ''"
        ).fetchone()[0]
    )
    dst_con.close()
    return {"rows": before, "had_enrich": had, "left_enrich": left}


def clean_key(raw: str) -> str:
    key = (raw or "").strip().strip('"').strip("'")
    if key.lower().startswith("bearer "):
        key = key[7:].strip()
    return key


def describe_key(key: str) -> str:
    if not key:
        return "empty"
    prefix = key[:4]
    return f"len={len(key)} prefix={prefix!r} last4=...{key[-4:]}"


def ask_key() -> str:
    import os

    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        v = clean_key(os.environ.get(name) or "")
        if v:
            log(f"Using {name} from the environment ({describe_key(v)}).")
            return v
    print()
    print("Paste your Google API key, then Enter.")
    print("  Page: https://aistudio.google.com/apikey  (it is labeled API key)")
    print("  Click the copy icon on the key row — the list only shows ...last4,")
    print("  which is not the key. You want a long string (often starts with AIza or AQ.).")
    print("  Typing/paste is invisible — that is normal. Paste ONCE.")
    print("  Do not Set up billing; Free tier is enough. The key is not saved to disk.")
    key = clean_key(getpass("API key: "))
    if not key:
        raise SystemExit("No key — nothing was sent.")
    if key.startswith("...") or len(key) < 20 or key.startswith("gen-lang-client"):
        raise SystemExit(
            "That is not the full API key (too short, or the masked ...last4 / project id). "
            "On the API Keys page click the copy icon, then paste here once."
        )
    log(f"Key accepted for this run ({describe_key(key)}). Not saved.")
    return key


def _google_error_message(raw: bytes) -> str:
    try:
        data = json.loads(raw.decode("utf-8", errors="replace"))
        err = data.get("error") or {}
        return str(err.get("message") or data)[:400]
    except Exception:
        return raw.decode("utf-8", errors="replace")[:400]


def chat_gemini(model: str, key: str, user: str) -> dict:
    import urllib.error
    import urllib.request

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )
    body = {
        "system_instruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 500,
            "responseMimeType": "application/json",
        },
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": key,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except TimeoutError as e:
        raise GeminiHTTPError(598, "read timed out", 8.0) from e
    except urllib.error.HTTPError as e:
        msg = _google_error_message(e.read() if e.fp else b"")
        retry = None
        if e.code == 429:
            raw = e.headers.get("Retry-After") if e.headers else None
            try:
                retry = max(1.0, float(raw)) if raw else 20.0
            except ValueError:
                retry = 20.0
        raise GeminiHTTPError(e.code, msg, retry) from None
    except urllib.error.URLError as e:
        reason = str(getattr(e, "reason", e))
        if "timed out" in reason.lower():
            raise GeminiHTTPError(598, reason, 8.0) from e
        raise GeminiHTTPError(599, reason, 8.0) from e

    parts = (
        ((payload.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
    )
    text = "".join(str(p.get("text") or "") for p in parts).strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    if not text:
        raise RuntimeError(f"Empty model reply: {str(payload)[:200]}")
    return json.loads(text)


def retry_after_seconds(err: BaseException) -> float | None:
    if isinstance(err, GeminiHTTPError) and err.status == 429:
        return err.retry_after or 20.0
    if isinstance(err, GeminiHTTPError) and err.status in {598, 599}:
        return err.retry_after or 8.0
    if isinstance(err, TimeoutError) or "timed out" in str(err).lower():
        return 8.0
    return None


def preflight(model: str, key: str) -> None:
    log(f"Preflight {model} ({describe_key(key)})")
    try:
        out = chat_gemini(
            model,
            key,
            "@test\nA short post about rain barrels for a garden.",
        )
    except GeminiHTTPError as e:
        log(f"Preflight failed: {e}")
        if e.status in {401, 403}:
            raise SystemExit(
                "Google rejected the API key. On the API Keys page click the copy "
                "icon (not the visible ...JXnw). Paste ONCE. Leave billing on Free tier."
            ) from e
        raise SystemExit(f"Preflight failed: {e}") from e
    if not (out.get("summary") or out.get("keywords")):
        raise SystemExit(f"Preflight: model did not return summary/keywords: {out!r}")
    log("Preflight OK — Google accepted the key. Starting the copy database.")


def enrich(db: Path, key: str, model: str, limit: int, sleep_s: float) -> int:
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    rows = list(
        con.execute(
            "SELECT id, author_username, text, image_notes, reply_notes FROM bookmarks "
            "WHERE enriched_at IS NULL AND IFNULL(text,'') != '' "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
    )
    total_left = int(
        con.execute(
            "SELECT COUNT(*) FROM bookmarks "
            "WHERE enriched_at IS NULL AND IFNULL(text,'') != ''"
        ).fetchone()[0]
    )
    log(f"db {db}")
    log(f"model {model}")
    log(f"this run {len(rows)}  still-unenriched {total_left}  sleep {sleep_s}s")
    ok = fail = limited = 0
    t0 = time.perf_counter()
    try:
        for i, r in enumerate(rows, 1):
            blob = f"@{r['author_username']}\n{r['text']}"
            if r["image_notes"]:
                blob += f"\nIMAGE: {r['image_notes']}"
            if r["reply_notes"]:
                blob += f"\nREPLIES: {r['reply_notes']}"
            attempt = 0
            while True:
                attempt += 1
                try:
                    log(f"call {i}/{len(rows)} try {attempt}")
                    out = chat_gemini(model, key, blob)
                    summary = (out.get("summary") or "").strip()
                    kws = out.get("keywords") or []
                    if isinstance(kws, list):
                        keywords = ", ".join(str(x) for x in kws)
                    else:
                        keywords = str(kws)
                    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
                    con.execute(
                        "UPDATE bookmarks SET summary=?, keywords=?, enriched_at=? WHERE id=?",
                        (summary, keywords, now, r["id"]),
                    )
                    con.commit()
                    ok += 1
                    elapsed = time.perf_counter() - t0
                    rate = ok / elapsed if elapsed else 0
                    log(
                        f"ok {ok}/{len(rows)}  elapsed {elapsed:.0f}s  "
                        f"{rate * 60:.1f}/min  {summary[:70]}"
                    )
                    break
                except Exception as e:
                    wait = retry_after_seconds(e)
                    if wait is not None and attempt <= 8:
                        limited += 1
                        log(f"retry {r['id']} {type(e).__name__} — sleep {wait:.0f}s (try {attempt})")
                        time.sleep(wait)
                        continue
                    fail += 1
                    log(f"fail {r['id']}: {type(e).__name__}: {e}")
                    if isinstance(e, GeminiHTTPError) and e.status in {401, 403}:
                        log("Stopping — Google rejected the API key.")
                        raise SystemExit(3) from e
                    if "quota" in str(e).lower() or "exceeded" in str(e).lower():
                        log("Stopping — looks like a daily/quota cap. Re-run later; it resumes.")
                        raise SystemExit(2) from e
                    break
            time.sleep(sleep_s)
    finally:
        elapsed = time.perf_counter() - t0
        remain = int(
            con.execute(
                "SELECT COUNT(*) FROM bookmarks "
                "WHERE enriched_at IS NULL AND IFNULL(text,'') != ''"
            ).fetchone()[0]
        )
        con.close()
        log(
            f"DONE ok={ok} fail={fail} rate_limit_hits={limited}  "
            f"{elapsed:.1f}s ({elapsed / 60:.1f} min)  still-unenriched={remain}"
        )
        log(f"log file {LOG}")
    return 0 if fail == 0 else 1


def main() -> int:
    p = argparse.ArgumentParser(description="Test Gemini enrich on a copy of the index.")
    p.add_argument("--prepare-only", action="store_true", help="Copy+strip live DB, then exit.")
    p.add_argument("--refresh-copy", action="store_true", help="Rebuild the copy from live DB.")
    p.add_argument("--limit", type=int, default=10_000)
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument(
        "--sleep",
        type=float,
        default=4.0,
        help="Seconds between calls (default 4 ≈ under 15 RPM).",
    )
    p.add_argument("--db", default=str(COPY_DB))
    args = p.parse_args()
    dest = Path(args.db)

    if args.prepare_only or args.refresh_copy or not dest.exists():
        log(f"Copying live index → {dest}")
        stats = copy_and_strip(DB, dest)
        log(
            f"copy rows={stats['rows']}  stripped enrich {stats['had_enrich']} → "
            f"{stats['left_enrich']}"
        )
        if args.prepare_only:
            log("Prepare only. Live data/ideas.sqlite was not modified.")
            return 0

    key = ask_key()
    preflight(args.model, key)
    return enrich(dest, key, args.model, args.limit, args.sleep)


if __name__ == "__main__":
    raise SystemExit(main())
