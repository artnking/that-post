---
name: that-post
description: "Idea search over your X bookmarks, likes, and posts."
version: 1.4.3
author: Art King, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [x, twitter, bookmarks, search, sqlite, fts5]
    related_skills: []
  openclaw:
    requires:
      bins: [python]
---

# That Post

Idea search over what you bookmarked, liked, or posted.

Find that post you saved and can’t find on X. Keeps a **private, local** SQLite
index of bookmarks, likes, posts, replies, and reposts, then summarizes each
row so you can search by idea or keyword. Sync on the PC; publish a snapshot
to Netlify for phone search (keep the site private).

Skill id / folder: `that-post`. Display name: **That Post**.
One folder holds the skill **and** live data (`data/`, gitignored except `.gitkeep`).
Public package: this folder **without** `data/ideas.sqlite`; include
`templates/empty.sqlite` (zero rows). First run creates `data/ideas.sqlite`.

Do **not** ship live `data/ideas.sqlite`, `data/x_oauth.json`, `.env`, or tweets.
Do **not** use X’s official logo (trademark). The page uses our own mark.

Windows install/publish: `Install_Instructions.md`, `START-HERE.md`, `install.bat`, `publish.bat`.

## When to Use

- “Find that X bookmark / like / post about…”
- “Search my X history by idea”
- “Open That Post search page”
- “Sync / refresh my X bookmarks”
- “Install that-post / That Post on this computer”
- “Publish That Post to the phone / Netlify”

**Don't use for:** posting on X, general web search, scraping other people’s
timelines, asking anyone for their X password.

## Prerequisites

From this skill directory:

```
python3 -m pip install -r requirements.txt
```

(`python` is fine if that is 3.11+.) Windows: `install.bat` skips the Microsoft
Store `python.exe` stub and can install Python 3.12 via winget.

**Developer app (once, whoever owns the X API app):**

- X developer portal (https://console.x.com/ → Apps): **Native App** (public
  client), **Read**, user OAuth 2.0. Not the Consumer Key / Bearer Token from
  the first “Application Created” dialog.
- Callback URI **exactly**: `http://127.0.0.1:8080/callback`
- Scopes: `tweet.read users.read bookmark.read like.read offline.access`
- Copy `x_oauth.example.json` to `data/x_oauth.json` and fill client id/secret.
  Never paste those values into chat.

**This machine:**

- A graphical desktop and a browser (Firefox or Chrome) **on this same OS**.
  SSH-only / headless does not.
- Data dir: `<this-skill>/data/` unless `THAT_POST_HOME` is set.
- Enrichment: OpenRouter (`google/gemini-3.5-flash-lite`). Strongly recommended.
  `$5` credits; a typical first run is well under `$1`. `enrich.bat` later if skipped.
- Phone copy: a Netlify account. First `publish.bat` asks for a personal
  access token (typing is invisible — paste once).

## X login (human in the browser)

The agent **cannot** finish login. X shows a web page. A person sitting at
**this** computer must sign in. Do not ask for their password. Do not offer to
type it. Do not run `auth_x.py` over SSH without a browser on the same machine.

**What the agent does**

1. Confirm `data/x_oauth.json` exists and is not still `PASTE_CLIENT_ID_HERE`.
   Do not print the file.
2. In a terminal on this machine, from the skill directory:

   ```
   python3 scripts/auth_x.py
   ```

3. The script prints `Opening X login in your browser…` and usually opens a
   tab. It waits **3 minutes**. If no window appears, it also prints a long
   `https://twitter.com/i/oauth2/authorize?...` URL — tell the human to paste
   that into Firefox/Chrome **inside this same OS** (the VM, not the host, if
   this is a VM).
4. Stop and tell the human what to do (script below). Wait for them.
5. Success: stdout contains `OK — login works` (or `Token saved`) and **does
   not** contain a token. Failure: `No login code (timed out)` → run the
   script again; they have 3 minutes after it starts. `X returned error` →
   they hit Cancel, or the callback URI / scopes on the app are wrong.

**What you tell the human:**

> A browser window is going to ask you to sign in to X. That is X’s real login
> page, not us collecting a password. Sign in the way you always do. If X
> asks which permissions to allow, allow them (read bookmarks, likes, and
> posts). Click **Allow** or **Authorize**. When the page says **That Post is
> connected**, you can close the tab and tell me you’re done. I will never
> ask for your password.

If they are already signed into X in that browser, they may only see Allow.

**What this grant is:** a token on **this computer only**, so That Post can
read *their* bookmarks, likes, and posts. It cannot tweet. They can revoke it
later on X: Settings → Security and account access → Apps and sessions.

## How to Run

From this skill directory:

```
python3 scripts/auth_x.py
python3 scripts/ingest_bookmarks.py --all
python3 scripts/ingest_bookmarks.py --seed --seed-dir /path/to/json/dumps
python3 scripts/enrich_bookmarks.py --limit 10
python3 scripts/query_ideas.py "your idea here"
python3 scripts/sync_x.py
python3 scripts/launch_gui.py --no-open
python3 scripts/publish.py
```

Windows: `install.bat` then optional `enrich.bat` then `publish.bat`. Existing
`data/ideas.sqlite` skips X login and download.

Local search: http://127.0.0.1:8790/ (loopback only, no PIN).
The page loads a **snapshot** of the SQLite index into the browser
(sqlite-wasm). Reload after a sync. Default sort is **Newest**. Query Help
explains AND / OR / quotes / `*` / NOT — no FTS jargon in the UI.

Phone: `publish.bat` uploads a stripped copy (`raw_json` removed) with the
Netlify API. Same URL on later runs. No app PIN — keep the Netlify site
**private** (Visitor access; sign in with Netlify).

Bookmark folders: picking one or more folders in the search page narrows to
bookmarks only (other type boxes auto-uncheck). `(No folder)` at the bottom
matches the 89-ish uncategorized bookmarks; it combines with real folders.

Schedule: the user’s agent cron can run `python3 scripts/sync_x.py`. Do not
assume a particular autostart wrapper.

If a later sync prints `AUTH_FAIL`: run `auth_x.py` again; the same human
clicks Allow.

## Search page

- Dark UI. Our own rounded-bar X mark — **not** the official X logo.
- Photo (`gui/assets/bg-phone.jpg`): **PC** — small, right side, not under
  text. **Phone** — small, beside the “That Post” title, top ~¼ of the screen.
- Netlify only gets a new look after those files are on **that**
  machine and `publish.bat` runs again. The live URL is a copy.

## Procedure

1. **Auth** — section “X login” above. Done when `auth_x.py` prints OK and
   does not print token values.
2. **Ingest** — `ingest_bookmarks.py --all`. Optional `--seed --seed-dir`.
   Done when `python3 scripts/query_ideas.py` with no args shows `rows > 0`.
3. **Enrich** (strongly recommended) — OpenRouter `google/gemini-3.5-flash-lite`.
   `enrich_bookmarks.py` or Windows `enrich.bat`. Resume-safe. Can run later.
4. **Search** — `query_ideas.py "<idea>"` or http://127.0.0.1:8790/
   Return id, date, author, url, summary, snippet. Do not dump `raw_json` or
   tokens into chat.
5. **Publish** — `publish.bat` / `scripts/publish.py`. Done when it prints a
   `https://….netlify.app` URL and search works. Keep the Netlify site private.

## Database

Live: `data/ideas.sqlite` (gitignored). Public template: `templates/empty.sqlite`.

`bookmarks`: one tweet id per row — text, url, summary, keywords, type flags
(`is_bookmark` / `is_post` / `is_reply` / `is_repost` / `is_like` may overlap),
`bookmark_category`, `raw_json`, timestamps.

`bookmarks_fts`: FTS5 on text, summary, keywords, image_notes, reply_notes,
author_username, folder.

## Pitfalls

- Browser and `auth_x.py` must share localhost.
- Live bookmarks API: newest ~800. Older saves need a JSON dump (`--seed-dir`).
- Likes are a recent slice, not a lifetime archive.
- Search AND-is-default: `fertility TFR` requires both terms — use `OR`.
- X folder listing is incomplete (~20 ids per folder). Search still works.
- `like.read` 403 → `auth_x.py` again and Allow.
- Replies on old posts often fail (recent-search 7-day window). Skip.
- Port 8790 in use: stop the other `launch_gui.py` first.
- Port 8080 in use: stop whatever is bound there before `auth_x.py`.
- Enrichment costs LLM credits. Start with `--limit 10`.
- X API HTTP 402 “credits depleted”: keep saved rows; not a failed install.
  SuperGrok does not fund Developer API credits.
- Windows Store `python.exe` is a stub (“install from Microsoft Store”).
  `install.bat` ignores it.
- `getpass` hides pasted Netlify tokens. Paste **once**, Enter. A double paste
  is a bad token (HTTP 401). Delete `NETLIFY_AUTH_TOKEN` from `data/.env` and retry.
- New Netlify sites start **private**. Leave them private — that is the lock
  (Netlify login). Do not Make public unless they accept anyone with the URL
  seeing their bookmarks.
- Do not print tokens, client secrets, or full tweet JSON in chat.
- Do not zip `data/ideas.sqlite` for a public package.
- Phone/Netlify will look unchanged until new `gui/` files are on the machine
  that runs `publish.bat`. iPhone Chrome: close the tab, then reopen the URL.

## Verification

- `python3 scripts/query_ideas.py "test"` returns without error (hits optional).
- `COUNT(DISTINCT id)` = `COUNT(*)` after ingest.
- After enrich, an idea query can hit **summary/keywords**, not only raw text.
- Human can open http://127.0.0.1:8790/ and recognize their own posts.
- After publish: the printed Netlify URL opens search (site kept private).
  Photo sits beside the title on a phone-width screen.
