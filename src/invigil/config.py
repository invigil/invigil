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

import yaml

CONFIG_NAMES = (".invigil.yml", ".invigil.yaml")


@dataclass
class InvigilConfig:
    name: str = ""
    language: str = "python"
    min_gate: str = "G4"
    enforce: bool = False
    disabled_checks: list[str] = field(default_factory=list)
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
        data = yaml.safe_load(path.read_text()) or {}
        project = data.get("project", {})
        checks = data.get("checks", {})
        return cls(
            name=project.get("name", repo.name),
            language=project.get("language", "python"),
            min_gate=project.get("min_gate", "G4"),
            enforce=bool(project.get("enforce", False)),
            disabled_checks=list(checks.get("disable", [])),
            artifacts=list(data.get("artifacts", [])),
            probes=list(data.get("probes", [])),
            services=dict(data.get("services", {})),
            boot_budget_minutes=int(data.get("boot_budget_minutes", 10)),
            raw=data,
        )
