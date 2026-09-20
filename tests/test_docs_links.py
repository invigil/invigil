"""Every relative link we ship must resolve.

PR #31 had to retire four links in `docs/README.md` pointing at pages that were
never written. The monthly log adds a file and an index line every cycle, which is
exactly the surface that rots that way again — so the index polices itself.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

# [text](target) — skip images, and anything with an inline title.
_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")

DOCS = sorted(REPO.glob("docs/**/*.md")) + [REPO / "README.md", REPO / "AGENTS.md"]


def _relative_targets(md: Path) -> list[str]:
    out = []
    for raw in _LINK.findall(md.read_text(encoding="utf-8", errors="replace")):
        target = raw.split("#", 1)[0]
        if not target or "://" in target or target.startswith(("mailto:", "#")):
            continue
        out.append(target)
    return out


@pytest.mark.parametrize("md", DOCS, ids=lambda p: str(p.relative_to(REPO)))
def test_relative_links_resolve(md: Path) -> None:
    missing = [t for t in _relative_targets(md) if not (md.parent / t).resolve().exists()]
    assert not missing, f"{md.relative_to(REPO)} links to non-existent: {missing}"


def test_the_link_checker_actually_catches_a_dead_link(tmp_path: Path) -> None:
    # A guard that cannot fail is decoration. Prove this one bites.
    page = tmp_path / "page.md"
    page.write_text("[gone](./never-written.md)\n")
    assert _relative_targets(page) == ["./never-written.md"]
    assert not (page.parent / "./never-written.md").exists()
