"""G1 — a stranger succeeds in 10 minutes on a clean machine.

These are the "is this even approachable?" checks: a real license, a landing-page
README that stays a landing page, a copy-paste quickstart, and an env-var config
surface instead of hardcoded values. Full G1 (the timed clean-machine boot) is
proven dynamically by the Stranger Gate; these are its static preconditions.
"""

from __future__ import annotations

from ..context import Context
from ..model import CheckResult, Status
from . import register

README_MAX_LINES = 300


@register(
    id="license-present",
    gate="G1",
    title="LICENSE file exists",
    weight=2,
    mandatory=True,
    discipline="D1",
)
def license_present(ctx: Context) -> CheckResult:
    """Mandatory: every OSS project needs *some* license.
    Which license is advisory — see license-apache2 (non-mandatory).
    """
    check = license_present.__invigil__  # type: ignore[attr-defined]
    p = ctx.first_existing("LICENSE", "LICENSE.txt", "LICENSE.md")
    if p is not None:
        return CheckResult(check, Status.PASS, f"{p.name} present")
    return CheckResult(
        check,
        Status.FAIL,
        "no LICENSE file",
        "add a LICENSE file at repo root — without one the repo is All Rights Reserved by default",
    )


@register(
    id="license-apache2",
    gate="G1",
    title="LICENSE is Apache-2.0 (advisory)",
    weight=1,
    mandatory=False,
    discipline="D1",
)
def license_apache2(ctx: Context) -> CheckResult:
    """Advisory: flags when the license is not Apache-2.0.
    MIT, GPL, MPL repos see this as a ding, never a gate failure.
    To enforce Apache-2.0, promote via .invigil.yml:
      checks:
        weights: { license-apache2: 3 }
    """
    check = license_apache2.__invigil__  # type: ignore[attr-defined]
    p = ctx.first_existing("LICENSE", "LICENSE.txt", "LICENSE.md")
    if p is None:
        return CheckResult(check, Status.SKIP, "no LICENSE file (checked by license-present)")
    text = p.read_text(errors="replace")
    if "Apache License" in text and "Version 2.0" in text:
        return CheckResult(check, Status.PASS, f"{p.name}: Apache-2.0")
    return CheckResult(
        check,
        Status.FAIL,
        f"{p.name} is not Apache-2.0",
        "optional: switch to Apache-2.0 for maximum OSS compatibility; "
        "see https://apache.org/licenses/LICENSE-2.0.txt",
    )


@register(id="readme-present", gate="G1", title="README exists", weight=1, discipline="D1")
def readme_present(ctx: Context) -> CheckResult:
    check = readme_present.__invigil__  # type: ignore[attr-defined]
    p = ctx.first_existing("README.md", "README.rst", "README")
    if p:
        return CheckResult(check, Status.PASS, p.name)
    return CheckResult(check, Status.FAIL, "no README", "add a README.md landing page")


@register(
    id="readme-length",
    gate="G1",
    title=f"README <= {README_MAX_LINES} lines (landing page, not the docs)",
    weight=1,
    discipline="D1",
)
def readme_length(ctx: Context) -> CheckResult:
    check = readme_length.__invigil__  # type: ignore[attr-defined]
    p = ctx.first_existing("README.md", "README.rst", "README")
    if p is None:
        return CheckResult(check, Status.FAIL, "no README", "add a README.md")
    n = len(p.read_text(errors="replace").splitlines())
    if n <= README_MAX_LINES:
        return CheckResult(check, Status.PASS, f"{n} lines")
    return CheckResult(
        check,
        Status.FAIL,
        f"{n} lines (> {README_MAX_LINES})",
        f"move deep sections into docs/ and link them; target <= {README_MAX_LINES} lines",
    )


@register(id="readme-quickstart", gate="G1", title="README has a Quick Start section", weight=1, discipline="D1")
def readme_quickstart(ctx: Context) -> CheckResult:
    check = readme_quickstart.__invigil__  # type: ignore[attr-defined]
    text = ctx.read("README.md").lower()
    if any(h in text for h in ("## quick start", "## quickstart", "## getting started", "## install")):
        return CheckResult(check, Status.PASS, "quickstart heading found")
    return CheckResult(
        check,
        Status.FAIL,
        "no quickstart heading",
        'add a "## Quick Start" section with <=5 copy-paste commands to first success',
    )


@register(
    id="env-example",
    gate="G1",
    title="Config is env-var driven (.env.example present)",
    weight=1,
    mandatory=False,
    discipline="D1",
)
def env_example(ctx: Context) -> CheckResult:
    check = env_example.__invigil__  # type: ignore[attr-defined]
    if ctx.first_existing(".env.example", ".env.sample", ".env.template"):
        return CheckResult(check, Status.PASS, ".env.example present")
    env_patterns = ("os.getenv(", "os.environ[", "os.environ.get", "(BaseSettings)")
    reads_env = any(
        m in p.read_text(errors="replace")
        for p in ctx.rglob("**/*.py")
        if "/invigil/" not in str(p)
        for m in env_patterns
    )
    has_surface = ctx.exists("docker-compose.yml") or ctx.exists("compose.yml") or reads_env
    if not has_surface:
        return CheckResult(check, Status.SKIP, "no runtime env-config surface")
    return CheckResult(
        check,
        Status.FAIL,
        "config surface exists but no .env.example",
        "add a .env.example documenting every env var; replace hardcoded values (e.g. localhost)",
    )
