# That Post — install instructions

**That Post** is a private search index of **your** X bookmarks, likes, and posts. It lives on your PC. You search by idea, topic, or keyword — not by scrolling X. An optional locked copy can be opened on your phone or any browser.

That Post is **open source** under the **MIT License**.

Hand this file to ChatGPT, Claude, Grok, or any competent assistant and say:

> Walk me through installing That Post on this computer. Follow `Install_Instructions.md`. Do not ask me to paste secrets into chat.

---

## What the install does

Do these in order. You can stop after F and still have a working PC search.

| | Step | Required? |
| --- | --- | --- |
| **A** | Install the local folders, scripts, and Python (if needed) | Yes |
| **B** | Configure the X Developer API, add **$5** of credits (their minimum), and put the app’s client id/secret in `data\x_oauth.json` | Yes, unless you already have `data\ideas.sqlite` |
| **C** | Build the database from your X bookmarks, posts, and likes | Yes (same exception as B) |
| **D** | Create an OpenRouter account, add **$5** of credits, get an API key | Strongly recommended |
| **E** | Enrich the database with **gemini-3.5-flash-lite** via OpenRouter so you can search by concept and topic, not only keywords | Strongly recommended. **D and E can be skipped and done later** with `enrich.bat` |
| **F** | Open the search page in a browser **on this PC** | Yes |
| **G** | Publish a locked public page for phone / any browser | Optional |
| **H** | Later: periodic updates (X + OpenRouter), then refresh local search and republish | Optional, after you use it |

This first install typically spends **under $1** on X and **under $1** on OpenRouter. Both services take **$5** as the smallest credit purchase, so leftover credits stay for **H**.

---

## If you are an AI helping someone

1. **Do not** ask for X passwords, API keys, client secrets, Netlify tokens, or tweet JSON in chat. Those stay on their computer.
2. **Do not** offer to type their X password. X shows a real login page in *their* browser on *this* PC.
3. Finish **A–F** before **G**. Do not mix them into one wizard.
4. **Do not** use X’s official logo.
5. Windows: use `install.bat` / `enrich.bat` / `publish.bat`. Ignore a Microsoft Store “Python was not found” popup — that stub is not real Python.
6. If `data\ideas.sqlite` already has posts, skip B and C.
7. Invisible paste (`getpass`) is normal. Paste **once**. A double paste is a bad token.
8. Stop and wait whenever they must use a browser on their machine.
9. **Encourage D and E.** Skipping enrich means keyword-only search after they already did the hard X work. If they skip now, show them `enrich.bat` before you finish.

---

## A — Folders, scripts, Python

Unzip this folder. Work on a PC with a desktop and Firefox or Chrome.

Double-click **`install.bat`**. It finds real Python 3.11+ or installs Python 3.12 with winget, creates `.venv`, and installs packages.

If `data\ideas.sqlite` already has posts, install skips X and OpenRouter and jumps toward **F**.

---

## B — X Developer API ($5 credits; this install uses less than $1)

Someone (usually the person installing) needs an X developer app. Calls are **pay-per-usage** on that project. Buy **$5** of credits — that is X’s minimum. This install uses **less than $1**.

1. Open https://developer.x.com/
2. Create or open an app with **user** OAuth 2.0 (not an app-only Bearer token).
3. Confidential client.
4. Callback URI **exactly**: `http://127.0.0.1:8080/callback`
5. Scopes: `tweet.read users.read bookmark.read like.read offline.access`
6. Copy `x_oauth.example.json` to `data\x_oauth.json` and fill `client_id` and `client_secret` **in that file on disk**. Never paste those values into chat.

If a download later prints HTTP **402** (credits depleted), keep any rows already saved — that is not a failed install. X Premium / SuperGrok does **not** fund Developer API credits.

---

## C — Build the database from X

`install.bat` continues here when the database is empty.

A browser window asks them to sign in to **X** and click **Allow**. That is X’s real login page. They have **3 minutes**. Tell them:

> A browser will ask you to sign in to X. That is X’s login page, not us collecting a password. Sign in the way you always do. Allow read access to bookmarks, likes, and posts. Click **Allow**. When it says That Post is connected, close the tab and tell me you’re done. I will never ask for your password.

Success: the script prints `OK — login works` or `Token saved` and does **not** print a token. Timeout: run `install.bat` again.

It then downloads recent bookmarks, posts, and likes. Live bookmarks are roughly the newest ~800; older saves need a JSON dump (`ingest_bookmarks.py --seed --seed-dir …`). Likes are a recent slice, not a lifetime archive.

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

- Local PIN: **1234** (any username), unless `THAT_POST_PASSWORD` is set.
- Default sort: **Newest**. **Query Help** is on the page.
- Reload the page after a later sync to see new rows.

This address is only on this computer (loopback). It is not the phone page.

---

## G — Phone / any browser (optional)

After F works, double-click **`publish.bat`**.

1. Choose a **Publish PIN**: **exactly 4 digits**, not `1234`. It is saved for next time.
2. First time: paste a Netlify personal access token once (https://app.netlify.com/user/applications#personal-access-tokens). Typing is invisible. Later runs reuse the same site.
3. Open the printed `https://….netlify.app` URL and enter the **Publish PIN**.
4. New Netlify sites often start **private**. If the phone asks you to log into Netlify: dashboard → Visitor access → Make public **once**.

If they skip the token, the script opens Netlify Drop and the `publish\` folder.

The public page is a **copy**. After you update the database (**H**), run `publish.bat` again. iPhone Chrome: close the tab, then reopen the URL.

---

## H — Later updates

From this folder, after the first install:

```
sync.bat  (runs scripts\sync_x.py)
enrich.bat
publish.bat
```

`sync_x.py` uses the X Developer API (credits on the same $5). `enrich.bat` uses OpenRouter (`gemini-3.5-flash-lite`) for new rows. `publish.bat` refreshes the phone copy. Reload http://127.0.0.1:8790/ after a sync.

If sync prints `AUTH_FAIL`, run `scripts\auth_x.py`; they click Allow again in the browser.

---

## Pitfalls

- Port **8080** in use → stop that process before X login.
- Port **8790** in use → stop the other search-page window first.
- Search AND-is-default: `fertility TFR` requires both; use `OR`.
- Do not zip, email, or upload `data\ideas.sqlite` or `data\x_oauth.json`.
- Do not bind `:8790` to the LAN or WAN.
- Do not reuse local PIN **1234** as the Publish PIN.
- Closing the extra window stops http://127.0.0.1:8790/.
- Laptop sleep pauses the local page.

---

## Verification

- http://127.0.0.1:8790/ opens with PIN **1234**; they recognize their own posts.
- After enrich, an idea/topic query can hit summaries, not only raw text.
- After publish: the public URL unlocks with the **4-digit Publish PIN**.

---

## macOS / Linux

Python 3.11+:

```
python3 -m pip install -r requirements.txt
# data/x_oauth.json filled on disk (never in chat)
python3 scripts/auth_x.py
python3 scripts/ingest_bookmarks.py --all
python3 scripts/enrich_bookmarks.py --limit 5000    # OpenRouter key; strongly recommended
python3 scripts/launch_gui.py
python3 scripts/publish.py                          # optional; 4-digit Publish PIN
```

Data dir is `data/` unless `THAT_POST_HOME` is set.

---

## After it works

MIT License — use and share the code. To thank the author: [paypal.me/artnking](https://www.paypal.me/artnking) (also a Donate link on the search page). Never ask for payment details in chat.
