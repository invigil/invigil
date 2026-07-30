"""The published `.invigil.yml` schema must describe the config we actually accept.

`schema/invigil.schema.json` is not loaded by any code path — nothing validates against
it at runtime, so it can drift silently and nobody finds out until an editor red-underlines
a config that works fine. It did drift: the `audit` profile shipped and the schema kept
listing only strict/progressive/light, so a valid config was rejected by our own published
schema for three days.

A schema is a claim about the software. These tests make it a checked one.
"""

from __future__ import annotations

import json
from pathlib import Path

from invigil.engine import PROFILES

SCHEMA = json.loads((Path(__file__).resolve().parents[1] / "schema" / "invigil.schema.json").read_text())


def test_schema_profile_enum_matches_the_engine():
    declared = set(SCHEMA["properties"]["profile"]["enum"])
    real = set(PROFILES)
    assert declared == real, (
        f"schema/invigil.schema.json profile enum is out of sync with engine.PROFILES: "
        f"only in schema={sorted(declared - real)}, only in engine={sorted(real - declared)}"
    )


def test_every_profile_is_described():
    # An enum value nobody explains is a config option nobody can choose on purpose.
    description = SCHEMA["properties"]["profile"]["description"]
    for name in PROFILES:
        assert name in description, f"profile {name!r} is accepted but undocumented in the schema description"
