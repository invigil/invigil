"""G4 — supply-chain evidence is public (Discipline D3, the enterprise door).

A security-branded project is held to a higher bar, and meeting it publicly is
itself marketing: an OpenSSF Scorecard workflow (and a >=7 score), signed
releases with an SBOM, a security policy, and a changelog. The Scorecard score
is read live from scorecard.dev; if the repo isn't published there yet the check
degrades to SKIP rather than punishing an un-pushed repo.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from ..context import Context
from ..model import CheckResult, Status
from . import register

SCORECARD_MIN = 7.0


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
            score = float(json.load(resp).get("score", 0))
    except (urllib.error.URLError, ValueError, TimeoutError, OSError):
        return CheckResult(check, Status.SKIP, "scorecard.dev has no published score yet")
    if score >= SCORECARD_MIN:
        return CheckResult(check, Status.PASS, f"score {score}")
    return CheckResult(
        check,
        Status.FAIL,
        f"score {score} < {SCORECARD_MIN:.0f}",
        "triage the Scorecard findings (branch protection, token perms, pinned deps) to reach >=7",
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
