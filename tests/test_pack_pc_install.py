"""Public zip must be the app, not the Hermes skill."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from pack_pc_install import ROOT, keep


def test_zip_keeps_runtime():
    for rel in (
        "install.bat",
        "sync.bat",
        "enrich.bat",
        "publish.bat",
        "Install_Instructions.md",
        "User_Guide.md",
        "README.md",
        "LICENSE",
        "VERSION",
        "requirements.txt",
        "scripts/setup_local.py",
        "scripts/sync_x.py",
        "gui/index.html",
    ):
        assert keep(ROOT / rel), rel


def test_zip_drops_hermes_and_dev():
    for rel in (
        "SKILL.md",
        "START-HERE.md",
        "INSTALL-PC.md",
        "INSTALL-PUBLISH.md",
        ".gitignore",
        "references/roadmap.md",
        "tests/test_version_check.py",
        "scripts/pack_pc_install.py",
        "scripts/test_gemini_enrich.py",
        "scripts/serve_publish.py",
        "scripts/publish_crypto.py",
        "scripts/query_ideas.py",
        "landing/index.html",
        "dev/landing/index.html",
        "docs/search.jpg",
    ):
        assert not keep(ROOT / rel), rel
