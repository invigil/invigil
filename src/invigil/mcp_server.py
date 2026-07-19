"""`invigil mcp` — the scorecard as an MCP tool surface (stdio).

Runs on the official `mcp` SDK, installed via the optional `[mcp]` extra so
the core CLI stays zero-dep beyond PyYAML. The server is read-only by design:
`preview_fixes` returns the mutation plan without touching files — agents
apply changes with their own edit tools or the fix-PR workflow.
"""

from __future__ import annotations

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .checks import GROUPS
from .cli import score
from .report import as_json, as_llm

server = FastMCP(
    "invigil",
    instructions=(
        "Grades a repository against a product-quality doctrine (G1-G7 gates, "
        "A-F grade, AI-legibility sub-score). Call evaluate_repo first; each "
        "FAIL line carries its own fix instruction."
    ),
)


def _resolve(path: str) -> Path:
    repo = Path(path).resolve()
    if not repo.exists():
        raise ValueError(f"path not found: {repo}")
    return repo


@server.tool()
def evaluate_repo(path: str, format: str = "llm", offline: bool = True) -> str:
    """Score a repo against the quality doctrine. `format` is "llm" (one line
    per finding, each with a fix) or "json" (full scorecard)."""
    if format not in ("llm", "json"):
        raise ValueError(f'unknown format {format!r} — use "llm" or "json"')
    repo = _resolve(path)
    sc, _ = score(repo, offline=offline)
    return as_json(sc) if format == "json" else as_llm(sc)


@server.tool()
def check_group(path: str, group: str) -> str:
    """Run one check group offline (fast). Groups: ai, doors, errors,
    evidence, layout, secrets, supply-chain."""
    if group not in GROUPS:
        raise ValueError(f"unknown group {group!r} — one of: {', '.join(GROUPS)}")
    repo = _resolve(path)
    sc, _ = score(repo, only_groups={group}, offline=True)
    return as_llm(sc)


@server.tool()
def preview_fixes(path: str) -> str:
    """List the file mutations `invigil --fix` would apply, without writing
    anything. Apply them with your own edit tools, then re-run evaluate_repo."""
    from .context import Context
    from .fixer import apply_fixes

    repo = _resolve(path)
    sc, config = score(repo, offline=True)
    ctx = Context(repo=repo, config=config)
    rep = apply_fixes(ctx, sc.results, dry_run=True)
    return json.dumps(
        {
            "fixable_checks": sorted(rep.fixed + rep.unresolved),
            "no_fix_available": sorted(rep.no_fix),
            "would_change_files": rep.changed_files,
            "mutations": rep.log,
        },
        indent=2,
    )


def serve() -> None:
    """Run the server over stdio (blocks until the client disconnects)."""
    server.run()
