"""B1 — Plugin contract (hookspecs).

Defines `InvigilPlugin` — the Protocol that every project plugin must satisfy.
Plugin authors never need to import this; it's used internally for validation.

The contract is intentionally minimal: one function, one return type, no base
class. This keeps the plugin-author experience as simple as possible — just
define `invigil_register_check()` in a `.py` file.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class InvigilPlugin(Protocol):
    """The contract every Invigil project plugin must satisfy.

    A plugin is any Python module that exports `invigil_register_check()`.
    No base class. No imports from Invigil required to write a plugin.

    Example plugin (.invigil/plugins/my_check.py)::

        def invigil_register_check() -> list[dict]:
            return [{
                "id":             "my-check",
                "gate":           "G2",
                "title":          "My custom rule",
                "layer":          "local",
                "group":          "layout",
                "effort":         "minutes",
                "check_callback": _run,
            }]

        def _run(ctx):
            from invigil.model import Check, CheckResult, Status
            check = Check(id="my-check", gate="G2", title="My custom rule")
            if (ctx.repo / "MY_FILE.md").exists():
                return CheckResult(check, Status.PASS, "found")
            return CheckResult(check, Status.FAIL, "missing", "add MY_FILE.md")
    """

    def invigil_register_check(self) -> list[dict]:
        """Return one manifest dict per check.

        Required keys:
            id (str): unique, kebab-case identifier
            gate (str): "G1".."G7"
            title (str): human-readable description
            layer (str): "local" | "network" | "heavy"
            group (str): e.g. "layout", "ai", "supply-chain"
            check_callback (Callable[[Context], CheckResult])

        Optional keys (defaults shown):
            weight (int): 1
            mandatory (bool): True
            effort (str): "hours"  — "minutes" | "hours" | "days"
            severity (str): "standard"  — "standard" | "blocker"
            fix_callback (Callable | None): None
        """


# Required manifest keys — validated by manager.validate_manifest()
REQUIRED_MANIFEST_KEYS: frozenset[str] = frozenset({"id", "gate", "title", "layer", "group", "check_callback"})

# Valid enum values
VALID_GATES: frozenset[str] = frozenset({"G1", "G2", "G3", "G4", "G5", "G6", "G7"})
VALID_LAYERS: frozenset[str] = frozenset({"local", "network", "heavy"})
VALID_EFFORTS: frozenset[str] = frozenset({"minutes", "hours", "days", ""})
VALID_SEVERITIES: frozenset[str] = frozenset({"standard", "blocker"})
