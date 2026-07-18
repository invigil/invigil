"""B1 — Plugin manager.

Four focused functions — each independently testable:

    discover_plugins(repo)          → list[Path]
    load_plugin(path)               → module
    validate_manifest(manifest)     → dict   (validated copy)
    merge_registry(builtins, extra) → list[tuple[Check, Callable]]

Top-level entry point:

    build_registry(repo) → list[tuple[Check, Callable]]

Called by `run_all()` in `checks/__init__.py`. With no `.invigil/plugins/` dir
the call returns `REGISTRY` unchanged in constant time — zero overhead on repos
that don't use project plugins.
"""

from __future__ import annotations

import importlib.util
import logging
from collections.abc import Callable
from pathlib import Path

from .hookspecs import (
    REQUIRED_MANIFEST_KEYS,
    VALID_EFFORTS,
    VALID_GATES,
    VALID_LAYERS,
    VALID_SEVERITIES,
)
from .model import Check, CheckResult, Status

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class PluginLoadError(Exception):
    """Raised when a plugin file cannot be imported."""


# ---------------------------------------------------------------------------
# Stage 1 — Discover
# ---------------------------------------------------------------------------


def discover_plugins(repo: Path) -> list[Path]:
    """Return all *.py files in .invigil/plugins/ (sorted for determinism).

    Returns an empty list when the directory doesn't exist — this is the
    normal case for repos that don't use project plugins.
    """
    plugin_dir = repo / ".invigil" / "plugins"
    if not plugin_dir.is_dir():
        return []
    return sorted(plugin_dir.glob("*.py"))


# ---------------------------------------------------------------------------
# Stage 2 — Load
# ---------------------------------------------------------------------------


def load_plugin(path: Path):
    """Import a plugin file and return its module object.

    Raises:
        PluginLoadError: if the file cannot be imported (syntax error,
            missing dependency, etc.)
    """
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise PluginLoadError(f"cannot create module spec for {path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)  # type: ignore[union-attr]
    except Exception as exc:
        raise PluginLoadError(f"import error in {path.name}: {exc}") from exc
    if not hasattr(module, "invigil_register_check"):
        raise PluginLoadError(
            f"{path.name} has no `invigil_register_check()` function — add it to register checks with Invigil"
        )
    return module


# ---------------------------------------------------------------------------
# Stage 3 — Validate
# ---------------------------------------------------------------------------


def validate_manifest(manifest: dict, source: str = "") -> dict:
    """Validate a single check manifest dict returned by a plugin.

    Returns the validated manifest (with defaults filled in) on success.
    Raises ValueError with a descriptive message on any schema violation.

    Args:
        manifest: the dict to validate
        source:   human label for error messages (e.g. plugin filename)
    """
    loc = f"[{source}] " if source else ""

    # Required keys
    missing = REQUIRED_MANIFEST_KEYS - manifest.keys()
    if missing:
        raise ValueError(f"{loc}manifest missing required keys: {sorted(missing)!r}")

    # Enum validations
    gate = manifest["gate"]
    if gate not in VALID_GATES:
        raise ValueError(f"{loc}invalid gate {gate!r}; must be one of {sorted(VALID_GATES)}")

    layer = manifest["layer"]
    if layer not in VALID_LAYERS:
        raise ValueError(f"{loc}invalid layer {layer!r}; must be one of {sorted(VALID_LAYERS)}")

    effort = manifest.get("effort", "hours")
    if effort not in VALID_EFFORTS:
        raise ValueError(f"{loc}invalid effort {effort!r}; must be one of {sorted(VALID_EFFORTS)}")

    severity = manifest.get("severity", "standard")
    if severity not in VALID_SEVERITIES:
        raise ValueError(f"{loc}invalid severity {severity!r}; must be one of {sorted(VALID_SEVERITIES)}")

    cb = manifest["check_callback"]
    if not callable(cb):
        raise ValueError(f"{loc}`check_callback` must be callable, got {type(cb).__name__!r}")

    fix_cb = manifest.get("fix_callback")
    if fix_cb is not None and not callable(fix_cb):
        raise ValueError(f"{loc}`fix_callback` must be callable or None, got {type(fix_cb).__name__!r}")

    # Return validated copy with defaults applied
    return {
        "id": manifest["id"],
        "gate": gate,
        "title": manifest["title"],
        "weight": int(manifest.get("weight", 1)),
        "mandatory": bool(manifest.get("mandatory", True)),
        "layer": layer,
        "group": manifest["group"],
        "effort": effort,
        "severity": severity,
        "discipline": manifest.get("discipline", ""),
        "check_callback": cb,
        "fix_callback": fix_cb,
    }


# ---------------------------------------------------------------------------
# Stage 4 — Merge
# ---------------------------------------------------------------------------


def merge_registry(
    builtins: list[tuple[Check, Callable]],
    extras: list[tuple[Check, Callable]],
) -> list[tuple[Check, Callable]]:
    """Merge project-plugin checks into the builtin registry.

    Deduplication policy: builtin check IDs always win. A project plugin with
    the same ID as a builtin emits a log warning and is silently skipped — no
    silent overrides, no crashes.

    Args:
        builtins: the existing REGISTRY list
        extras:   checks contributed by project plugins

    Returns:
        Combined list, builtins first, extras appended (minus any duplicates).
    """
    builtin_ids = {check.id for check, _ in builtins}
    merged = list(builtins)
    for check, fn in extras:
        if check.id in builtin_ids:
            log.warning("plugin check %r shadows builtin — skipped (builtin always wins)", check.id)
        else:
            merged.append((check, fn))
    return merged


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def build_registry(
    repo: Path,
    builtins: list[tuple[Check, Callable]] | None = None,
) -> tuple[list[tuple[Check, Callable]], list[CheckResult]]:
    """Build the full check registry for *repo*, including any project plugins.

    Steps: discover → load → validate → merge.

    On any plugin error (import failure, bad manifest):
        - emits a WARN CheckResult (visible in the scorecard)
        - skips the offending plugin
        - never crashes the gate

    Returns:
        (registry, warn_results) where warn_results is a (possibly empty) list
        of WARN CheckResults to inject into the scorecard.
    """
    if builtins is None:
        # Lazy import to avoid a circular dependency at module load time
        from .checks import REGISTRY

        builtins = REGISTRY

    plugin_paths = discover_plugins(repo)
    if not plugin_paths:
        # Fast path: no plugins → return builtins unchanged
        return list(builtins), []

    warn_results: list[CheckResult] = []
    extra_checks: list[tuple[Check, Callable]] = []

    for path in plugin_paths:
        # Load
        try:
            module = load_plugin(path)
        except PluginLoadError as exc:
            log.warning("failed to load plugin %s: %s", path.name, exc)
            warn_results.append(_plugin_warn(f"plugin-load-{path.stem}", str(exc)))
            continue

        # Validate each manifest returned by the plugin
        try:
            raw_manifests: list[dict] = module.invigil_register_check()
        except Exception as exc:
            msg = f"{path.name}: invigil_register_check() raised {exc}"
            log.warning(msg)
            warn_results.append(_plugin_warn(f"plugin-call-{path.stem}", msg))
            continue

        for manifest in raw_manifests:
            try:
                m = validate_manifest(manifest, source=path.name)
            except ValueError as exc:
                log.warning("invalid manifest in %s: %s", path.name, exc)
                warn_results.append(_plugin_warn(f"plugin-schema-{path.stem}", str(exc)))
                continue

            check = Check(
                id=m["id"],
                gate=m["gate"],
                title=m["title"],
                weight=m["weight"],
                mandatory=m["mandatory"],
                layer=m["layer"],
                group=m["group"],
                effort=m["effort"],
                severity=m["severity"],
                discipline=m["discipline"],
            )
            extra_checks.append((check, m["check_callback"]))

    registry = merge_registry(builtins, extra_checks)
    return registry, warn_results


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _plugin_warn(check_id: str, detail: str) -> CheckResult:
    """Produce a WARN CheckResult for a plugin load/validation failure."""
    check = Check(
        id=check_id,
        gate="G1",
        title=f"Plugin: {check_id}",
        mandatory=False,
        layer="local",
        group="layout",
    )
    return CheckResult(
        check,
        Status.WARN,
        detail=detail,
        fix="check the plugin file for import errors or invalid manifest keys",
    )
