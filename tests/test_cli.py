"""End-to-end CLI: scoring a repo, output formats, and enforce exit codes."""

import json

import pytest

from invigil import cli

APACHE = "Apache License\nVersion 2.0\n"
GOOD_README = "# App\n\n## Quick Start\n\n```\npip install app\n```\n"


def make_good_repo(tmp_path):
    (tmp_path / "LICENSE").write_text(APACHE)
    (tmp_path / "README.md").write_text(GOOD_README)
    return tmp_path


def test_score_returns_scorecard(tmp_path):
    make_good_repo(tmp_path)
    sc, config = cli.score(tmp_path)
    assert config.name == tmp_path.name
    assert sc.results  # the full registry ran
    assert sc.gate_level() in {"—", "G1", "G2", "G3", "G4", "G5", "G6", "G7"}
    # A repo with only a LICENSE + README passes its G1 basics...
    assert any(r.check.id == "license-apache2" and r.status.value == "pass" for r in sc.results)


def test_gate_ge():
    assert cli._gate_ge("G4", "G4")
    assert cli._gate_ge("G5", "G4")
    assert not cli._gate_ge("G2", "G4")
    assert not cli._gate_ge("—", "G1")


def test_main_report_only_never_fails(tmp_path, capsys):
    # Empty repo scores terribly but report-only mode still exits 0.
    rc = cli.main(["score", str(tmp_path)])
    assert rc == 0
    assert "Invigil scorecard" in capsys.readouterr().out


def test_main_enforce_fails_below_gate(tmp_path):
    # Empty repo can't reach the default G4 -> enforce exits 1.
    assert cli.main(["score", str(tmp_path), "--enforce", "--min-gate", "G4"]) == 1


def test_main_json_format(tmp_path, capsys):
    make_good_repo(tmp_path)
    cli.main(["score", str(tmp_path), "--format", "json"])
    data = json.loads(capsys.readouterr().out)
    assert data["repo"] == tmp_path.name


def test_main_output_file(tmp_path):
    make_good_repo(tmp_path)
    out = tmp_path / "card.md"
    cli.main(["score", str(tmp_path), "--format", "markdown", "--output", str(out)])
    assert "Invigil" in out.read_text()


def test_main_missing_path_errors():
    assert cli.main(["score", "/no/such/repo/here"]) == 2


def test_main_requires_subcommand():
    with pytest.raises(SystemExit):
        cli.main([])


def test_check_group_offline_passes_and_fails(tmp_path, capsys):
    # 'layout' group: an empty repo fails (no LICENSE/README) -> exit 1
    assert cli.main(["check", "layout", str(tmp_path)]) == 1
    assert "invigil check layout" in capsys.readouterr().out
    # once the layout basics exist, the group passes -> exit 0
    make_good_repo(tmp_path)
    assert cli.main(["check", "layout", str(tmp_path)]) == 0


def test_score_offline_marks_network_skipped(tmp_path):
    make_good_repo(tmp_path)
    sc, _ = cli.score(tmp_path, offline=True)
    net = [r for r in sc.results if r.check.layer == "network"]
    assert net and all(r.status.value == "skip" for r in net)


def test_score_group_filter_runs_subset(tmp_path):
    make_good_repo(tmp_path)
    sc, _ = cli.score(tmp_path, only_groups={"layout"})
    assert sc.results and all(r.check.group == "layout" for r in sc.results)


def test_score_layer_filter_local_only(tmp_path):
    make_good_repo(tmp_path)
    sc, _ = cli.score(tmp_path, only_layers={"local"})
    assert all(r.check.layer == "local" for r in sc.results)
