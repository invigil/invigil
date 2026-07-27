"""G1 — secret hygiene (a hard prerequisite for any public repo).

A tracked private key or committed .env is an instant, non-negotiable failure.
The tracked-file scan is cheap and always runs; a full gitleaks history scan runs
when the binary is available and otherwise degrades to SKIP (so absence of the
tool never masquerades as a pass).
"""

from __future__ import annotations

import re
import shutil
from fnmatch import fnmatch

from ..context import Context
from ..model import CheckResult, Status
from . import register

# Filenames/patterns worth *looking inside*. A name is a candidate, never a verdict:
# `.pem` is the extension for certificates and CSRs too, and those are public by
# definition — flagging them accuses a project of leaking something it published.
SECRET_GLOBS = ("*.pem", "*.key", "*.p12", "*.pfx", "*.keystore", "id_rsa", "id_dsa", "*.ppk")
SECRET_EXACT = (".env",)  # .env.example / .env.sample are fine
ALLOW_SUFFIXES = (".pub",)  # public keys are not secrets

# The PEM armour that actually means "this is key material":
# BEGIN PRIVATE KEY / RSA PRIVATE KEY / EC PRIVATE KEY / OPENSSH PRIVATE KEY /
# ENCRYPTED PRIVATE KEY / PGP PRIVATE KEY BLOCK.
_PRIVATE_PEM = re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY( BLOCK)?-----")
# Certificates, CSRs and public keys ship in `.pem` constantly and are not secrets.
_PUBLIC_PEM = re.compile(r"-----BEGIN (CERTIFICATE|CERTIFICATE REQUEST|PUBLIC KEY|[A-Z0-9 ]*PUBLIC KEY)-----")

# Key material under these path segments is near-always a deliberate throwaway
# fixture — TLS/client-cert test suites cannot exist without one. Still worth
# surfacing, but it is a WARN, not an accusation of a leak.
_FIXTURE_SEGMENTS = frozenset(
    {"test", "tests", "testdata", "test_data", "fixtures", "__fixtures__", "e2e", "spec", "specs"}
)


def _looks_like_fixture(rel_path: str) -> bool:
    return any(seg in _FIXTURE_SEGMENTS for seg in rel_path.split("/")[:-1])


def _is_public_material(ctx: Context, rel_path: str) -> bool:
    """True if the file's own contents say it is public (cert / CSR / public key)."""
    try:
        head = ctx.path(rel_path).read_text(errors="replace")[:4096]
    except OSError:
        return False  # unreadable/binary keystore — treat as secret, not as safe
    return bool(_PUBLIC_PEM.search(head)) and not _PRIVATE_PEM.search(head)


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
    hits: list[str] = []
    fixtures: list[str] = []
    for f in files:
        base = f.rsplit("/", 1)[-1]
        if base.endswith(ALLOW_SUFFIXES):
            continue
        if not (base in SECRET_EXACT or any(fnmatch(base, g) for g in SECRET_GLOBS)):
            continue
        # A candidate by name. Read it before calling it a leak.
        if _is_public_material(ctx, f):
            continue
        (fixtures if _looks_like_fixture(f) else hits).append(f)

    if hits:
        return CheckResult(
            check,
            Status.FAIL,
            f"tracked secret(s): {', '.join(hits[:3])}",
            "git rm --cached the file(s), add to .gitignore, rotate the key, and scrub history (git filter-repo)",
        )
    if fixtures:
        return CheckResult(
            check,
            Status.WARN,
            f"key material under a test path: {', '.join(fixtures[:3])}",
            "if these are throwaway test fixtures, keep them and silence this via "
            "`checks: {disable: [no-tracked-secrets]}` in .invigil.yml; if any is a real key, "
            "rotate it and scrub history (git filter-repo)",
        )
    return CheckResult(check, Status.PASS, "no secret-looking files tracked")


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
