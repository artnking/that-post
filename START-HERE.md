# That Post — start here (Windows)

You do **not** need Hermes. That Post is open source (MIT License).

Want an AI to walk you through it? Give it **`Install_Instructions.md`** and say: *Walk me through installing That Post. Follow that file. Do not ask me to paste secrets into chat.*

## On this computer (A–F)

1. Unzip this folder.
2. Optional: copy `ideas.sqlite` into `data\` if you already have an index
   (skips the X download).
3. Optional: copy `x_oauth.json` into `data\` only if you need a **new**
   download from X.
4. Double-click **`install.bat`**.

It installs Python if needed, builds the database from X, and strongly
encourages OpenRouter ($5 credits; this run uses well under $1) so search
can use **gemini-3.5-flash-lite** summaries. A **second window** opens
http://127.0.0.1:8790/ — leave that window open. Local PIN: **1234**
(any username).

If you skip OpenRouter during install, double-click **`enrich.bat`** later.

X Developer credits: buy **$5** (their minimum). This install uses less
than $1.

## Phone / any browser (G)

After local search works:

1. Double-click **`publish.bat`**.
2. Choose a **Publish PIN** (exactly 4 digits, not 1234).
3. First time only: paste a Netlify personal access token
   (paste once — nothing shows). Later publishes reuse it.

It prints a `https://….netlify.app` URL. Open that and type the Publish PIN.

New Netlify sites often start **private**. If the phone asks you to log into
Netlify, dashboard → Visitor access → Make public (once).

The public page is a **copy**. After a later sync, run `publish.bat` again.
iPhone Chrome: close the tab, then reopen the URL.

## Later updates (H)

```
.venv\Scripts\python scripts\sync_x.py
enrich.bat
publish.bat
```

## Do not

- Zip or email `data\ideas.sqlite` or `data\x_oauth.json` to strangers
- Reuse 1234 as the Publish PIN
- Close the search-page window if you still want http://127.0.0.1:8790/
