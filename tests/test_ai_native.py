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
