# That Post — roadmap

Updated 2026-09-04. Display name **That Post** (skill id `that-post`). Version **1.3.1**.

Install is **two parts**. They are different products:

1. **PC engine (Part 1)** — this computer builds and updates the private
   index (X login, ingest, optional summaries, local search at
   http://127.0.0.1:8790/). `install.bat`. VM tests **passed**.
2. **Publish (Part 2)** — `publish.bat` locks a snapshot and uploads with
   the Netlify API (same URL on later runs). Phone search **passed**.

Do not mix them in one wizard.

## Frozen copy

**Name:** That Post

**Tagline:** Idea search over what you bookmarked, liked, or posted.

**Description:** Find that post you saved and can’t find on X. It keeps a
private, local index of your bookmarks, likes, posts, replies, and reposts,
then summarizes each one so you can search by idea or keyword. Sync when you
want, or on a schedule.

Skill folder: `~/.hermes/skills/social-media/that-post` (code + `data/`).
Public zip must not include `data/ideas.sqlite`. Use `templates/empty.sqlite`.

## Current state

- Skill+data: `~/.hermes/skills/social-media/that-post`
- DB: `that-post/data/ideas.sqlite` (gitignored)
- Search UI: http://127.0.0.1:8790/ (loopback, HTTP basic PIN `1234`)
- Search runs **in the browser** (sqlite-wasm) against a snapshot of the DB.
  Reload the page after a sync to see new rows. Default sort: **Newest**.
- UI: dark page; our mark (not official X logo). Photo: PC right aside;
  phone small beside title, top ~¼.
- Bookmark folders: picking a folder narrows to bookmarks only (other type
  boxes auto-uncheck). `(No folder)` matches uncategorized bookmarks.
- Sketches (not shipped): `sketches/004-warm-editorial-v3` — approved Warm
  Editorial look (floating search band + Refine rail). Not yet ported to `gui/`.
- Weekly Hermes cron: **paused** (job `4808c4e2b14c`)
- Autostart: `\IdeasOnX_Web` → `launch_gui.py --no-open`

## Ladder

### 1. Portable skill — done

Agent Skills package. Any agent that can run Python.

### 2. Browser search as a snapshot — done

`gui/index.html` + `gui/app.js` load sqlite-wasm and search locally.
Server still binds `127.0.0.1:8790` and serves a non-WAL snapshot of
`ideas.sqlite`. Query Help (plain English).

### 3. Part 1 — PC install without Hermes — done

`START-HERE.md` + `install.bat`. Existing `ideas.sqlite` skips X download.
Store Python stub is skipped; winget can install 3.12.

### 4. Part 2 — publish snapshot — done (phone test)

`publish.bat` → AES-GCM `ideas.sqlite.enc` + Netlify API zip deploy.
First token is saved in `data/.env` (never print). New Netlify sites may
need **Make public** once. Do not reuse local PIN `1234`. Do not Drop
an unlocked sqlite.

### 5. Double-click desktop app — later

Same Part 1 engine, no “install Python first.”

### 6. Hosted multi-user web — not this product

Would store other people’s likes. Skip.

### 7. Native iPhone ingest app — last, probably never

Not needed if the PC keeps the database.

## Do not

- Bind `:8790` to the LAN or WAN
- Ship `data/ideas.sqlite` or `data/x_oauth.json` in a zip
- Put an unlocked index on Netlify
- Use X’s official logo
- Create a Cloudflare account or change nameservers until Art says go
- Promise the live X API recreates a lifetime archive
- Combine Part 1 and Part 2 into one first-run wizard
