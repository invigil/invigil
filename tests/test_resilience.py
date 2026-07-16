"""Threat 4 — a network flake must never move the grade, never crash the build."""

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
