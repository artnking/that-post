# That Post — user guide

After install, this is the day-to-day file. For first-time setup, use **Install_Instructions.md**.

Search: http://127.0.0.1:8790/

Leave the extra window that `install.bat` (or `setup_local.py`) opened running. Closing it stops local search until you start it again.

## Keep the index up to date

**Windows:** double-click `sync.bat`  
**Mac / Linux:** `python3 scripts/sync_x.py`

That pulls new bookmarks, likes, and posts from X, then summarizes **new** rows (OpenRouter). Reload the search tab when it finishes. A tab that was already open does not update until you refresh.

If sync says login expired (`AUTH_FAIL`):

**Windows:** in that folder, run `scripts\auth_x.py` with the same Python you used for install (usually `.venv\Scripts\python.exe scripts\auth_x.py`). Click **Allow** in the browser, then `sync.bat` again.  
**Mac / Linux:** `python3 scripts/auth_x.py`, then `python3 scripts/sync_x.py`.

Do this on the same computer (same browser) as That Post. Do not type your X password into chat.

## Summaries you skipped

If you skipped OpenRouter at install, idea-search is weaker until you enrich.

**Windows:** `enrich.bat`  
**Mac / Linux:** `python3 scripts/enrich_later.py`

`sync.bat` already enriches **new** posts. `enrich.bat` is for the backlog.

## Phone copy (optional)

**Windows:** `publish.bat`  
**Mac / Linux:** `python3 scripts/publish.py`

That uploads a stripped snapshot to Netlify. Keep that site **private**. After a later sync, publish again if you want the phone copy to match. Reload or reopen the Netlify URL.

Local search does not need publish. Reload the local tab after sync.

## New version of That Post

On the search page: **Check for updates**. If GitHub has a newer zip, download it, unzip it, and run install again.

**Keep your `data/` folder** (bookmarks and keys). Copy `data/` from the old folder into the new one, or unzip over the app without replacing `data/`.

## Do not share

- `data/ideas.sqlite` — your archive  
- `data/x_oauth.json` — API keys  
- `data/.env` — tokens  

## Contact

ThatPost@audiobalance.com  
Bugs: https://github.com/artnking/that-post/issues
