# That Post — install instructions (v1.4.3)

**That Post** is a private search index of **your** X bookmarks, likes, and posts. It lives on your PC. You search by idea, topic, or keyword — not by scrolling X. An optional copy can be opened on your phone. Keep that Netlify site **private**.

That Post is **open source** under the **MIT License**. You do **not** need Hermes.

Hand this file (and the zip) to ChatGPT, Claude, Grok, or any competent assistant and say:

> Walk me through installing That Post on this computer. Follow `Install_Instructions.md`. Do not ask me to paste secrets into chat.

---

## What you were given

Two files are enough:

1. **`that-post-pc-YYYY-MM-DD.zip`** — the program. No secrets. No live database.
2. **This `Install_Instructions.md`** — the procedure. A copy also sits inside the zip.

Unzip the zip to a folder. Do **all** work inside that folder.

- **Windows:** `install.bat`, `enrich.bat`, `publish.bat`, and `sync.bat` live there, next to `scripts/`, `gui/`, and `x_oauth.example.json`.
- **Mac / Linux:** ignore the `.bat` files. Use `python3 scripts/setup_local.py` (same folder).

The zip does **not** include `data/x_oauth.json` or `data/ideas.sqlite`. You add those below.

Work on a machine (or a **windowed** VM) with a desktop and Firefox or Chrome **on this same OS**. A headless / SSH-only machine will not finish X login. Inside a VM, use the **guest** browser, not the host. Linux Mint’s usual desktop ISO is fine; a server-only install is not.

---

## What the install does

Do these in order. You can stop after F and still have a working PC search.

`install.bat` (Windows) or `python3 scripts/setup_local.py` (Mac/Linux) is **one run**, not a wizard that pauses for accounts. Put `data/x_oauth.json` in place (or copy an existing `ideas.sqlite`) **before** a successful full run.

| | Step | Required? |
| --- | --- | --- |
| **A** | Unzip | Yes |
| **B** | X Developer app + `$5` credits, then `data\x_oauth.json` — **or** copy an existing `data\ideas.sqlite` | Yes, unless you already have `ideas.sqlite` |
| **C** | Windows: double-click `install.bat`. Mac/Linux: `python3 scripts/setup_local.py` | Yes |
| **D** | OpenRouter account, `$5` credits, API key | Strongly recommended |
| **E** | Enrich with **gemini-3.5-flash-lite** via OpenRouter (search by concept, not only keywords) | Strongly recommended. **D and E can be skipped and done later** (`enrich.bat` or `python3 scripts/enrich_later.py`) |
| **F** | Search in a browser **on this computer** | Yes |
| **G** | Publish a Netlify copy for phone / any browser (keep the site **private**) | Optional |
| **H** | Later: sync (X + enrich new rows), then republish | Optional, after you use it |

This first install typically spends **under $1** on X and **under $1** on OpenRouter. Both services take **$5** as the smallest credit purchase, so leftover credits stay for **H**.

---

## If you are an AI helping someone

1. **Do not** ask for X passwords, API keys, client secrets, Netlify tokens, or tweet JSON in chat. Those stay on their computer.
2. **Do not** offer to type their X password. X shows a real login page in *their* browser on *this* PC (the VM guest, if this is a VM).
3. Finish **A–F** before **G**. Do not mix them into one wizard.
4. **Do not** use X’s official logo.
5. Detect the OS. **Windows:** `install.bat` / `enrich.bat` / `publish.bat` / `sync.bat`. Ignore a Microsoft Store “Python was not found” popup — that stub is not real Python. **Mac / Linux:** do **not** run `.bat` files. Use `python3 scripts/setup_local.py`, then `.venv/bin/python scripts/enrich_later.py`, `publish.py`, `sync_x.py`.
6. If `data/ideas.sqlite` already has posts, skip B and the X download.
7. Invisible paste (`getpass`) is normal. Paste **once**. A double paste is a bad token.
8. Stop and wait whenever they must use a browser on their machine.
9. **Encourage D and E.** Skipping enrich means keyword-only search after they already did the hard X work. If they skip now, show them `enrich.bat` (Windows) or `python3 scripts/enrich_later.py` (Mac/Linux) before you finish.
10. If install prints that `data/x_oauth.json` is missing, that is expected when B is not done. Finish B, then run install **again**. Do not invent a client id.

---

## A — Unzip

Unzip the zip. Stay in that folder.

---

## B — X Developer API ($5 credits; this install uses less than $1)

Skip this section if they already copied a working `ideas.sqlite` into `data/`.

Someone (usually the person installing) needs an **X developer app**. Calls are **pay-per-usage**. Buy **$5** of credits if the balance is under about **$1**. This install uses **less than $1**.

X Premium / SuperGrok / Grok credits do **not** pay for this. The Credits page itself says Grok API credits are bought elsewhere; the balance on **this** page is what That Post uses.

The portal UI moves around. These labels matched **console.x.com** in September 2026. Never paste Client ID, Client Secret, Consumer Key, or Bearer Token into chat. Put them only in `data/x_oauth.json` on disk.

### Create the app

1. Open https://console.x.com/ (or https://developer.x.com/ — it sends you to the console). Sign in with the X account that will own the app.
2. Left sidebar: **Access** → **Apps**.
3. **+ Create App**.
4. **Application Name:** anything they will recognize. Connect it to the default **Pay Per Use** project. **Create**.
5. A dialog **Application Created Successfully** shows **Consumer Key**, **Secret Key**, and **Bearer Token**. **Ignore these. Do not copy them.** They are OAuth 1.0 / app-only. That Post does not use them. Click **Close**.

### Turn on OAuth 2.0 (this is the part That Post needs)

6. Click the app name to open it. Stay on **Keys & Tokens**.
7. Scroll to **OAuth 2.0 Keys** → **User authentication settings** → **Set up**.
8. **Type of App:** **Native App** (it will say Public client). That is the working choice.
9. **App permissions:** **Read** (not Read and write). That Post cannot tweet.
10. **Callback URI / Redirect URL** — **exactly**, including `/callback`:

    `http://127.0.0.1:8080/callback`

    `http://127.0.0.1:8080` without `/callback` will fail login.
11. **Website URL** (required): any `https://` site they control (a personal homepage is fine).
12. **Save Changes**.

### Copy Client ID and Client Secret (once)

13. A dialog **Did you save your OAuth 2.0 Client Secret?** shows **Client ID** and **Client Secret**. These two strings go in the JSON file. They are shown **once**. Copy them into the file below (a local notepad is fine as a holding place). Click **Close**.
14. In the unzipped That Post folder:

    ```
    mkdir -p data
    cp x_oauth.example.json data/x_oauth.json
    ```

    Windows Explorer: copy `x_oauth.example.json` to `data\x_oauth.json`.
15. Edit `data/x_oauth.json` so it looks like this (their real values, still never in chat):

    ```
    {
      "client_id": "PASTE_CLIENT_ID_HERE",
      "client_secret": "PASTE_CLIENT_SECRET_HERE"
    }
    ```

    Use the **Client ID** / **Client Secret** from step 13, not Consumer Key / Secret Key.

### Credits

16. Left sidebar: **Billing** → **Credits**. If **Remaining balance** is under about **$1**, click **Purchase credits** and add **$5**.
17. If a later download prints HTTP **402** (credits depleted), keep any rows already saved — that is not a failed install.

---

## C — `install.bat` (Python + database)

Double-click **`install.bat`**.

- Finds real Python 3.11+ (any 3.11–3.16 folder) or installs Python 3.12 with winget. Store `python.exe` is skipped.
- If winget runs, this same window should find python.exe afterward. Do not close just because of a pause.
- Creates `.venv` and installs packages.
- If `data\ideas.sqlite` already has posts: skips X and OpenRouter and jumps to **F**.
- If the database is empty: needs `data\x_oauth.json`, then opens X login.

A browser window asks them to sign in to **X** and click **Allow**. That is X’s real login page. They have **3 minutes**. Tell them:

> A browser will ask you to sign in to X. That is X’s login page, not us collecting a password. Sign in the way you always do. Allow read access to bookmarks, likes, and posts. Click **Allow**. When it says That Post is connected, close the tab and tell me you’re done. I will never ask for your password.

Success: the script prints `OK — login works` or `Token saved` and does **not** print a token. Timeout: run `install.bat` again.

It then downloads recent bookmarks, posts, and likes. Live bookmarks are roughly the newest ~800; older saves need a JSON dump (`ingest_bookmarks.py --seed --seed-dir …`). Likes are a recent slice, not a lifetime archive.

If an OpenRouter key is already in `data\.env`, it enriches in this same run (**E**). Otherwise it asks for a key (paste once, nothing shows) or Enter to skip.

---

## D — OpenRouter ($5 credits; this install uses less than $1)

**Do this.** Enrichment is what makes search-by-idea work.

1. Open https://openrouter.ai/ and create an account.
2. Add **$5** of credits (typical minimum; leftover is for later updates).
3. Create an API key.
4. When `install.bat` (or later `enrich.bat`) asks, paste the key **once** on that PC. Nothing should appear as they type. Never paste the key into chat.

That Post calls **`google/gemini-3.5-flash-lite`** on OpenRouter.

---

## E — Enrich the database (concept / topic search)

`install.bat` runs this when an OpenRouter key is present.

If they skipped D during install, double-click **`enrich.bat`** any time later (after Part 1 works). It asks for the OpenRouter key if needed, then summarizes posts. Resume-safe if it stops midway.

Without E, search still runs, but only against the raw post text — not summaries or topic keywords. After the X work, that is a poor trade.

---

## F — Search on this PC

`install.bat` opens http://127.0.0.1:8790/ in a **second window**. Leave that window open.

- No PIN on this local page (loopback only).
- Default sort: **Newest**. **Query Help** is on the page.
- Reload the page after a later sync to see new rows.
- Picking a bookmark folder narrows to bookmarks in that folder. **(No folder)** is uncategorized bookmarks.

This address is only on this computer (loopback). It is not the phone page.

When install finishes, the last lines in the window should be the local search URL.

---

## G — Phone / any browser (optional)

After F works, double-click **`publish.bat`**.

1. First time: paste a Netlify personal access token once (https://app.netlify.com/user/applications#personal-access-tokens). Typing is invisible. Later runs reuse the same site.
2. The last thing in the window should be the `https://….netlify.app` URL. Open that — there is **no PIN on the page**.
3. **Keep the Netlify site private.** New sites usually start private. Private means you sign in with Netlify to view it. That is the security for this copy. If you Make it public, anyone with the URL can search your bookmarks.

If they skip the token, the script opens Netlify Drop and the `publish\` folder.

The public page is a **copy**. After you update the database (**H**), run `publish.bat` again. iPhone Chrome: close the tab, then reopen the URL.

---

## H — Later updates

From this folder, after the first install:

```
sync.bat
publish.bat
```

`sync.bat` refreshes X (same $5 developer credits) **and** enriches new rows (up to 200) with OpenRouter `google/gemini-3.5-flash-lite`. Reload http://127.0.0.1:8790/ after a sync. Then `publish.bat` if they use the phone copy.

Use **`enrich.bat`** only if they skipped summaries at install, or a large backlog remains.

If sync prints `AUTH_FAIL` (or exit code 2): run `scripts\auth_x.py`, they click Allow in the browser, then run **`sync.bat` again**.

---

## Pitfalls

- Port **8080** in use → stop that process before X login.
- Port **8790** in use → stop the other search-page window first.
- Search AND-is-default: `fertility TFR` requires both; use `OR`.
- Do not zip, email, or upload `data\ideas.sqlite` or `data\x_oauth.json`.
- Do not bind `:8790` to the LAN or WAN.
- Closing the extra window stops http://127.0.0.1:8790/.
- Laptop sleep pauses the local page.
- A double-pasted Netlify token is a bad token (HTTP 401). Delete `NETLIFY_AUTH_TOKEN` from `data\.env` and retry.
- If the Netlify page is public, anyone with the URL can search the index. Leave Visitor access **private**.

---

## Verification

- http://127.0.0.1:8790/ opens with no PIN; they recognize their own posts.
- After enrich, an idea/topic query can hit summaries, not only raw text.
- After publish: the printed URL opens search. Site should stay **private** on Netlify.

---

## macOS / Linux

Same A–H as above. Do **not** run `.bat` files. Firefox on Linux Mint is fine.

**Python 3.11+** (do this before C):

- **Linux Mint / Ubuntu / Debian:** Python is usually already 3.12. You still need the venv package:

  ```
  python3 --version
  sudo apt update
  sudo apt install -y python3-venv python3-pip
  ```

  Do **not** `pip install` into system Python (PEP 668). `setup_local.py` creates `.venv`.

- **Mac:** install Python 3.12 from https://www.python.org/downloads/ or `brew install python@3.12`. Do not use an old Apple `/usr/bin/python3`.

**C — one command** (after B, from the unzipped folder):

```
python3 scripts/setup_local.py
```

That is the Unix `install.bat`: `.venv`, packages, X login in the **guest** browser (3 minutes), download, optional OpenRouter key, then the search page.

If it says `Could not create .venv`, the `python3-venv` package is missing — install it and run `setup_local.py` again.

On Mac/Linux the search page stays **in this terminal**. Last lines should include `http://127.0.0.1:8790/`. Leave it running. **Ctrl+C** stops it.

**E later / G / H** (use the venv python):

```
.venv/bin/python scripts/enrich_later.py
.venv/bin/python scripts/publish.py
.venv/bin/python scripts/sync_x.py
```

If sync prints `AUTH_FAIL`: `.venv/bin/python scripts/auth_x.py`, click Allow, then `sync_x.py` again.

Data dir is `data/` unless `THAT_POST_HOME` is set.

---

## After it works

MIT License — use and share the code. To thank the author: [paypal.me/artnking](https://www.paypal.me/artnking) (also a Donate link on the search page). Never ask for payment details in chat.
