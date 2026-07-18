from invigil.config import InvigilConfig


def test_config_accepts_list_form_disabled_checks(tmp_path):
    (tmp_path / ".invigil.yml").write_text(
        "version: 1\nchecks:\n  disable:\n    - readme-present\n    - license-apache2\n"
    )

    cfg = InvigilConfig.load(tmp_path)

    assert cfg.disabled_checks == ["readme-present", "license-apache2"]


def test_config_keeps_mapping_form_disabled_checks(tmp_path):
    (tmp_path / ".invigil.yml").write_text(
        "version: 1\nchecks:\n  disable:\n    readme-present: true\n    license-apache2: legacy reason\n"
    )

    cfg = InvigilConfig.load(tmp_path)

    assert cfg.disabled_checks == ["readme-present", "license-apache2"]
