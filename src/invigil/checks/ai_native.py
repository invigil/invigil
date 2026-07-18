"""AI-native checks (group `ai`) — Invigil's answer to the architecture shift
toward autonomous agents and micro-context payloads (survival Threat 2).

Legacy linters are blind to `llms.txt` leaking a key or an agent wired to tools
with no declared scope. These are the statically-honest slice of the "agent blast
radius" idea: they don't compute *effective* IAM permissions (that needs
code→credential→policy correlation — out of scope here), they ensure the
preconditions for reasoning about blast radius exist: no secrets in the machine-
readable surface, and a declared tool inventory whenever an agent framework is used.
"""

from __future__ import annotations

import re

from ..context import Context
from ..model import CheckResult, Status
from . import register

# High-signal secret patterns — specific enough not to fire on doc prose.
SECRET_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key id
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"sk-[A-Za-z0-9]{32,}"),  # OpenAI-style secret key
    re.compile(r"ghp_[A-Za-z0-9]{36}"),  # GitHub PAT
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),  # Slack token
)

AI_FILES = ("llms.txt", "llms-full.txt", "AGENTS.md")

# Files agents load as standing instructions before touching a repo.
AGENT_CONTEXT_FILES = ("AGENTS.md", "CLAUDE.md", ".github/copilot-instructions.md", ".cursorrules")

# llms.txt context budget: a machine entry point that doesn't fit alongside the
# task in a context window has failed at its one job.
LLMS_TXT_MAX_BYTES = 10_240

# Agent/LLM-framework import markers — presence means this repo builds agents.
AGENT_MARKERS = (
    "langchain",
    "langgraph",
    "llama_index",
    "llamaindex",
    "import mcp",
    "from mcp",
    "autogen",
    "crewai",
    "semantic_kernel",
)


@register(
    id="llms-no-secrets",
    gate="G5",
    title="Machine-readable surface leaks no secrets",
    weight=1,
    mandatory=False,
    discipline="D5",
)
def llms_no_secrets(ctx: Context) -> CheckResult:
    check = llms_no_secrets.__invigil__  # type: ignore[attr-defined]
    present = [f for f in AI_FILES if ctx.exists(f)]
    if not present:
        return CheckResult(check, Status.SKIP, "no llms.txt / AGENTS.md to scan")
    for f in present:
        text = ctx.read(f)
        for pat in SECRET_PATTERNS:
            if pat.search(text):
                return CheckResult(
                    check,
                    Status.FAIL,
                    f"{f} contains a secret-looking token",
                    f"remove the credential from {f} and rotate it — the AI surface is world-readable and crawled",
                )
    return CheckResult(check, Status.PASS, f"clean: {', '.join(present)}")


@register(
    id="agent-scope-visibility",
    gate="G5",
    title="Agents declare their tool inventory (blast-radius precondition)",
    weight=1,
    mandatory=False,
    discipline="D5",
)
def agent_scope_visibility(ctx: Context) -> CheckResult:
    check = agent_scope_visibility.__invigil__  # type: ignore[attr-defined]
    uses_agents = ctx.source_contains(*AGENT_MARKERS, suffixes=(".py", ".ts", ".js"))
    if not uses_agents:
        return CheckResult(check, Status.SKIP, "no agent framework in use")
    # An AGENTS.md (or a tools manifest) is the declared inventory of what the
    # agent can touch — the thing you'd reason about a blast radius from.
    if ctx.first_existing("AGENTS.md", "agents.yaml", "tools.yaml", "docs/agents.md"):
        return CheckResult(check, Status.PASS, "agent tool inventory declared")
    return CheckResult(
        check,
        Status.FAIL,
        "agent framework used but no declared tool inventory",
        "add AGENTS.md listing each tool the agent can call and its permission scope "
        "(the blast radius if the agent is prompt-injected)",
    )


@register(
    id="agents-md-actionable",
    gate="G5",
    title="Agent context file contains runnable commands",
    weight=1,
    mandatory=False,
    discipline="D5",
    effort="minutes",
)
def agents_md_actionable(ctx: Context) -> CheckResult:
    check = agents_md_actionable.__invigil__  # type: ignore[attr-defined]
    present = [f for f in AGENT_CONTEXT_FILES if ctx.exists(f)]
    if not present:
        return CheckResult(check, Status.SKIP, "no agent-context file (presence is ai-door's call)")
    verbs = ("test", "build", "lint", "install", "run")
    for f in present:
        text = ctx.read(f)
        if "```" in text and any(v in text.lower() for v in verbs):
            return CheckResult(check, Status.PASS, f"{f} has fenced, runnable commands")
    return CheckResult(
        check,
        Status.FAIL,
        f"{', '.join(present)} has no fenced build/test/lint commands",
        f"add the exact build/test/lint commands to {present[0]} in a fenced code block — "
        "an agent executes what you wrote, not what you meant",
    )


@register(
    id="llms-txt-shape",
    gate="G5",
    title="llms.txt follows the spec shape and fits a context budget",
    weight=1,
    mandatory=False,
    discipline="D5",
    effort="minutes",
)
def llms_txt_shape(ctx: Context) -> CheckResult:
    check = llms_txt_shape.__invigil__  # type: ignore[attr-defined]
    if not ctx.exists("llms.txt"):
        return CheckResult(check, Status.SKIP, "no llms.txt (presence is ai-door's call)")
    text = ctx.read("llms.txt")
    problems = []
    h1s = [ln for ln in text.splitlines() if ln.startswith("# ")]
    if len(h1s) != 1:
        problems.append(f"{len(h1s)} H1 titles (want exactly one)")
    if not any(ln.startswith("> ") for ln in text.splitlines()):
        problems.append("no `> summary` blockquote")
    if not (re.search(r"\[[^\]]+\]\([^)]+\)", text) or "```" in text):
        problems.append("no links or fenced quickstart")
    size = len(text.encode("utf-8"))
    if size > LLMS_TXT_MAX_BYTES:
        problems.append(f"{size} bytes (budget {LLMS_TXT_MAX_BYTES})")
    if problems:
        return CheckResult(
            check,
            Status.FAIL,
            "llms.txt off-spec: " + "; ".join(problems),
            "shape llms.txt to the spec: one `# Title`, a `> summary` blockquote, "
            f"linked sections or a fenced quickstart, and keep it under {LLMS_TXT_MAX_BYTES // 1024} KB",
        )
    return CheckResult(check, Status.PASS, f"spec-shaped, {size} bytes")


@register(
    id="agent-context-fresh",
    gate="G5",
    title="Agent context not stale against the source tree",
    weight=1,
    mandatory=False,
    discipline="D5",
    effort="minutes",
)
def agent_context_fresh(ctx: Context) -> CheckResult:
    check = agent_context_fresh.__invigil__  # type: ignore[attr-defined]
    present = [f for f in AGENT_CONTEXT_FILES if ctx.exists(f)]
    if not present:
        return CheckResult(check, Status.SKIP, "no agent-context file")
    code_a, out_a = ctx.git("log", "-1", "--format=%ct", "--", *present)
    if code_a != 0 or not out_a.strip():
        return CheckResult(check, Status.SKIP, "no git history for the agent-context files")
    src_specs = [d for d in ("src", "lib", "app", "cmd", "pkg") if ctx.exists(d)] or ["."]
    code_s, out_s = ctx.git("log", "-1", "--format=%ct", "--", *src_specs)
    if code_s != 0 or not out_s.strip():
        return CheckResult(check, Status.SKIP, "no git history for the source tree")
    try:
        drift_days = (int(out_s.split()[0]) - int(out_a.split()[0])) / 86_400
    except (ValueError, IndexError):
        return CheckResult(check, Status.SKIP, "could not parse git timestamps")
    if drift_days > 90:
        return CheckResult(
            check,
            Status.FAIL,
            f"agent context last touched {int(drift_days)} days before the newest source change",
            f"re-read {present[0]} against the current build/test commands and commit the refresh — "
            "agents follow stale instructions verbatim",
        )
    return CheckResult(check, Status.PASS, f"fresh (drift {max(int(drift_days), 0)}d)")


@register(
    id="readme-heading-hierarchy",
    gate="G5",
    title="README heading hierarchy is machine-chunkable",
    weight=1,
    mandatory=False,
    discipline="D5",
    effort="minutes",
)
def readme_heading_hierarchy(ctx: Context) -> CheckResult:
    check = readme_heading_hierarchy.__invigil__  # type: ignore[attr-defined]
    if not ctx.exists("README.md"):
        return CheckResult(check, Status.SKIP, "no README.md (presence is readme-present's call)")
    h1 = h2 = 0
    in_fence = False
    for ln in ctx.read("README.md").splitlines():
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if ln.startswith("# "):
            h1 += 1
        elif ln.startswith("## "):
            h2 += 1
    if h1 == 1 and h2 >= 2:
        return CheckResult(check, Status.PASS, f"1 H1, {h2} H2 sections")
    return CheckResult(
        check,
        Status.FAIL,
        f"{h1} H1 titles, {h2} H2 sections (want exactly 1 and >=2)",
        "restructure README.md: exactly one `#` title and `##` sections for install/quickstart/usage — "
        "agents chunk documents by heading",
    )


@register(
    id="exit-codes-documented",
    gate="G5",
    title="CLI exit codes are documented",
    weight=1,
    mandatory=False,
    discipline="D5",
    effort="minutes",
)
def exit_codes_documented(ctx: Context) -> CheckResult:
    check = exit_codes_documented.__invigil__  # type: ignore[attr-defined]
    is_cli = "[project.scripts]" in ctx.read("pyproject.toml") or '"bin"' in ctx.read("package.json")
    if not is_cli:
        return CheckResult(check, Status.SKIP, "not a CLI (no declared entry points)")
    docs = ctx.read("README.md") + "".join(p.read_text(errors="replace") for p in ctx.glob("docs/*.md"))
    if "exit code" in docs.lower() or "exit status" in docs.lower() or ctx.exists("docs/errors.md"):
        return CheckResult(check, Status.PASS, "exit codes documented")
    return CheckResult(
        check,
        Status.FAIL,
        "no exit-code documentation found in README or docs/",
        "document the CLI's exit codes (e.g. a table in docs/cli-reference.md: 0 ok, 1 below gate, "
        "2 usage error, 3 refused) — agents branch on exit codes, not prose",
    )
