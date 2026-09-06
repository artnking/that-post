# That Post

Idea search over what you bookmarked, liked, or posted.

**Download and install:** [https://audiobalance.com/thatpost](https://audiobalance.com/thatpost)

Private, local index of your X (Twitter) bookmarks, likes, and posts. Search by idea or keyword. Optional summaries. Optional phone copy on Netlify (keep that site private).

MIT License. Free.

## Install

1. Get the zip from the [download page](https://audiobalance.com/thatpost) or from **Releases** on this GitHub repo.
2. Unzip it.
3. Hand [Install_Instructions.md](Install_Instructions.md) to ChatGPT, Claude, Grok, DeepSeek, or any competent assistant and say:

   > Walk me through installing That Post on this computer. Follow Install_Instructions.md.

Windows, Linux, and Mac. Python 3.11+.

## Do not ship

- `data/ideas.sqlite` (your archive)
- `data/x_oauth.json` (API keys)
- `.env` (tokens)

Do not use X’s official logo.

## Agent skill

`SKILL.md` is the Hermes / OpenClaw skill. Folder name: `that-post`.
