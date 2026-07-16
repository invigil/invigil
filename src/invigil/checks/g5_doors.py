"""G5 — all five doors open and documented (Discipline D5).

One product, five first-class entrances: newbie (quickstart — covered in G1),
seasoned operator (API/CLI reference), OSS contributor (CONTRIBUTING + a menu of
good-first-issues), enterprise (SECURITY — covered in G4), and the emerging AI
door (machine-readable llms.txt / AGENTS.md). Docs are the map contributors need
before the code.
"""

from __future__ import annotations

from ..context import Context
from ..model import CheckResult, Status
from . import register


@register(id="docs-index", gate="G5", title="docs/ has an index", weight=1, mandatory=False, discipline="D5")
def docs_index(ctx: Context) -> CheckResult:
    check = docs_index.__invigil__  # type: ignore[attr-defined]
    if ctx.first_existing("docs/README.md", "docs/index.md", "mkdocs.yml", "docs/SUMMARY.md"):
        return CheckResult(check, Status.PASS, "docs index present")
    return CheckResult(
        check,
        Status.FAIL,
        "no docs index",
        "add docs/README.md linking every deep doc (README is the lobby, not the building)",
    )


@register(id="contributor-door", gate="G5", title="CONTRIBUTING.md present", weight=1, discipline="D5")
def contributor_door(ctx: Context) -> CheckResult:
    check = contributor_door.__invigil__  # type: ignore[attr-defined]
    if ctx.first_existing("CONTRIBUTING.md", ".github/CONTRIBUTING.md", "docs/CONTRIBUTING.md"):
        return CheckResult(check, Status.PASS, "CONTRIBUTING.md present")
    return CheckResult(
        check,
        Status.FAIL,
        "no CONTRIBUTING.md",
        "add CONTRIBUTING.md: dev setup, how to run tests, PR expectations, DCO",
    )


@register(
    id="code-of-conduct", gate="G5", title="CODE_OF_CONDUCT.md present", weight=1, mandatory=False, discipline="D5"
)
def code_of_conduct(ctx: Context) -> CheckResult:
    check = code_of_conduct.__invigil__  # type: ignore[attr-defined]
    if ctx.first_existing("CODE_OF_CONDUCT.md", ".github/CODE_OF_CONDUCT.md"):
        return CheckResult(check, Status.PASS, "present")
    return CheckResult(check, Status.FAIL, "no CODE_OF_CONDUCT.md", "add the Contributor Covenant with a real contact")


@register(
    id="operator-door", gate="G5", title="API/CLI reference for operators", weight=1, mandatory=False, discipline="D5"
)
def operator_door(ctx: Context) -> CheckResult:
    check = operator_door.__invigil__  # type: ignore[attr-defined]
    has = ctx.first_existing("docs/api.md", "docs/configuration.md", "openapi.json", "openapi.yaml") or bool(
        ctx.rglob("**/openapi*.json") or ctx.rglob("**/openapi*.yaml")
    )
    if has:
        return CheckResult(check, Status.PASS, "API/CLI reference present")
    return CheckResult(
        check,
        Status.FAIL,
        "no operator reference",
        "publish an API/CLI reference (or OpenAPI spec) — every UI action should have a curl",
    )


@register(id="ai-door", gate="G5", title="AI door: llms.txt / AGENTS.md", weight=1, mandatory=False, discipline="D5")
def ai_door(ctx: Context) -> CheckResult:
    check = ai_door.__invigil__  # type: ignore[attr-defined]
    if ctx.first_existing("llms.txt", "llms-full.txt", "AGENTS.md"):
        return CheckResult(check, Status.PASS, "machine-readable entry present")
    return CheckResult(
        check,
        Status.FAIL,
        "no llms.txt / AGENTS.md",
        "add llms.txt (pitch + quickstart + API) and AGENTS.md (build/test/lint conventions)",
    )


@register(
    id="good-first-issues", gate="G5", title=">=5 open good-first-issues", weight=1, mandatory=False, discipline="D5"
)
def good_first_issues(ctx: Context) -> CheckResult:
    check = good_first_issues.__invigil__  # type: ignore[attr-defined]
    slug = ctx.repo_slug()
    if not slug:
        return CheckResult(check, Status.SKIP, "no github remote")
    code, out = ctx.gh(
        "issue",
        "list",
        "--repo",
        slug,
        "--label",
        "good first issue",
        "--state",
        "open",
        "--json",
        "number",
        "--limit",
        "20",
    )
    if code != 0:
        return CheckResult(check, Status.SKIP, "gh unavailable / not authenticated")
    try:
        count = out.count('"number"')
    except Exception:
        count = 0
    if count >= 5:
        return CheckResult(check, Status.PASS, f"{count} good-first-issues open")
    return CheckResult(
        check,
        Status.FAIL,
        f"only {count} good-first-issues",
        "seed 5-10 good-first-issues with acceptance criteria + a local verify command",
    )
