"""The `invigil fix` engine: safe mutations, the single-pass loop, CI-lockout, CLI."""

import subprocess
from pathlib import Path

import pytest

from invigil import cli
from invigil.checks import FIXES
from invigil.fixer import apply_fixes, ci_active
from invigil.mutator import Mutation, MutationError, Mutator


@pytest.fixture(autouse=True)
def _no_ci_env(monkeypatch):
    # CI runners set CI=true, which trips the --fix CI-lockout; tests that
    # want the lockout set CI themselves.
    monkeypatch.delenv("CI", raising=False)


# --- mutator --------------------------------------------------------------
def test_create_file_idempotent(tmp_path):
    m = Mutator(tmp_path)
    assert m.apply(Mutation("create_file", "docs/x.md", content="hi")) is True
    assert (tmp_path / "docs/x.md").read_text() == "hi"
    assert m.apply(Mutation("create_file", "docs/x.md", content="other")) is False  # exists
    assert m.changed == ["docs/x.md"]


def test_append_file_idempotent(tmp_path):
    (tmp_path / "f.txt").write_text("a\n")
    m = Mutator(tmp_path)
    assert m.apply(Mutation("append_file", "f.txt", content="b\n")) is True
    assert (tmp_path / "f.txt").read_text() == "a\nb\n"
    assert m.apply(Mutation("append_file", "f.txt", content="b\n")) is False  # already there


def test_replace_string(tmp_path):
    (tmp_path / "f.txt").write_text("hello localhost world")
    m = Mutator(tmp_path)
    assert m.apply(Mutation("replace_string", "f.txt", find="localhost", replace="0.0.0.0")) is True
    assert "0.0.0.0" in (tmp_path / "f.txt").read_text()
    assert m.apply(Mutation("replace_string", "f.txt", find="nope", replace="x")) is False


def test_delete_file(tmp_path):
    (tmp_path / "f.txt").write_text("x")
    m = Mutator(tmp_path)
    assert m.apply(Mutation("delete_file", "f.txt")) is True
    assert not (tmp_path / "f.txt").exists()
    assert m.apply(Mutation("delete_file", "f.txt")) is False


def test_path_jail_blocks_escape(tmp_path):
    m = Mutator(tmp_path)
    for bad in ("../evil.txt", "../../etc/passwd", "/etc/passwd"):
        with pytest.raises(MutationError):
            m.apply(Mutation("create_file", bad, content="x"))


def test_unknown_action(tmp_path):
    with pytest.raises(MutationError):
        Mutator(tmp_path).apply(Mutation("chmod", "f"))


def test_dry_run_writes_nothing(tmp_path):
    m = Mutator(tmp_path, dry_run=True)
    assert m.apply(Mutation("create_file", "x.md", content="hi")) is True
    assert not (tmp_path / "x.md").exists()  # recorded but not written
    assert m.changed == ["x.md"]


# --- ci-lockout -----------------------------------------------------------
def test_ci_active():
    assert ci_active({"CI": "true"}) is True
    assert ci_active({"CI": "1"}) is True
    assert ci_active({"CI": ""}) is False
    assert ci_active({}) is False


# --- fix loop -------------------------------------------------------------
def _evidence_repo(tmp_path):
    # a bare repo: fails evidence checks (no SECURITY.md / CHANGELOG.md / scorecard)
    (tmp_path / "LICENSE").write_text("Apache License\nVersion 2.0\n")
    (tmp_path / "README.md").write_text("# X\n## Quick Start\n`pip install x`\n")
    return tmp_path


def test_apply_fixes_creates_and_single_pass(tmp_path):
    _evidence_repo(tmp_path)
    sc, _ = cli.score(tmp_path, only_groups={"evidence"}, offline=True)
    rep = apply_fixes(_ctx(tmp_path), sc.results)
    # security-policy + changelog have fixes and now pass; scorecard/sbom have none
    assert "security-policy" in rep.fixed
    assert "changelog" in rep.fixed
    assert (tmp_path / "SECURITY.md").exists()
    assert (tmp_path / "CHANGELOG.md").exists()
    assert "signed-releases-sbom" in rep.no_fix


def test_single_pass_unresolved(tmp_path, monkeypatch):
    _evidence_repo(tmp_path)
    # a fix that does nothing -> the re-check still fails -> unresolved (no infinite loop)
    monkeypatch.setitem(FIXES, "scorecard-workflow", lambda ctx: [])
    sc, _ = cli.score(tmp_path, only_groups={"evidence"}, offline=True)
    rep = apply_fixes(_ctx(tmp_path), sc.results)
    assert "scorecard-workflow" in rep.unresolved


def _ctx(path):
    from invigil.config import InvigilConfig
    from invigil.context import Context

    return Context(repo=Path(path), config=InvigilConfig.load(Path(path)))


# --- CLI ------------------------------------------------------------------
def _git(tmp_path, *args):
    subprocess.run(["git", *args], cwd=tmp_path, capture_output=True, check=False)


def test_cli_check_fix_creates_and_stages(tmp_path):
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "t@t.t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "app.py").write_text("import os\n")  # config surface, no docs
    rc = cli.main(["check", "doors", str(tmp_path), "--fix"])
    # doors: contributor-door + code-of-conduct + docs-index get fixed; operator-door
    # has no fix and still fails -> exit 1. (ai-door lives in the `ai` group.)
    assert rc == 1
    assert (tmp_path / "CONTRIBUTING.md").exists()
    assert (tmp_path / "CODE_OF_CONDUCT.md").exists()
    assert (tmp_path / "docs" / "README.md").exists()


def test_cli_check_ai_fix_creates_agents_md(tmp_path):
    _git(tmp_path, "init")
    # No llms.txt / AGENTS.md -> ai-door fails; its fix creates AGENTS.md.
    (tmp_path / "agent.py").write_text("import langchain\n")
    cli.main(["check", "ai", str(tmp_path), "--fix"])
    assert (tmp_path / "AGENTS.md").exists()


def test_cli_fix_ci_lockout(tmp_path, monkeypatch):
    monkeypatch.setenv("CI", "true")
    (tmp_path / "app.py").write_text("x = 1\n")
    assert cli.main(["check", "doors", str(tmp_path), "--fix"]) == 3
