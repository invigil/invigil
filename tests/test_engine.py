"""Profiles + rule overrides (M3)."""

from invigil import engine
from invigil.config import InvigilConfig
from invigil.model import Check


def test_profiles():
    prog = engine.resolve(InvigilConfig(profile="progressive"))
    assert prog.fail_on == "G3" and prog.only_layers is None and prog.offline is False

    light = engine.resolve(InvigilConfig(profile="light"))
    assert light.only_layers == {"local"} and light.offline is True
    assert light.advisory_all is True and light.fail_on is None

    strict = engine.resolve(InvigilConfig(profile="strict"))
    assert strict.fail_on == "G4"


def test_config_threshold_overrides_profile():
    eff = engine.resolve(InvigilConfig(profile="progressive", fail_on="G5"))
    assert eff.fail_on == "G5"


def test_adjust_weight_override():
    eff = engine.resolve(InvigilConfig(weights={"license-apache2": 5}))
    c = Check(id="license-apache2", gate="G1", title="x", weight=2)
    assert eff.adjust(c).weight == 5


def test_adjust_optional_demotes_mandatory():
    eff = engine.resolve(InvigilConfig(optional_checks=["security-policy"]))
    c = Check(id="security-policy", gate="G4", title="x", mandatory=True)
    assert eff.adjust(c).mandatory is False


def test_adjust_light_makes_everything_advisory():
    eff = engine.resolve(InvigilConfig(profile="light"))
    c = Check(id="whatever", gate="G4", title="x", mandatory=True)
    assert eff.adjust(c).mandatory is False


def test_adjust_returns_same_object_when_no_change():
    eff = engine.resolve(InvigilConfig(profile="progressive"))
    c = Check(id="x", gate="G1", title="x", weight=1, mandatory=True)
    assert eff.adjust(c) is c  # no needless copy


def test_config_parses_overrides(tmp_path):
    (tmp_path / ".invigil.yml").write_text(
        "version: 1\n"
        "profile: light\n"
        "checks:\n"
        "  optional: [version-matrix]\n"
        "  weights: { license-apache2: 3 }\n"
        "  thresholds: { fail_on: G2 }\n"
    )
    cfg = InvigilConfig.load(tmp_path)
    assert cfg.profile == "light"
    assert cfg.optional_checks == ["version-matrix"]
    assert cfg.weights == {"license-apache2": 3}
    assert cfg.fail_on == "G2"
