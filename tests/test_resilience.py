"""Threat 4 — a network flake must never move the grade, never crash the build."""

import json
import urllib.error

from invigil.checks import g4_evidence as g4
from invigil.config import InvigilConfig
from invigil.context import Context
from invigil.model import Status


def _ctx_with_remote(tmp_path, monkeypatch):
    ctx = Context(repo=tmp_path, config=InvigilConfig.load(tmp_path))
    monkeypatch.setattr(type(ctx), "repo_slug", lambda self: "owner/repo")
    return ctx


def test_scorecard_timeout_is_skip_not_fail(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise urllib.error.URLError("timed out")

    monkeypatch.setattr(g4.urllib.request, "urlopen", boom)
    r = g4.scorecard_score(_ctx_with_remote(tmp_path, monkeypatch))
    # SKIP (excluded from the grade denominator), never FAIL, never an exception.
    assert r.status is Status.SKIP
    assert "excluded from grade" in r.detail


def test_scorecard_success_still_evaluates(tmp_path, monkeypatch):
    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"score": 8.1}'

    monkeypatch.setattr(g4.urllib.request, "urlopen", lambda *a, **k: Resp())
    r = g4.scorecard_score(_ctx_with_remote(tmp_path, monkeypatch))
    assert r.status is Status.PASS and "8.1" in r.detail


# Modelled on the real api.scorecard.dev response for invicton/bakex on 2026-08-05,
# before its Token-Permissions findings were fixed -- the case this remediation exists for.
_BAKEX_BEFORE = {
    "score": 6.0,
    "checks": [
        {"name": "Branch-Protection", "score": -1, "reason": "internal error", "details": []},
        {
            "name": "Token-Permissions",
            "score": 0,
            "reason": "detected GitHub workflow tokens with excessive permissions",
            "details": [
                "Info: jobLevel 'contents' permission set to 'read': .github/workflows/ci.yml:170",
                "Warn: no topLevel permission defined: .github/workflows/ci.yml:1",
                "Warn: topLevel 'contents' permission set to 'write': .github/workflows/refresh-amis.yml:9",
            ],
        },
        {
            "name": "Pinned-Dependencies",
            "score": 6,
            "reason": "dependency not pinned by hash detected",
            "details": [
                "Warn: containerImage not pinned by hash: Dockerfile:1: pin by updating"
                " python:3.14-slim to python:3.14-slim@sha256:7bec",
                "Warn: GitHub-owned GitHubAction not pinned by hash:"
                " .github/workflows/test-action.yml:30: update using https://app.stepsecurity.io/secure",
            ],
        },
        {"name": "CI-Tests", "score": 10, "reason": "all checked", "details": []},
    ],
}


def test_scorecard_fix_names_checks_files_and_the_pattern():
    """The whole point: Scorecard says *what*, the fix says *where* and *how*."""
    fix = g4._scorecard_fix(_BAKEX_BEFORE)
    assert "Token-Permissions" in fix  # worst actionable check, named
    assert ".github/workflows/ci.yml:1" in fix  # the file, which Scorecard buries
    assert "permissions: contents: read" in fix  # the pattern, which Scorecard never gives
    assert "triage the Scorecard findings" not in fix  # the old non-answer is gone


def test_scorecard_fix_is_a_single_line():
    """`fix` renders inside a markdown table cell (report.py) -- a newline breaks the table."""
    assert "\n" not in g4._scorecard_fix(_BAKEX_BEFORE)


def test_scorecard_fix_excludes_internal_errors_and_passing_checks():
    """score -1 is Scorecard failing to look, not the repo failing -- never report it as a finding."""
    fix = g4._scorecard_fix(_BAKEX_BEFORE)
    assert "Branch-Protection" not in fix  # score -1
    assert "CI-Tests" not in fix  # score 10


def test_scorecard_fix_ignores_info_details_and_urls():
    """Info: lines describe what is already correct; URLs and image tags are not locations."""
    fix = g4._scorecard_fix(_BAKEX_BEFORE)
    assert "ci.yml:170" not in fix  # an Info: line -- that job is already correct
    assert "http" not in fix  # the stepsecurity remediation URL
    assert "python:3" not in fix  # image tag, not a file:line


def test_scorecard_fix_falls_back_when_findings_are_absent():
    """Older/leaner payloads carry only a score -- degrade, never raise."""
    assert g4._scorecard_fix({"score": 4.0}) == g4._FIX_GENERIC
    assert g4._scorecard_fix({"score": 4.0, "checks": []}) == g4._FIX_GENERIC


def test_scorecard_below_bar_fails_with_the_real_fix(tmp_path, monkeypatch):
    """End to end through the check, not just the helper."""

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps(_BAKEX_BEFORE).encode()

    monkeypatch.setattr(g4.urllib.request, "urlopen", lambda *a, **k: Resp())
    r = g4.scorecard_score(_ctx_with_remote(tmp_path, monkeypatch))
    assert r.status is Status.FAIL
    assert "Token-Permissions" in r.fix and ".github/workflows/ci.yml:1" in r.fix


def test_grade_is_invariant_to_network_failure(tmp_path, monkeypatch):
    """A repo's grade with a failing network is byte-identical to its offline grade."""
    from invigil import cli

    (tmp_path / "LICENSE").write_text("Apache License\nVersion 2.0\n")
    (tmp_path / "README.md").write_text("# App\n\n## Quick Start\n\n`pip install app`\n")

    def boom(*a, **k):
        raise urllib.error.URLError("down")

    monkeypatch.setattr(g4.urllib.request, "urlopen", boom)
    online_fail, _ = cli.score(tmp_path)  # network attempted, fails -> SKIP
    offline, _ = cli.score(tmp_path, offline=True)  # network never attempted -> SKIP
    assert online_fail.grade() == offline.grade()
    assert online_fail.gate_level() == offline.gate_level()
