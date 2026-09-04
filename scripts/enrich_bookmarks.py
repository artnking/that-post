#!/usr/bin/env python3
"""Add summary + keywords for unenriched bookmarks. Resume-safe.

Uses OpenRouter if OPENROUTER_API_KEY is set. Skips replies/vision in v0.1
unless --vision (agent should use vision_analyze separately for image posts).
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import sys

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from ingest_bookmarks import load_env  # noqa: E402
from paths import DB  # noqa: E402

SYSTEM = """You index X (Twitter) bookmarks for later search-by-idea.
Given one post (and optional notes), write JSON only:
{"summary": "one paragraph, what the idea is, not a restatement of every word",
 "keywords": ["keyword", "..."]}
Keywords: topics, people, products, events, concrete nouns. 8-25 items.
No hashtags required. No markdown. JSON only."""


def chat_openrouter(model: str, key: str, user: str) -> dict:
    from openai import OpenAI

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
    resp = client.chat.completions.create(
        model=model,
        temperature=0.2,
        max_tokens=500,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
        extra_headers={"HTTP-Referer": "https://localhost/that-post", "X-Title": "That Post"},
    )
    text = (resp.choices[0].message.content or "").strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--model", default="google/gemini-3.5-flash-lite")
    args = p.parse_args()
    env = load_env()
    key = env.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY missing — enrich needs it")
    if not DB.exists():
        raise SystemExit("run ingest_bookmarks.py --seed first")
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = list(
        con.execute(
            "SELECT id, author_username, text, image_notes, reply_notes FROM bookmarks "
            "WHERE enriched_at IS NULL AND IFNULL(text,'') != '' "
            "ORDER BY created_at DESC LIMIT ?",
            (args.limit,),
        )
    )
    print(f"enriching {len(rows)} of limit {args.limit}")
    ok = 0
    for r in rows:
        blob = f"@{r['author_username']}\n{r['text']}"
        if r["image_notes"]:
            blob += f"\nIMAGE: {r['image_notes']}"
        if r["reply_notes"]:
            blob += f"\nREPLIES: {r['reply_notes']}"
        try:
            out = chat_openrouter(args.model, key, blob)
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
            print(f"ok {r['id']}  {summary[:80]}")
        except Exception as e:
            print(f"fail {r['id']}: {e}")
        time.sleep(0.3)
    print(f"enriched {ok}/{len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
