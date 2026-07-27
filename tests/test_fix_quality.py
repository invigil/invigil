"""Invariants on the *advice* Invigil gives, not on what it detects.

A gate that can't tell you how to pass it is the anti-pattern Invigil exists to
catch, so the fix text is product surface, not a comment. A wrong recommendation
costs more trust than a missed check — PR #23 found `smoke-published` recommending
an unpinned `stranger-gate.yml@v1`, i.e. our own advice breaking our own
`actions-sha-pinned` check. These tests make that class of regression impossible.
"""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

import pytest

import invigil.checks as checks_pkg
from invigil.checks import (  # noqa: F401  (imported for registry side effects)
    ai_native,
    g1_stranger,
    g2_errors,
    g3_supply,
    g4_evidence,
    g5_doors,
    tier1_secrets,
)
from invigil.config import InvigilConfig
from invigil.context import Context
from invigil.model import Status

CHECKS_DIR = Path(checks_pkg.__file__).parent

# `uses: owner/repo@ref` as it appears inside fix strings and docstrings.
_USES = re.compile(r"uses:\s*([\w.-]+/[\w./-]+)@([^\s`\"']+)")
_SHA40 = re.compile(r"^[0-9a-f]{40}$")


def _empty_git_repo(tmp_path: Path) -> Context:
    for args in (("init",), ("config", "user.email", "t@t.t"), ("config", "user.name", "t")):
        subprocess.run(["git", *args], cwd=tmp_path, capture_output=True, check=False)
    return Context(repo=tmp_path, config=InvigilConfig.load(tmp_path))


@pytest.mark.parametrize("check,fn", checks_pkg.REGISTRY, ids=[c.id for c, _ in checks_pkg.REGISTRY])
def test_every_failure_carries_a_fix(tmp_path, check, fn):
    """D2, applied to Invigil itself: no failing check may leave you stuck."""
    result = fn(_empty_git_repo(tmp_path))
    if result.status is Status.FAIL:
        assert result.fix and result.fix.strip(), f"{check.id} failed without telling anyone how to fix it"


@pytest.mark.parametrize("check,fn", checks_pkg.REGISTRY, ids=[c.id for c, _ in checks_pkg.REGISTRY])
def test_a_failure_says_what_is_wrong(tmp_path, check, fn):
    result = fn(_empty_git_repo(tmp_path))
    if result.status is Status.FAIL:
        assert result.detail and result.detail.strip(), f"{check.id} failed with no detail"


def test_no_check_recommends_an_unpinned_action():
    """Any workflow snippet Invigil hands out must satisfy `actions-sha-pinned`.

    A placeholder like `@<sha>` is fine — it is visibly a blank to fill in. A
    floating `@v1` is not: it is copy-pasteable and wrong.
    """
    offenders: list[str] = []
    for path in sorted(CHECKS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(errors="replace"))
        # Only string literals — a `#` comment describing a regex is not advice.
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                continue
            for owner_repo, ref in _USES.findall(node.value):
                if ref.startswith("<") or _SHA40.match(ref):
                    continue
                offenders.append(f"{path.name}:{node.lineno}: uses: {owner_repo}@{ref}")
    assert not offenders, "fix text recommends unpinned actions:\n  " + "\n  ".join(offenders)


def test_every_exit_code_the_cli_returns_is_documented():
    """Agents branch on exit codes, not prose — so the table has to be true.

    `exit-codes-documented` only checks that *some* exit-code docs exist. This
    checks they match the code, which is the difference between a claim and
    evidence.
    """
    import invigil.cli as cli_mod

    src = Path(cli_mod.__file__).read_text(errors="replace")
    returned = {
        node.value.value
        for node in ast.walk(ast.parse(src))
        if isinstance(node, ast.Return)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, int)
        and not isinstance(node.value.value, bool)
    }
    doc = Path(__file__).resolve().parents[1] / "docs" / "cli-reference.md"
    documented = {int(m) for m in re.findall(r"^\|\s*`(\d+)`\s*\|", doc.read_text(), re.MULTILINE)}
    assert returned <= documented, (
        f"cli.py can return {sorted(returned - documented)}, which docs/cli-reference.md does not document"
    )
