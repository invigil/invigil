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
