"""The `invigil fix` loop.

For each *failing* check that has a registered fix: apply its mutations through the
broker, then immediately re-run that one check — the **single-pass rule**. If the
check still fails, it's flagged unresolved (a broken fix can never loop forever).
`--fix` is hard-disabled under CI so a misconfigured fix can't trigger cascading
automated commits on a protected branch.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .checks import FIXES, run_one
from .context import Context
from .model import CheckResult, Status
from .mutator import Mutator


def ci_active(env: dict | None = None) -> bool:
    """True under CI — where `--fix` must refuse to run (CI-lockout)."""
    e = env if env is not None else os.environ
    return str(e.get("CI", "")).strip().lower() in ("1", "true", "yes", "on")


@dataclass
class FixReport:
    fixed: list[str] = field(default_factory=list)  # failing -> now passing
    unresolved: list[str] = field(default_factory=list)  # fix ran, still failing
    no_fix: list[str] = field(default_factory=list)  # failing, no fix available
    changed_files: list[str] = field(default_factory=list)
    log: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.changed_files)


def apply_fixes(ctx: Context, results: list[CheckResult], *, dry_run: bool = False) -> FixReport:
    """Apply fixes for the failing checks in `results`, single-pass each."""
    rep = FixReport()
    mut = Mutator(ctx.repo, dry_run=dry_run)
    for r in results:
        if r.status is not Status.FAIL:
            continue
        fixfn = FIXES.get(r.check.id)
        if fixfn is None:
            rep.no_fix.append(r.check.id)
            continue
        for m in fixfn(ctx):
            mut.apply(m)
        again = run_one(ctx, r.check.id)  # the single pass
        if again is not None and again.status is Status.PASS:
            rep.fixed.append(r.check.id)
        else:
            rep.unresolved.append(r.check.id)
    rep.changed_files = mut.changed
    rep.log = mut.log
    return rep
