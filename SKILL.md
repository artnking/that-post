---
name: ideas-on-x
description: "Search X bookmarks, posts, replies, reposts, and likes by idea."
version: 1.0.0
author: Art King, Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [x, twitter, bookmarks, search, sqlite, fts5]
    related_skills: []
---

# Ideas on X

Index Art's X bookmarks, his own posts/replies/reposts, and likes so he can
find "that post from weeks ago about topic X." X's own folders are a weak
search tool. This skill pulls those sources, writes a short idea-summary +
keywords, and stores them in SQLite FTS5. One tweet id = one row; type flags
can overlap (liked AND bookmarked).

Do **not** dump this SKILL.md into `PROJECTS.md`. One-line status only.

## When to Use

- "Find that X bookmark about…"
- "Search my bookmarks / posts / likes for…"
- "Open the Ideas on X search page"
- "Weekly X sync" / "refresh my bookmarks"
- "Refresh / ingest / enrich Ideas on X"
- Revive the old `OpenClaw skills/X bookmarks` dumps

**Don't use for:** posting on X, general web search, BookBack, the master disk index.

## What you get

Each row: original text, author, **type flags** (bookmark / post / reply /
repost / like), **bookmark_category** (X folder name when the API returns it),
**summary paragraph**, **keywords**, optional image notes, optional top-reply
notes. Query is FTS5 over the text fields — idea language, not just exact tweet
wording.

## Prerequisites

- Python 3.11 on this PC (already used by Hermes).
- Data dir: `%USERPROFILE%\.hermes\ideas-on-x\` (`ideas.sqlite`, `state.json`, `media/`).
- Seed JSON (already on disk): `~/.hermes/skills/OpenClaw skills/X bookmarks/*.json`
- **Full live pull** needs the existing X developer app ("XURL access from Hermes")
  as a **user** login (`bookmark.read tweet.read users.read like.read`), not the portal
  "Bearer Token" (that is app-only and cannot read bookmarks).
  Do not paste secrets into chat.
  1. Fill `~/.hermes/ideas-on-x/x_oauth.json` from `x_oauth.example.json`
  2. `python scripts/auth_x.py` on the PC — browser approve — writes `X_BEARER_TOKEN`
     into `~/.hermes/.env` without printing it.
- Image notes use `vision_analyze`. Reply scrape uses X API if the token allows
  conversation search; otherwise skip replies and still index the post.

## How to Run

All commands via `terminal`, cwd anywhere. Use Hermes venv python on this PC:

```
& "$env:LOCALAPPDATA\hermes\hermes-agent\venv\Scripts\python.exe"
```

Git-bash:

```
"$LOCALAPPDATA/hermes/hermes-agent/venv/Scripts/python.exe"
```

Scripts live in this skill's `scripts/`.

## Quick Reference

```
python scripts/ingest_bookmarks.py --seed
python scripts/ingest_bookmarks.py --live
python scripts/ingest_bookmarks.py --posts --folders
python scripts/ingest_bookmarks.py --likes
python scripts/ingest_bookmarks.py --all
python scripts/enrich_bookmarks.py --limit 10
python scripts/query_ideas.py "your idea here"
python scripts/sync_x.py
python scripts/launch_gui.py
```

http://127.0.0.1:8790/ — localhost only.

Weekly sync: Hermes cron `Ideas on X weekly sync`, Wednesday 16:00 PDT.
`scripts/sync_x.py` refreshes the X token (no browser), ingests bookmarks/posts/replies/reposts/likes/folders, enriches new rows, Telegram even on +0.
If token refresh fails: say **ready** and click Allow.

Autostart: scheduled task `\IdeasOnX_Web` (Art logon +30s), same pattern as BookBack_Web / BlueBubbles.
Launcher: `%LOCALAPPDATA%\IdeasOnX-autostart\start-ideas-on-x.vbs`
Log: `~/.hermes/ideas-on-x/logs/web.log`

## Procedure

1. **Ingest IDs + text** (`ingest_bookmarks.py --seed` and/or `--live` / `--posts`
   / `--likes` / `--folders` / `--all`).
   Done when `SELECT COUNT(*) FROM bookmarks` is > 0 and `state.json` has `last_ingest`.
2. **Enrich** (`enrich_bookmarks.py`). For each unenriched row: media → optional
   vision note; top replies if available; one summary paragraph + keyword list
   via a cheap OpenRouter chat model (`OPENROUTER_API_KEY`). Resume-safe.
   Long runs: Telegram status every 15 minutes.
   Done when `enriched_at` is set on the batch you asked for.
3. **Query** (`query_ideas.py "<idea>"`). Return id, date, author, url, summary,
   and a snippet. Do not dump full tweet JSON into chat.
4. **Update `PROJECTS.md`** one row only: Status + Now.

## Database (SQLite FTS5)

File: `~/.hermes/ideas-on-x/ideas.sqlite`

`bookmarks` (one tweet id per row): id, author_id, author_username, author_name,
created_at, folder, bookmark_category, is_bookmark, is_post, is_reply, is_repost,
is_like, text, url, summary, keywords, image_notes, reply_notes, raw_json,
ingested_at, enriched_at.

Type flags are 0/1 and may overlap. `bookmark_category` is the X folder name
(also copied into `folder` so FTS can hit it).

`bookmarks_fts`: FTS5 on text, summary, keywords, image_notes, reply_notes,
author_username, folder.

## Pitfalls

- Weekly sync needs the PC on (Art auto-logs on). Token refresh uses `X_REFRESH_TOKEN`; if X revokes it, AUTH_FAIL until `auth_x.py`.
- Port 8790 in use: stop the previous `launch_gui.py` (Ctrl+C) before starting another.
- FTS AND-is-default: `fertility TFR` requires both terms — use `OR`.
- X folder listing exists (`GET .../bookmarks/folders`) but each folder only
  returns ~20 tweet **ids**, no pagination. Category will be incomplete; do not
  wait on folder-perfect data. Search is the product.
- Likes need `like.read` on the user token. If `liked_tweets` returns 403, run
  `auth_x.py` again and approve. The likes endpoint is a recent slice, not a
  lifetime archive (use an X data download later if Art wants older likes).
- Own timeline (`/users/:id/tweets`) includes replies and retweets; classify
  with `referenced_tweets` + `in_reply_to_user_id`.
- Live bookmark endpoint may cap around the most recent ~800. Older than that may
  never appear via API; keep seed JSON and any exports.
- `bookmarks_002.json` and `bookmarks_004.json` are duplicates. Ingest is idempotent
  on tweet id.
- `xurl` CLI skill is Linux/Mac. This skill uses Python + bearer token on Windows.
- Do not put `~/.xurl` or tokens in chat.
- Enrichment costs OpenRouter tokens. Default `--limit` for a first pass.
- Replies on old posts often fail on the recent-search API (7-day window). Skip
  rather than hang.

## Verification

- `query_ideas.py "test"` returns rows without error.
- Duplicate seed files do not double-count (`COUNT(DISTINCT id)` = `COUNT(*)`).
- After enrich, a topic query hits **summary/keywords**, not only the raw tweet text.
