"""Tests that JSON profiles load correctly and override hardcoded defaults."""

from invigil.engine import PROFILES


def test_strict_profile_loaded():
    p = PROFILES["strict"]
    assert p.only_layers is None
    assert p.offline is False
    assert p.fail_on == "G4"
    assert p.advisory_all is False


def test_progressive_profile_loaded():
    p = PROFILES["progressive"]
    assert p.only_layers is None
    assert p.offline is False
    assert p.fail_on == "G3"
    assert p.advisory_all is False


def test_light_profile_loaded():
    p = PROFILES["light"]
    assert p.only_layers == {"local"}
    assert p.offline is True
    assert p.fail_on is None
    assert p.advisory_all is True


def test_audit_profile_loaded():
    p = PROFILES["audit"]
    # Auditing a repo you do not own must never fail someone's build.
    assert p.fail_on is None
    assert p.advisory_all is False
    # House-style checks report but carry no weight, so they cannot drag the grade.
    assert p.weights["operator-door"] == 0
    assert p.weights["good-first-issues"] == 0
    # Real findings that should not collapse the gate ladder are demoted instead.
    assert "readme-length" in p.optional_ids


def test_audit_does_not_zero_out_universal_checks():
    # The checks a maintainer concedes on sight must keep their weight, or the
    # audit profile is flattery rather than a score.
    p = PROFILES["audit"]
    for cid in ("license-present", "no-tracked-secrets", "smoke-published", "signed-releases-sbom"):
        assert p.weights.get(cid, 1) != 0, f"{cid} must still count in audit"
