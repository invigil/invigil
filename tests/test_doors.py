"""Presence checks against the naming conventions real projects actually use.

Every case here is a repo Invigil told "you don't have X" while X sat in the tree
under a different spelling. Measured over 27 third-party repos: see the Phase 2
false-positive audit.
"""

from pathlib import Path

import pytest

from invigil.checks import g4_evidence as g4
from invigil.checks import g5_doors as g5
from invigil.config import InvigilConfig
from invigil.context import Context
from invigil.model import Status


def ctx(tmp_path: Path) -> Context:
    return Context(repo=tmp_path, config=InvigilConfig.load(tmp_path))


def write(tmp_path: Path, rel: str, body: str = "x\n") -> None:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)


# Regression: 15 of the 19 repos we told "no CHANGELOG" were shipping release
# history — flask CHANGES.rst, celery Changelog.rst, scrapy NEWS, requests
# HISTORY.md, jq ChangeLog, asciidoctor CHANGELOG.adoc, fastapi release-notes.md.
@pytest.mark.parametrize(
    "rel",
    [
        "CHANGES.rst", "CHANGES.md", "Changelog.rst", "ChangeLog", "NEWS", "NEWS.md",
        "HISTORY.md", "CHANGELOG.adoc", "docs/changes.rst", "docs/release-notes.md",
    ],
)
def test_changelog_recognised_under_any_convention(tmp_path, rel):
    write(tmp_path, rel)
    assert g4.changelog(ctx(tmp_path)).status is Status.PASS


def test_changelog_fragments_directory_counts(tmp_path):
    # towncrier (tox-dev/tox) keeps unreleased entries as fragments, not a file.
    write(tmp_path, "changelog.d/1234.bugfix.rst")
    assert g4.changelog(ctx(tmp_path)).status is Status.PASS


def test_changelog_absent_still_fails(tmp_path):
    write(tmp_path, "README.md", "# app\n")
    assert g4.changelog(ctx(tmp_path)).status is Status.FAIL


# Regression: sphinx-doc/sphinx ships CONTRIBUTING.rst, chalk lowercase
# contributing.md. Both were reported as having no contributor door at all.
@pytest.mark.parametrize(
    "rel",
    ["CONTRIBUTING.rst", "contributing.md", "CONTRIBUTING.adoc", "docs/contributing.rst", ".github/CONTRIBUTING.md"],
)
def test_contributor_door_recognised_under_any_convention(tmp_path, rel):
    write(tmp_path, rel)
    assert g5.contributor_door(ctx(tmp_path)).status is Status.PASS


def test_contributor_door_absent_still_fails(tmp_path):
    write(tmp_path, "README.md", "# app\n")
    assert g5.contributor_door(ctx(tmp_path)).status is Status.FAIL


@pytest.mark.parametrize("rel", ["CODE-OF-CONDUCT.md", "code_of_conduct.md", "docs/CODE_OF_CONDUCT.rst"])
def test_code_of_conduct_recognised_under_any_convention(tmp_path, rel):
    write(tmp_path, rel)
    assert g5.code_of_conduct(ctx(tmp_path)).status is Status.PASS


# Regression: every Sphinx repo in the sample (requests, flask, scrapy, numpy,
# celery, sphinx, tox) has a docs index; we looked only for Markdown and told all
# seven they had none. Antora, Hugo and per-locale mkdocs had the same problem.
@pytest.mark.parametrize(
    "rel",
    [
        "docs/index.rst",
        "doc/index.rst",
        "doc/source/index.rst",
        "docs/conf.py",
        "docs/antora.yml",
        "site/content/_index.md",
        "docs/en/mkdocs.yml",
        "website/docs/index.md",
        "docs/README.md",
        "docs/SUMMARY.md",
    ],
)
def test_docs_index_recognised_under_any_toolchain(tmp_path, rel):
    write(tmp_path, rel)
    assert g5.docs_index(ctx(tmp_path)).status is Status.PASS


def test_docs_index_absent_still_fails(tmp_path):
    # ripgrep, fzf, chalk genuinely have no docs tree — that is a real finding.
    write(tmp_path, "README.md", "# app\n")
    assert g5.docs_index(ctx(tmp_path)).status is Status.FAIL


def test_docs_dir_without_an_index_still_fails(tmp_path):
    write(tmp_path, "docs/advanced-tuning.md")
    assert g5.docs_index(ctx(tmp_path)).status is Status.FAIL
