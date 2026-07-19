"""End-to-end test of `invigil mcp`: spawn the real server over stdio, speak
the MCP protocol to it, and read a scorecard back. Skipped when the optional
`[mcp]` extra is not installed (the CLI-error path for that case is tested
unconditionally below)."""

from __future__ import annotations

import subprocess
import sys

import pytest

mcp = pytest.importorskip("mcp", reason="optional [mcp] extra not installed")

import anyio  # noqa: E402  (dependency of mcp, only needed when it's present)
from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402

EXPECTED_TOOLS = {"evaluate_repo", "check_group", "preview_fixes"}


def _fixture_repo(tmp_path):
    (tmp_path / "README.md").write_text("# demo\n\n## Quick Start\n\n```sh\npip install demo\n```\n")
    return tmp_path


def _stdio_session_roundtrip(repo) -> tuple[set[str], str, str]:
    """Spawn the server, list tools, call evaluate_repo + preview_fixes."""
    params = StdioServerParameters(command=sys.executable, args=["-m", "invigil.cli", "mcp"])

    async def go():
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = {t.name for t in (await session.list_tools()).tools}
                ev = await session.call_tool("evaluate_repo", {"path": str(repo)})
                pf = await session.call_tool("preview_fixes", {"path": str(repo)})
                return tools, ev.content[0].text, pf.content[0].text

    return anyio.run(go)


def test_stdio_server_lists_tools_and_scores_a_repo(tmp_path):
    repo = _fixture_repo(tmp_path)
    tools, report, preview = _stdio_session_roundtrip(repo)
    assert tools == EXPECTED_TOOLS
    assert report.startswith(f"invigil repo={repo.name} gate=")
    assert '"mutations"' in preview  # dry-run plan, JSON shape


def test_evaluate_repo_rejects_bad_format(tmp_path):
    from invigil.mcp_server import evaluate_repo

    with pytest.raises(ValueError, match="unknown format"):
        evaluate_repo(str(_fixture_repo(tmp_path)), format="yaml")


def test_check_group_rejects_unknown_group(tmp_path):
    from invigil.mcp_server import check_group

    with pytest.raises(ValueError, match="unknown group"):
        check_group(str(_fixture_repo(tmp_path)), group="nope")


def test_missing_path_is_an_error():
    from invigil.mcp_server import evaluate_repo

    with pytest.raises(ValueError, match="path not found"):
        evaluate_repo("/does/not/exist")


def test_mcp_subcommand_without_extra_prints_install_fix():
    """Simulate a core-only install: hide the `mcp` package from the child
    process and assert the G2-style actionable error + exit 3."""
    code = (
        "import sys; sys.modules['mcp'] = None\n"  # import raises ModuleNotFoundError('mcp')
        "from invigil.cli import main\n"
        "sys.exit(main(['mcp']))\n"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert proc.returncode == 3
    assert 'pip install "invigil[mcp]"' in proc.stderr
