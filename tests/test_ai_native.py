"""AI-native group (M5): secret-free machine surface + agent tool-inventory."""

from pathlib import Path

from invigil.checks import ai_native as ai
from invigil.config import InvigilConfig
from invigil.context import Context
from invigil.model import Status


def ctx(tmp_path: Path) -> Context:
    return Context(repo=tmp_path, config=InvigilConfig.load(tmp_path))


def test_llms_no_secrets_skips_without_files(tmp_path):
    assert ai.llms_no_secrets(ctx(tmp_path)).status is Status.SKIP


def test_llms_no_secrets_pass(tmp_path):
    (tmp_path / "llms.txt").write_text("# App\n\nA clean machine-readable summary.\n")
    assert ai.llms_no_secrets(ctx(tmp_path)).status is Status.PASS


def test_llms_no_secrets_flags_planted_key(tmp_path):
    (tmp_path / "llms.txt").write_text("api key: AKIA1234567890ABCD99\n")
    r = ai.llms_no_secrets(ctx(tmp_path))
    assert r.status is Status.FAIL and "rotate" in r.fix


def test_agent_scope_skips_when_no_framework(tmp_path):
    (tmp_path / "main.py").write_text("print('plain app')\n")
    assert ai.agent_scope_visibility(ctx(tmp_path)).status is Status.SKIP


def test_agent_scope_fails_without_inventory(tmp_path):
    (tmp_path / "agent.py").write_text("from langchain.agents import initialize_agent\n")
    r = ai.agent_scope_visibility(ctx(tmp_path))
    assert r.status is Status.FAIL and "AGENTS.md" in r.fix


def test_agent_scope_passes_with_inventory(tmp_path):
    (tmp_path / "agent.py").write_text("import langgraph\n")
    (tmp_path / "AGENTS.md").write_text("# Tools\n- search: read-only\n")
    assert ai.agent_scope_visibility(ctx(tmp_path)).status is Status.PASS


# --- agents-md-actionable ---------------------------------------------------
def test_agents_md_actionable_skips_without_context_file(tmp_path):
    assert ai.agents_md_actionable(ctx(tmp_path)).status is Status.SKIP


def test_agents_md_actionable_fails_on_prose_only(tmp_path):
    (tmp_path / "AGENTS.md").write_text("# Agents\n\nBe careful and thoughtful.\n")
    r = ai.agents_md_actionable(ctx(tmp_path))
    assert r.status is Status.FAIL and "fenced" in r.fix


def test_agents_md_actionable_passes_with_commands(tmp_path):
    (tmp_path / "AGENTS.md").write_text("# Agents\n\n```bash\npytest -q  # test\n```\n")
    assert ai.agents_md_actionable(ctx(tmp_path)).status is Status.PASS


# --- llms-txt-shape ---------------------------------------------------------
def test_llms_txt_shape_skips_when_absent(tmp_path):
    assert ai.llms_txt_shape(ctx(tmp_path)).status is Status.SKIP


def test_llms_txt_shape_passes_spec_file(tmp_path):
    (tmp_path / "llms.txt").write_text("# App\n\n> One-line summary.\n\n- [README](README.md)\n")
    assert ai.llms_txt_shape(ctx(tmp_path)).status is Status.PASS


def test_llms_txt_shape_fails_shapeless_file(tmp_path):
    (tmp_path / "llms.txt").write_text("just a wall of prose with no structure\n")
    r = ai.llms_txt_shape(ctx(tmp_path))
    assert r.status is Status.FAIL and "blockquote" in r.detail


def test_llms_txt_shape_fails_oversized_file(tmp_path):
    (tmp_path / "llms.txt").write_text("# App\n\n> Summary.\n\n[a](b)\n" + "x" * 11_000)
    r = ai.llms_txt_shape(ctx(tmp_path))
    assert r.status is Status.FAIL and "budget" in r.detail


# --- agent-context-fresh ----------------------------------------------------
def _git(tmp_path, *args, env=None):
    import subprocess

    subprocess.run(["git", *args], cwd=tmp_path, capture_output=True, check=False, env=env)


def _committed_repo(tmp_path, agents_age_days: int, src_age_days: int):
    import os
    import time

    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "t@t.t")
    _git(tmp_path, "config", "user.name", "t")
    now = int(time.time())

    def commit_at(days_ago, *paths):
        stamp = str(now - days_ago * 86_400)
        env = {**os.environ, "GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp}
        _git(tmp_path, "add", *paths)
        _git(tmp_path, "commit", "-m", "c", "--no-verify", env=env)

    (tmp_path / "AGENTS.md").write_text("# Agents\n")
    commit_at(agents_age_days, "AGENTS.md")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("x = 1\n")
    commit_at(src_age_days, "src")


def test_agent_context_fresh_skips_without_context_file(tmp_path):
    assert ai.agent_context_fresh(ctx(tmp_path)).status is Status.SKIP


def test_agent_context_fresh_skips_without_git_history(tmp_path):
    (tmp_path / "AGENTS.md").write_text("# Agents\n")
    assert ai.agent_context_fresh(ctx(tmp_path)).status is Status.SKIP


def test_agent_context_fresh_passes_small_drift(tmp_path):
    _committed_repo(tmp_path, agents_age_days=10, src_age_days=5)
    assert ai.agent_context_fresh(ctx(tmp_path)).status is Status.PASS


def test_agent_context_fresh_fails_stale_context(tmp_path):
    _committed_repo(tmp_path, agents_age_days=200, src_age_days=1)
    r = ai.agent_context_fresh(ctx(tmp_path))
    assert r.status is Status.FAIL and "stale" in r.fix.lower() or "verbatim" in r.fix


# --- readme-heading-hierarchy -----------------------------------------------
def test_readme_hierarchy_skips_without_readme(tmp_path):
    assert ai.readme_heading_hierarchy(ctx(tmp_path)).status is Status.SKIP


def test_readme_hierarchy_passes_clean_structure(tmp_path):
    (tmp_path / "README.md").write_text("# App\n\n## Install\n\n## Usage\n\n```sh\n# not a heading\n```\n")
    assert ai.readme_heading_hierarchy(ctx(tmp_path)).status is Status.PASS


def test_readme_hierarchy_fails_multiple_h1(tmp_path):
    (tmp_path / "README.md").write_text("# One\n# Two\n\n## A\n\n## B\n")
    r = ai.readme_heading_hierarchy(ctx(tmp_path))
    assert r.status is Status.FAIL and "2 H1" in r.detail


def test_readme_hierarchy_ignores_hashes_inside_fences(tmp_path):
    (tmp_path / "README.md").write_text("# App\n\n```yaml\n# comment\n# comment\n```\n\n## A\n\n## B\n")
    assert ai.readme_heading_hierarchy(ctx(tmp_path)).status is Status.PASS


# --- exit-codes-documented --------------------------------------------------
def test_exit_codes_skips_non_cli(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "lib"\n')
    assert ai.exit_codes_documented(ctx(tmp_path)).status is Status.SKIP


def test_exit_codes_fails_undocumented_cli(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project.scripts]\nx = "x:main"\n')
    (tmp_path / "README.md").write_text("# X\n\nA CLI.\n")
    r = ai.exit_codes_documented(ctx(tmp_path))
    assert r.status is Status.FAIL and "exit codes" in r.fix


def test_exit_codes_passes_documented_cli(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project.scripts]\nx = "x:main"\n')
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "cli-reference.md").write_text("## Exit codes\n\n0 ok, 1 below gate\n")
    assert ai.exit_codes_documented(ctx(tmp_path)).status is Status.PASS
