#!/usr/bin/env python3
"""Shared data locations. Default: <skill>/data. Override with THAT_POST_HOME."""
from __future__ import annotations

import os
from pathlib import Path

HOME = Path.home()
SKILL_ROOT = Path(__file__).resolve().parent.parent
DATA = Path(
    os.environ.get("THAT_POST_HOME")
    or os.environ.get("THE_POST_HOME")
    or (SKILL_ROOT / "data")
).expanduser()
DB = DATA / "ideas.sqlite"
STATE = DATA / "state.json"
OAUTH_FILE = DATA / "x_oauth.json"
DATA_ENV = DATA / ".env"
HERMES_ENV = HOME / ".hermes" / ".env"
SEED_DIR_DEFAULT = DATA / "seed"
EMPTY_DB = SKILL_ROOT / "templates" / "empty.sqlite"

ENV_KEYS = (
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "X_BEARER_TOKEN",
    "X_REFRESH_TOKEN",
    "X_USER_ID",
    "THAT_POST_HOME",
    "THE_POST_HOME",
    "THAT_POST_PASSWORD",
    "THE_POST_PASSWORD",
    "THAT_POST_PUBLISH_PASSWORD",
    "NETLIFY_AUTH_TOKEN",
    "NETLIFY_SITE_ID",
)


def _parse_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    out.update(_parse_env_file(HERMES_ENV))
    out.update(_parse_env_file(DATA_ENV))
    for k in ENV_KEYS:
        v = os.environ.get(k)
        if v:
            out[k] = v
    return out


def upsert_env(key: str, value: str) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    targets = [DATA_ENV]
    if HERMES_ENV.parent.exists():
        targets.append(HERMES_ENV)
    for path in targets:
        lines: list[str] = []
        if path.exists():
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        found = False
        out: list[str] = []
        for line in lines:
            if line.startswith(f"{key}=") or line.startswith(f"#{key}="):
                out.append(f"{key}={value}")
                found = True
            else:
                out.append(line)
        if not found:
            if out and out[-1].strip():
                out.append("")
            out.append(f"{key}={value}")
        path.write_text("\n".join(out) + "\n", encoding="utf-8")
