# That Post

Idea search over what you bookmarked, liked, or posted.

Private local index (SQLite + http://127.0.0.1:8790/). Skill id: `that-post`.
One folder: code + `data/` (live DB, gitignored). Public zip uses
`templates/empty.sqlite` only — never ship `data/ideas.sqlite`.

```
python3 -m pip install -r requirements.txt
mkdir -p data
cp x_oauth.example.json data/x_oauth.json
# fill client_id and client_secret; never commit that file
python3 scripts/auth_x.py
# A person at this computer signs in to X in the browser and clicks Allow.
# The agent must not ask for their password. See SKILL.md → "X login".
python3 scripts/ingest_bookmarks.py --all
python3 scripts/enrich_bookmarks.py --limit 10
python3 scripts/launch_gui.py
```

X app callback must be exactly `http://127.0.0.1:8080/callback`.
User OAuth scopes: `tweet.read users.read bookmark.read like.read offline.access`.

Optional: `THAT_POST_HOME` to put data somewhere else. `OPENROUTER_API_KEY` for summaries.

See `Install_Instructions.md` to walk a human (or ChatGPT / Claude / Grok) through install.
See `SKILL.md` for the agent procedure. See `references/roadmap.md` for later work.
