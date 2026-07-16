"""Loader for `.invigil.yml` — the per-repo declaration of what to check and
what the published artifacts / probes are for the Stranger Gate.

The config is intentionally small and declarative (config over code, per the
project's OSS conventions). A repo with no `.invigil.yml` still gets a full
static scorecard using sensible defaults; the file is only required for the
Layer-2 Stranger Gate (artifacts/probes) and for overriding checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

CONFIG_NAMES = (".invigil.yml", ".invigil.yaml")


@dataclass
class InvigilConfig:
    name: str = ""
    language: str = "python"
    min_gate: str = "G4"
    enforce: bool = False
    profile: str = "progressive"  # strict | progressive | light
    disabled_checks: list[str] = field(default_factory=list)
    optional_checks: list[str] = field(default_factory=list)  # force these non-mandatory
    weights: dict[str, int] = field(default_factory=dict)  # per-check weight overrides
    fail_on: str | None = None  # hard-fail at/below this gate (checks.thresholds.fail_on)
    artifacts: list[dict] = field(default_factory=list)
    probes: list[dict] = field(default_factory=list)
    services: dict = field(default_factory=dict)
    boot_budget_minutes: int = 10
    raw: dict = field(default_factory=dict)

    @classmethod
    def load(cls, repo: Path) -> InvigilConfig:
        path = next((repo / n for n in CONFIG_NAMES if (repo / n).exists()), None)
        if path is None:
            return cls(name=repo.name)
        # Lazy import: an offline `invigil check` on a repo with no config never
        # pays the PyYAML import cost (keeps the pre-commit path stdlib-only).
        import yaml

        data = yaml.safe_load(path.read_text()) or {}
        project = data.get("project", {})
        checks = data.get("checks", {})
        thresholds = checks.get("thresholds", {})
        return cls(
            name=project.get("name", repo.name),
            language=project.get("language", "python"),
            min_gate=project.get("min_gate", "G4"),
            enforce=bool(project.get("enforce", False)),
            profile=data.get("profile", "progressive"),
            disabled_checks=list(checks.get("disable", [])),
            optional_checks=list(checks.get("optional", [])),
            weights={str(k): int(v) for k, v in (checks.get("weights") or {}).items()},
            fail_on=thresholds.get("fail_on"),
            artifacts=list(data.get("artifacts", [])),
            probes=list(data.get("probes", [])),
            services=dict(data.get("services", {})),
            boot_budget_minutes=int(data.get("boot_budget_minutes", 10)),
            raw=data,
        )
