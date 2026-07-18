"""Profiles + rule overrides — the layer that makes Invigil *yours*, not a rigid
corporate doctrine (survival Threat 1).

A `profile` picks a baseline posture; `.invigil.yml` `checks.*` then overrides it
(swap weights, demote mandatory checks to advisory dings, set the hard-fail gate).
`resolve()` turns a config into an `Effective` object the CLI uses to (a) pick which
layers run, (b) whether to go offline, (c) the enforce threshold, and (d) adjust each
check's weight/mandatory — via `dataclasses.replace`, so the shared registry singletons
are never mutated.
"""

from __future__ import annotations

import importlib.resources
import json
import logging
from dataclasses import dataclass, replace

from .config import InvigilConfig
from .model import Check

log = logging.getLogger(__name__)

# profile -> (only_layers, offline, default fail_on, all-checks-advisory)
PROFILES: dict[str, tuple[set[str] | None, bool, str | None, bool]] = {
    "strict": (None, False, "G4", False),
    "progressive": (None, False, "G3", False),
    "light": ({"local"}, True, None, True),
}
DEFAULT_PROFILE = "progressive"


def _load_profiles_json():
    try:
        from . import profiles

        # Use importlib.resources.files for Python 3.9+ compatibility
        for resource in importlib.resources.files(profiles).iterdir():
            if resource.name.endswith(".json"):
                data = json.loads(resource.read_text())
                name = resource.name[:-5]
                layers = set(data["only_layers"]) if data.get("only_layers") else None
                PROFILES[name] = (
                    layers,
                    bool(data.get("offline", False)),
                    data.get("fail_on"),
                    bool(data.get("advisory_all", False)),
                )
    except Exception as exc:
        log.warning("failed to load JSON profiles: %s", exc)


_load_profiles_json()


@dataclass
class Effective:
    only_layers: set[str] | None
    offline: bool
    fail_on: str | None
    advisory_all: bool
    optional_ids: set[str]
    weights: dict[str, int]

    def adjust(self, check: Check) -> Check:
        """Return a copy of `check` with weight/mandatory overrides applied."""
        weight = self.weights.get(check.id, check.weight)
        mandatory = check.mandatory
        if self.advisory_all or check.id in self.optional_ids:
            mandatory = False
        if weight == check.weight and mandatory == check.mandatory:
            return check
        return replace(check, weight=weight, mandatory=mandatory)


def resolve(config: InvigilConfig) -> Effective:
    only_layers, offline, fail_on, advisory = PROFILES.get(config.profile, PROFILES[DEFAULT_PROFILE])
    # config's explicit threshold wins over the profile default
    if config.fail_on:
        fail_on = config.fail_on
    return Effective(
        only_layers=only_layers,
        offline=offline,
        fail_on=fail_on,
        advisory_all=advisory,
        optional_ids=set(config.optional_checks),
        weights=dict(config.weights),
    )
