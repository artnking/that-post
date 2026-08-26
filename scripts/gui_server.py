#!/usr/bin/env python3
"""Read-only local API for the Ideas on X search page. Bind loopback only."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import search_ideas  # noqa: E402

SKILL = SCRIPTS.parent
GUI_HTML = SKILL / "gui" / "index.html"
ENV = Path.home() / ".hermes" / ".env"
INTERPRET_MODEL = "google/gemini-3.5-flash-lite"
TYPE_FLAGS = ("bookmark", "post", "reply", "repost", "like")

app = FastAPI(title="Ideas on X", docs_url=None, redoc_url=None)


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if not ENV.exists():
        return out
    for line in ENV.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


class InterpretIn(BaseModel):
    sentence: str = Field(min_length=1, max_length=500)


class InterpretOut(BaseModel):
    q: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    include_undated: bool | None = None
    enriched_only: bool | None = None
    author: str | None = None
    category: str | None = None
    types: list[str] | None = None
    limit: int | None = None
    sort: str | None = None


@app.get("/")
def index():
    if not GUI_HTML.exists():
        raise HTTPException(500, "gui/index.html missing")
    return FileResponse(GUI_HTML)


@app.get("/api/stats")
def api_stats():
    return search_ideas.stats()


@app.get("/api/search")
def api_search(
    q: str = "",
    date_from: str | None = None,
    date_to: str | None = None,
    include_undated: bool = True,
    enriched_only: bool = False,
    author: str = "",
    category: str = "",
    types: list[str] | None = Query(default=None),
    limit: int = 25,
    sort: str = "relevance",
):
    if types:
        types = [t for t in types if t in TYPE_FLAGS]
    rows = search_ideas.search(
        q=q,
        date_from=date_from or None,
        date_to=date_to or None,
        include_undated=include_undated,
        enriched_only=enriched_only,
        author=author,
        category=category,
        types=types,
        limit=limit,
        sort=sort,
    )
    return {"hits": len(rows), "rows": rows}


def _clean_interpret(raw: dict) -> dict:
    allowed = set(InterpretOut.model_fields)
    out = {k: raw[k] for k in raw if k in allowed}
    if "limit" in out and out["limit"] is not None:
        try:
            out["limit"] = max(10, min(100, int(out["limit"])))
        except (TypeError, ValueError):
            out.pop("limit")
    if out.get("sort") not in (None, "relevance", "newest", "oldest"):
        out["sort"] = "relevance"
    if out.get("types") is not None:
        out["types"] = [t for t in out["types"] if t in TYPE_FLAGS]
    for key in ("date_from", "date_to"):
        val = out.get(key)
        if val and not re.match(r"^\d{4}-\d{2}-\d{2}", str(val)):
            out[key] = None
    return InterpretOut(**out).model_dump()


@app.post("/api/interpret")
def api_interpret(body: InterpretIn):
    key = load_env().get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise HTTPException(503, "Interpret unavailable")
    from openai import OpenAI

    schema = {
        "q": "FTS5 query, use OR between alternate terms",
        "date_from": "YYYY-MM-DD or null",
        "date_to": "YYYY-MM-DD or null",
        "include_undated": True,
        "enriched_only": False,
        "author": "handle fragment or empty",
        "category": "exact folder name or empty",
        "types": list(TYPE_FLAGS),
        "limit": 25,
        "sort": "relevance|newest|oldest",
    }
    system = (
        "Map one English request onto this JSON schema for an X-post search form. "
        "JSON only. No SQL. No markdown. Omit keys you are not sure about.\n"
        + json.dumps(schema)
    )
    try:
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
        resp = client.chat.completions.create(
            model=INTERPRET_MODEL,
            temperature=0.1,
            max_tokens=400,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": body.sentence},
            ],
            extra_headers={
                "HTTP-Referer": "https://hermes-agent.local/ideas-on-x",
                "X-Title": "Ideas on X",
            },
        )
        text = (resp.choices[0].message.content or "").strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        raw = json.loads(text)
        if not isinstance(raw, dict):
            raise ValueError("not an object")
        if any(isinstance(v, str) and re.search(r"\b(SELECT|INSERT|UPDATE|DELETE)\b", v, re.I) for v in raw.values() if isinstance(v, str)):
            raise ValueError("sql refused")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "Interpret failed")
    return _clean_interpret(raw)
