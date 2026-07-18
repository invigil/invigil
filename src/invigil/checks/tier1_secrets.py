"""G1 — secret hygiene (a hard prerequisite for any public repo).

A tracked private key or committed .env is an instant, non-negotiable failure.
The tracked-file scan is cheap and always runs; a full gitleaks history scan runs
when the binary is available and otherwise degrades to SKIP (so absence of the
tool never masquerades as a pass).
"""

from __future__ import annotations

import shutil
from fnmatch import fnmatch

from ..context import Context
from ..model import CheckResult, Status
from . import register

# Filenames/patterns that must never be tracked.
SECRET_GLOBS = ("*.pem", "*.key", "*.p12", "*.pfx", "*.keystore", "id_rsa", "id_dsa", "*.ppk")
SECRET_EXACT = (".env",)  # .env.example / .env.sample are fine
ALLOW_SUFFIXES = (".pub",)  # public keys are not secrets


@register(
    id="no-tracked-secrets",
    gate="G1",
    title="No secrets tracked in git",
    weight=2,
    discipline="D1",
    severity="blocker",  # a tracked secret blocks the gate regardless of other scores
)
def no_tracked_secrets(ctx: Context) -> CheckResult:
    check = no_tracked_secrets.__invigil__  # type: ignore[attr-defined]
    files = ctx.tracked_files()
    if not files:
        return CheckResult(check, Status.SKIP, "not a git repo / no tracked files")
    hits = []
    for f in files:
        base = f.rsplit("/", 1)[-1]
        if base.endswith(ALLOW_SUFFIXES):
            continue
        if base in SECRET_EXACT or any(fnmatch(base, g) for g in SECRET_GLOBS):
            hits.append(f)
    if not hits:
        return CheckResult(check, Status.PASS, "no secret-looking files tracked")
    return CheckResult(
        check,
        Status.FAIL,
        f"tracked secret(s): {', '.join(hits[:3])}",
        "git rm --cached the file(s), add to .gitignore, rotate the key, and scrub history (git filter-repo)",
    )


@register(
    id="gitleaks-clean",
    gate="G1",
    title="gitleaks finds no secrets in history",
    weight=1,
    mandatory=False,
    discipline="D1",
)
def gitleaks_clean(ctx: Context) -> CheckResult:
    check = gitleaks_clean.__invigil__  # type: ignore[attr-defined]
    if shutil.which("gitleaks") is None:
        return CheckResult(check, Status.SKIP, "gitleaks not installed")
    code, out = ctx._run("gitleaks", "detect", "--no-banner", "--redact")
    if code == 0:
        return CheckResult(check, Status.PASS, "gitleaks clean")
    return CheckResult(
        check,
        Status.FAIL,
        "gitleaks found secrets in history",
        "rotate the leaked secrets and scrub history; run `gitleaks detect` locally for detail",
    )
