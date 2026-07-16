"""G1 checks against synthetic repos, plus the invariant that every FAIL carries a fix."""

from pathlib import Path

import pytest

from invigil.checks import g1_stranger as g1
from invigil.config import InvigilConfig
from invigil.context import Context
from invigil.model import Status

APACHE = "Apache License\nVersion 2.0\n"


def ctx(tmp_path: Path) -> Context:
    return Context(repo=tmp_path, config=InvigilConfig.load(tmp_path))


def test_license_pass(tmp_path):
    (tmp_path / "LICENSE").write_text(APACHE)
    assert g1.license_apache2(ctx(tmp_path)).status is Status.PASS


def test_license_missing_fails_with_fix(tmp_path):
    r = g1.license_apache2(ctx(tmp_path))
    assert r.status is Status.FAIL
    assert r.fix  # D2: a failing check must tell you how to fix it


def test_license_wrong_kind_fails(tmp_path):
    (tmp_path / "LICENSE").write_text("MIT License\n")
    assert g1.license_apache2(ctx(tmp_path)).status is Status.FAIL


def test_readme_length_boundary(tmp_path):
    (tmp_path / "README.md").write_text("\n" * (g1.README_MAX_LINES - 1))
    assert g1.readme_length(ctx(tmp_path)).status is Status.PASS
    (tmp_path / "README.md").write_text("\n" * (g1.README_MAX_LINES + 50))
    r = g1.readme_length(ctx(tmp_path))
    assert r.status is Status.FAIL and str(g1.README_MAX_LINES) in r.fix


def test_quickstart_detected(tmp_path):
    (tmp_path / "README.md").write_text("# App\n\n## Quick Start\n\n```\npip install app\n```\n")
    assert g1.readme_quickstart(ctx(tmp_path)).status is Status.PASS


def test_env_example_skips_when_no_surface(tmp_path):
    assert g1.env_example(ctx(tmp_path)).status is Status.SKIP


@pytest.mark.parametrize("fn", [g1.license_apache2, g1.readme_length, g1.readme_quickstart])
def test_all_failures_have_fixes(tmp_path, fn):
    # empty repo -> everything that can fail, fails, and every failure has a fix
    r = fn(ctx(tmp_path))
    if r.status is Status.FAIL:
        assert r.fix, f"{r.check.id} failed without a fix"
