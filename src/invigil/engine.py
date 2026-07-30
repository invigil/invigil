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
from dataclasses import dataclass, field, replace

from .config import InvigilConfig
from .model import Check

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProfileSpec:
    """A named scoring posture.

    `optional_ids` demotes a check from mandatory (it stops gating), while a
    `weights` entry of 0 removes it from the score entirely — the check still
    runs and still reports, it just stops moving the grade. That split is what
    lets `audit` report Invigil's house-style checks as suggestions without
    letting them drag a third-party repo's letter down.
    """

    only_layers: set[str] | None = None
    offline: bool = False
    fail_on: str | None = None
    advisory_all: bool = False
    optional_ids: frozenset[str] = frozenset()
    weights: dict[str, int] = field(default_factory=dict)


PROFILES: dict[str, ProfileSpec] = {
    "strict": ProfileSpec(fail_on="G4"),
    "progressive": ProfileSpec(fail_on="G3"),
    "light": ProfileSpec(only_layers={"local"}, offline=True, advisory_all=True),
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
                PROFILES[name] = ProfileSpec(
                    only_layers=layers,
                    offline=bool(data.get("offline", False)),
                    fail_on=data.get("fail_on"),
                    advisory_all=bool(data.get("advisory_all", False)),
                    optional_ids=frozenset(data.get("optional_ids") or ()),
                    weights={str(k): int(v) for k, v in (data.get("weights") or {}).items()},
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
    spec = PROFILES.get(config.profile, PROFILES[DEFAULT_PROFILE])
    # config's explicit threshold wins over the profile default
    fail_on = config.fail_on or spec.fail_on
    # The repo's own .invigil.yml is the last word: profile values are the
    # baseline, anything set locally overrides it.
    return Effective(
        only_layers=spec.only_layers,
        offline=spec.offline,
        fail_on=fail_on,
        advisory_all=spec.advisory_all,
        optional_ids=set(spec.optional_ids) | set(config.optional_checks),
        weights={**spec.weights, **config.weights},
    )
