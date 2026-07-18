"""The check registry.

Each check is a function `(Context) -> CheckResult` decorated with `@register`,
which pins its Check metadata (id, gate, weight, discipline). `run_all` executes
every registered check against a repo, honouring `checks.disable` from config.

Modules are imported for their side effect of registering checks. Add a new
discipline module here and its checks light up automatically.
"""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter

from ..context import Context
from ..model import Check, CheckResult, Status
from ..mutator import Mutation

REGISTRY: list[tuple[Check, Callable[[Context], CheckResult]]] = []

# check id -> a fix that returns the mutations which should make the check pass.
FIXES: dict[str, Callable[[Context], list[Mutation]]] = {}


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


def fix(check_id: str):
    """Decorator: register a fix for a check id. The fix returns the mutations
    that should make that check pass; the fix engine applies them, then re-runs
    the one check (the single-pass rule)."""

    def wrap(fn: Callable[[Context], list[Mutation]]) -> Callable[[Context], list[Mutation]]:
        FIXES[check_id] = fn
        return fn

    return wrap


def run_one(ctx: Context, check_id: str) -> CheckResult | None:
    """Run a single check by id — used to re-verify after a fix (single-pass).

    Searches both builtin REGISTRY and any project-plugin checks.
    """
    from ..manager import build_registry

    registry, _ = build_registry(ctx.repo)
    for check, fn in registry:
        if check.id == check_id:
            return fn(ctx)
    return None


def run_all(
    ctx: Context,
    *,
    only_layers: set[str] | None = None,
    only_groups: set[str] | None = None,
    offline: bool = False,
) -> list[CheckResult]:
    """Run all registered checks (builtin + project plugins), optionally filtered.

    Project plugins are discovered from `.invigil/plugins/*.py` in the repo.
    On any plugin error, a WARN result is injected — the gate never crashes.

    - `only_layers` / `only_groups`: run just that subset (the rest are omitted,
      not reported — used by `invigil check <group>` and `--layer`).
    - `offline`: never touch the network; `network`-layer checks become a SKIP
      instead of running (used by pre-commit and `--offline`).
    """
    from ..manager import build_registry

    registry, plugin_warns = build_registry(ctx.repo)

    results: list[CheckResult] = list(plugin_warns)  # plugin errors appear first
    for check, fn in registry:
        if only_layers and check.layer not in only_layers:
            continue
        if only_groups and check.group not in only_groups:
            continue
        if check.id in ctx.config.disabled_checks:
            results.append(CheckResult(check, Status.SKIP, detail="disabled in .invigil.yml"))
            continue
        if offline and check.layer == "network":
            results.append(CheckResult(check, Status.SKIP, detail="offline — network check skipped"))
            continue
        started_at = perf_counter()
        try:
            result = fn(ctx)
        except Exception as exc:  # a check must never crash the gate
            result = CheckResult(
                check,
                Status.WARN,
                detail=f"check errored: {exc}",
                fix="file an Invigil bug",
            )
        result.duration_ms = round((perf_counter() - started_at) * 1000, 3)
        results.append(result)
    return results


# Import check modules for their registration side effects. Order is cosmetic;
# checks are grouped in the report by gate, not by import order.
from . import (  # noqa: E402,F401
    ai_native,
    g1_stranger,
    g2_errors,
    g3_supply,
    g4_evidence,
    g5_doors,
    tier1_secrets,
)
from . import fixes as fixes  # noqa: E402,F401  (registers @fix handlers)

# Central layer/group tagging — one place to maintain, so the 20+ `@register`
# call sites stay clean. id -> (layer, group). Anything unlisted keeps the Check
# defaults (local, "").
TAGS: dict[str, tuple[str, str]] = {
    # layout (G1 stranger-readiness)
    "license-present": ("local", "layout"),
    "license-apache2": ("local", "layout"),
    "readme-present": ("local", "layout"),
    "readme-length": ("local", "layout"),
    "readme-quickstart": ("local", "layout"),
    "env-example": ("local", "layout"),
    # secrets (secret hygiene)
    "no-tracked-secrets": ("local", "secrets"),
    "gitleaks-clean": ("local", "secrets"),
    # errors (G2)
    "deep-health": ("local", "errors"),
    "error-correlation-id": ("local", "errors"),
    "error-path-tests": ("local", "errors"),
    # supply-chain (G3)
    "smoke-published": ("local", "supply-chain"),
    "dependabot": ("local", "supply-chain"),
    "actions-sha-pinned": ("local", "supply-chain"),
    "lockfile-enforced": ("local", "supply-chain"),
    "coverage-gate": ("local", "supply-chain"),
    "version-matrix": ("local", "supply-chain"),
    # evidence (G4)
    "scorecard-workflow": ("local", "evidence"),
    "scorecard-score": ("network", "evidence"),
    "signed-releases-sbom": ("local", "evidence"),
    "security-policy": ("local", "evidence"),
    "changelog": ("local", "evidence"),
    # doors (G5) + ai
    "docs-index": ("local", "doors"),
    "contributor-door": ("local", "doors"),
    "code-of-conduct": ("local", "doors"),
    "operator-door": ("local", "doors"),
    "ai-door": ("local", "ai"),
    "good-first-issues": ("network", "doors"),
    # ai-native (M5)
    "llms-no-secrets": ("local", "ai"),
    "agent-scope-visibility": ("local", "ai"),
    "agents-md-actionable": ("local", "ai"),
    "llms-txt-shape": ("local", "ai"),
    "agent-context-fresh": ("local", "ai"),
    "readme-heading-hierarchy": ("local", "ai"),
    "exit-codes-documented": ("local", "ai"),
}


def _apply_tags() -> None:
    for check, _ in REGISTRY:
        check.layer, check.group = TAGS.get(check.id, (check.layer, check.group))


_apply_tags()

# Group/layer names the CLI exposes (for `invigil check <group>` / `--layer`).
GROUPS = sorted({g for _, g in TAGS.values()})
LAYERS = ("local", "network", "heavy")
