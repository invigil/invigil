"""The check registry.

Each check is a function `(Context) -> CheckResult` decorated with `@register`,
which pins its Check metadata (id, gate, weight, discipline). `run_all` executes
every registered check against a repo, honouring `checks.disable` from config.

Modules are imported for their side effect of registering checks. Add a new
discipline module here and its checks light up automatically.
"""

from __future__ import annotations

from collections.abc import Callable

from ..context import Context
from ..model import Check, CheckResult, Status

REGISTRY: list[tuple[Check, Callable[[Context], CheckResult]]] = []


def register(**meta):
    """Decorator: attach Check metadata to a check function and register it."""

    def wrap(fn: Callable[[Context], CheckResult]) -> Callable[[Context], CheckResult]:
        check = Check(**meta)
        # Expose the Check on the function so its body can build CheckResults
        # without repeating the metadata.
        fn.__invigil__ = check  # type: ignore[attr-defined]
        REGISTRY.append((check, fn))
        return fn

    return wrap


def run_all(ctx: Context) -> list[CheckResult]:
    results: list[CheckResult] = []
    for check, fn in REGISTRY:
        if check.id in ctx.config.disabled_checks:
            results.append(CheckResult(check, Status.SKIP, detail="disabled in .invigil.yml"))
            continue
        try:
            results.append(fn(ctx))
        except Exception as exc:  # a check must never crash the gate
            results.append(CheckResult(check, Status.WARN, detail=f"check errored: {exc}", fix="file an Invigil bug"))
    return results


# Import check modules for their registration side effects. Order is cosmetic;
# checks are grouped in the report by gate, not by import order.
from . import (  # noqa: E402,F401
    g1_stranger,
    g2_errors,
    g3_supply,
    g4_evidence,
    g5_doors,
    tier1_secrets,
)
