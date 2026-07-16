"""G3 — machines watch what users won't report (Discipline D3).

Repo CI tests source; these checks prove the supply-chain gates that make quality
non-optional: a scheduled smoke-test of the *published* artifact, an enforced
lockfile, a coverage floor, SHA-pinned actions, a version matrix, and Dependabot.
All are read straight out of `.github/`.
"""

from __future__ import annotations

import re

from ..context import Context
from ..model import CheckResult, Status
from . import register

# `uses: owner/repo@REF` — a pin is a 40-hex SHA; anything else (tag/branch) is mutable.
_USES = re.compile(r"uses:\s*([^\s@]+)@([^\s#]+)")
_SHA = re.compile(r"^[0-9a-f]{40}$")


@register(
    id="smoke-published", gate="G3", title="Scheduled smoke-test of the published artifact", weight=2, discipline="D3"
)
def smoke_published(ctx: Context) -> CheckResult:
    check = smoke_published.__invigil__  # type: ignore[attr-defined]
    for p in ctx.workflow_files():
        text = p.read_text(errors="replace")
        looks_smoke = "smoke" in p.name.lower() or "published" in text.lower() or "clean venv" in text.lower()
        if looks_smoke and "schedule:" in text:
            return CheckResult(check, Status.PASS, f"{p.name} runs on a schedule")
    return CheckResult(
        check,
        Status.FAIL,
        "no scheduled published-artifact smoke test",
        "add a scheduled workflow (or `uses: rrskris/invigil/.github/workflows/stranger-gate.yml@v1`) "
        "that installs+boots the published artifact daily",
    )


@register(id="dependabot", gate="G3", title="Dependabot configured", weight=1, discipline="D3")
def dependabot(ctx: Context) -> CheckResult:
    check = dependabot.__invigil__  # type: ignore[attr-defined]
    if ctx.first_existing(".github/dependabot.yml", ".github/dependabot.yaml") or ctx.exists("renovate.json"):
        return CheckResult(check, Status.PASS, "dependabot/renovate present")
    return CheckResult(
        check,
        Status.FAIL,
        "no dependency update bot",
        "add .github/dependabot.yml for your ecosystems (pip/npm/docker/github-actions)",
    )


@register(
    id="actions-sha-pinned",
    gate="G3",
    title="All GitHub Actions are SHA-pinned",
    weight=1,
    mandatory=False,
    discipline="D3",
)
def actions_sha_pinned(ctx: Context) -> CheckResult:
    check = actions_sha_pinned.__invigil__  # type: ignore[attr-defined]
    unpinned: list[str] = []
    for p in ctx.workflow_files():
        for owner_repo, ref in _USES.findall(p.read_text(errors="replace")):
            if owner_repo.startswith((".", "docker://")):  # local/composite or docker refs are fine
                continue
            if not _SHA.match(ref):
                unpinned.append(f"{owner_repo}@{ref}")
    if not unpinned:
        return CheckResult(check, Status.PASS, "all actions pinned to SHAs")
    sample = ", ".join(sorted(set(unpinned))[:3])
    return CheckResult(
        check,
        Status.FAIL,
        f"{len(set(unpinned))} unpinned action(s): {sample}",
        "pin every `uses:` to a 40-char commit SHA (keep the version in a trailing comment)",
    )


@register(id="lockfile-enforced", gate="G3", title="Lockfile enforced in CI", weight=1, discipline="D3")
def lockfile_enforced(ctx: Context) -> CheckResult:
    check = lockfile_enforced.__invigil__  # type: ignore[attr-defined]
    text = ctx.workflows_text()
    if any(tok in text for tok in ("--locked", "--frozen", "npm ci", "--frozen-lockfile", "go mod verify")):
        return CheckResult(check, Status.PASS, "lockfile enforced")
    return CheckResult(
        check,
        Status.FAIL,
        "CI installs without enforcing the lockfile",
        "use `uv sync --locked` / `npm ci` / `--frozen-lockfile` so CI fails on lockfile drift",
    )


@register(id="coverage-gate", gate="G3", title="Coverage floor enforced in CI", weight=1, discipline="D3")
def coverage_gate(ctx: Context) -> CheckResult:
    check = coverage_gate.__invigil__  # type: ignore[attr-defined]
    text = ctx.workflows_text() + ctx.read("pyproject.toml") + ctx.read("setup.cfg")
    if any(tok in text for tok in ("--cov-fail-under", "fail_under", "cov-fail-under", "-covermode")):
        return CheckResult(check, Status.PASS, "coverage floor enforced")
    return CheckResult(
        check,
        Status.FAIL,
        "no coverage floor in CI",
        "add `--cov-fail-under=<N>` (or equivalent) so a coverage drop fails the build",
    )


@register(id="version-matrix", gate="G3", title="CI runs a version matrix", weight=1, mandatory=False, discipline="D3")
def version_matrix(ctx: Context) -> CheckResult:
    check = version_matrix.__invigil__  # type: ignore[attr-defined]
    if "matrix:" in ctx.workflows_text():
        return CheckResult(check, Status.PASS, "matrix build present")
    return CheckResult(
        check,
        Status.FAIL,
        "no build matrix",
        "add a matrix over the runtimes you claim to support (e.g. python 3.11 + 3.12)",
    )
