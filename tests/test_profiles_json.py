"""Tests that JSON profiles load correctly and override hardcoded defaults."""

from invigil.engine import PROFILES


def test_strict_profile_loaded():
    assert "strict" in PROFILES
    only_layers, offline, fail_on, advisory_all = PROFILES["strict"]
    assert only_layers is None
    assert offline is False
    assert fail_on == "G4"
    assert advisory_all is False


def test_progressive_profile_loaded():
    assert "progressive" in PROFILES
    only_layers, offline, fail_on, advisory_all = PROFILES["progressive"]
    assert only_layers is None
    assert offline is False
    assert fail_on == "G3"
    assert advisory_all is False


def test_light_profile_loaded():
    assert "light" in PROFILES
    only_layers, offline, fail_on, advisory_all = PROFILES["light"]
    assert only_layers == {"local"}
    assert offline is True
    assert fail_on is None
    assert advisory_all is True
