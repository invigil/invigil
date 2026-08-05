"""G4 — supply-chain evidence is public (the enterprise door).

A security-branded project is held to a higher bar, and meeting it publicly is
itself marketing: an OpenSSF Scorecard workflow (and a >=7 score), signed
releases with an SBOM, a security policy, and a changelog. The Scorecard score
is read live from scorecard.dev; if the repo isn't published there yet the check
degrades to SKIP rather than punishing an un-pushed repo.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from ..context import Context
from ..model import CheckResult, Status
from . import register

SCORECARD_MIN = 7.0

# Scorecard reports *what* is wrong; these say *how* to fix it. Keyed on Scorecard's own
# check names. Anything not listed falls back to Scorecard's `reason` — we echo their
# finding rather than inventing guidance we haven't verified.
_SCORECARD_PATTERNS = {
    "Token-Permissions": "set top-level `permissions: contents: read`, elevate per-job",
    "Pinned-Dependencies": "pin every `uses:` to a 40-char SHA (version in a trailing comment)",
    "Dangerous-Workflow": "replace `pull_request_target` + checkout with `pull_request`",
    "Signed-Releases": "sign with cosign and attach an SBOM in the release workflow",
    "Code-Review": "require one approving review in branch protection",
    "Branch-Protection": "protect the default branch (required checks + no force-push)",
    "Security-Policy": "add SECURITY.md with a private reporting address",
    "Fuzzing": "add a fuzzing target (OSS-Fuzz, or a `hypothesis`/`atheris` suite)",
    "SAST": "run a SAST tool (CodeQL, semgrep) on every PR",
    "CII-Best-Practices": "earn the OpenSSF best-practices badge at bestpractices.dev",
    "Contributors": "needs contributors from 2+ organisations (read from commit affiliations)",
    "Maintained": "commit or triage issues regularly -- the window is the last 90 days",
    "Vulnerabilities": "resolve the advisories OSV reports against your dependencies",
    "Binary-Artifacts": "remove checked-in binaries; build them in CI instead",
    "CI-Tests": "run the test suite on every pull request",
    "Dependency-Update-Tool": "add .github/dependabot.yml or renovate.json",
    "License": "add a LICENSE file Scorecard recognises (an SPDX-named one)",
    "Packaging": "publish the artifact from CI to a package registry",
}

_FIX_GENERIC = "triage the Scorecard findings (branch protection, token perms, pinned deps) to reach >=7"
_FIX_MAX_LEN = 200


# A `path:line` reference. Anchored on the trailing line number so it cannot swallow the
# remediation URLs Scorecard appends ("...: update your workflow using https://..."), and
# the lookahead stops it matching image tags -- `python:3.14-slim` is not `python:3`.
_LOCATION = re.compile(r"(?:^|\s)([\w./\\-]+:\d+)(?![\w.-])")


def _locations(check: dict) -> list[str]:
    """File:line references from a Scorecard check's details.

    Only `Warn:` lines describe something wrong -- `Info:` lines report what is already
    correct, so including them would point the reader at files that need no change.
    """
    seen: list[str] = []
    for line in check.get("details") or []:
        if not line.startswith("Warn:"):
            continue
        for loc in _LOCATION.findall(line):
            if loc not in seen:
                seen.append(loc)
    return seen


def _scorecard_fix(payload: dict) -> str:
    """Turn a Scorecard API response into one actionable line.

    The response carries every failing check with its file:line details; the old behaviour
    read `.score` and threw the rest away, leaving the reader to look up what we already
    knew. Single line by necessity -- `fix` is rendered inside a markdown table cell.
    """
    # score == -1 is Scorecard's internal error (Branch-Protection returns it without a
    # token), not a finding. Naming it would send someone to fix a working thing.
    failing = sorted(
        (c for c in payload.get("checks") or [] if 0 <= float(c.get("score", -1)) < 10),
        key=lambda c: float(c.get("score", 0)),
    )
    if not failing:
        return _FIX_GENERIC

    parts: list[str] = []
    for c in failing[:3]:
        name = c.get("name", "?")
        how = _SCORECARD_PATTERNS.get(name) or (c.get("reason") or "").strip()
        where = _locations(c)
        piece = f"{name} {float(c.get('score', 0)):g}/10: {how}"
        if where:
            piece += f" [{', '.join(where[:2])}{f' +{len(where) - 2}' if len(where) > 2 else ''}]"
        parts.append(piece)

    out = " · ".join(parts)
    if len(out) > _FIX_MAX_LEN:  # drop whole entries, never truncate mid-path
        while len(parts) > 1 and len(" · ".join(parts)) > _FIX_MAX_LEN:
            parts.pop()
        out = " · ".join(parts) + f" (+{len(failing) - len(parts)} more)"
    return out


@register(id="scorecard-workflow", gate="G4", title="OpenSSF Scorecard workflow present", weight=1, discipline="D3")
def scorecard_workflow(ctx: Context) -> CheckResult:
    check = scorecard_workflow.__invigil__  # type: ignore[attr-defined]
    if "ossf/scorecard-action" in ctx.workflows_text() or ctx.first_existing(".github/workflows/scorecard.yml"):
        return CheckResult(check, Status.PASS, "scorecard workflow present")
    return CheckResult(
        check,
        Status.FAIL,
        "no Scorecard workflow",
        "add ossf/scorecard-action (scheduled) and publish the badge once >=7",
    )


@register(
    id="scorecard-score",
    gate="G4",
    title=f"OpenSSF Scorecard >= {SCORECARD_MIN:.0f}",
    weight=1,
    mandatory=False,
    discipline="D3",
)
def scorecard_score(ctx: Context) -> CheckResult:
    check = scorecard_score.__invigil__  # type: ignore[attr-defined]
    slug = ctx.repo_slug()
    if not slug:
        return CheckResult(check, Status.SKIP, "no github remote to look up")
    try:
        url = f"https://api.scorecard.dev/projects/github.com/{slug}"
        with urllib.request.urlopen(url, timeout=8) as resp:  # noqa: S310 (fixed https host)
            payload = json.load(resp)
        score = float(payload.get("score", 0))
    except (urllib.error.URLError, TimeoutError, OSError):
        # Network flake / not published yet: SKIP (excluded from the grade) so a
        # timeout can never move the score. Resilience over a spurious downgrade.
        return CheckResult(check, Status.SKIP, "scorecard.dev unreachable — excluded from grade")
    except ValueError:
        return CheckResult(check, Status.SKIP, "scorecard.dev returned no score yet")
    if score >= SCORECARD_MIN:
        return CheckResult(check, Status.PASS, f"score {score}")
    return CheckResult(
        check,
        Status.FAIL,
        f"score {score} < {SCORECARD_MIN:.0f}",
        _scorecard_fix(payload),
    )


@register(id="signed-releases-sbom", gate="G4", title="Releases are signed and ship an SBOM", weight=2, discipline="D3")
def signed_releases_sbom(ctx: Context) -> CheckResult:
    check = signed_releases_sbom.__invigil__  # type: ignore[attr-defined]
    text = ctx.workflows_text()
    signed = "cosign" in text or "sigstore" in text
    sbom = "syft" in text or "sbom" in text.lower() or "spdx" in text.lower()
    if signed and sbom:
        return CheckResult(check, Status.PASS, "cosign + SBOM in release workflow")
    missing = ", ".join(m for m, ok in (("signing (cosign)", signed), ("SBOM (syft)", sbom)) if not ok)
    return CheckResult(
        check,
        Status.FAIL,
        f"release evidence missing: {missing}",
        "sign release artifacts with cosign (keyless) and attach a syft SPDX SBOM",
    )


@register(id="security-policy", gate="G4", title="SECURITY.md present", weight=1, discipline="D3")
def security_policy(ctx: Context) -> CheckResult:
    check = security_policy.__invigil__  # type: ignore[attr-defined]
    if ctx.first_existing("SECURITY.md", ".github/SECURITY.md", "docs/SECURITY.md"):
        return CheckResult(check, Status.PASS, "SECURITY.md present")
    return CheckResult(
        check,
        Status.FAIL,
        "no SECURITY.md",
        "add SECURITY.md with a private report channel and a supported-versions table",
    )


@register(id="changelog", gate="G4", title="CHANGELOG.md present", weight=1, mandatory=False, discipline="D4")
def changelog(ctx: Context) -> CheckResult:
    check = changelog.__invigil__  # type: ignore[attr-defined]
    if ctx.first_existing("CHANGELOG.md", "CHANGELOG.rst", "docs/CHANGELOG.md"):
        return CheckResult(check, Status.PASS, "CHANGELOG present")
    return CheckResult(
        check,
        Status.FAIL,
        "no CHANGELOG",
        "keep a CHANGELOG.md (Keep a Changelog format) with honest caveats per release",
    )
