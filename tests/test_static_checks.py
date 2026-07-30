"""Coverage for the G2–G5 and Tier-1 check modules against synthetic repos.

Network/gh-backed checks (scorecard score, good-first-issues) SKIP without a
remote, which is the behavior we assert — no network is touched in tests.
"""

import subprocess
from pathlib import Path

import pytest

from invigil.checks import ai_native
from invigil.checks import g2_errors as g2
from invigil.checks import g3_supply as g3
from invigil.checks import g4_evidence as g4
from invigil.checks import g5_doors as g5
from invigil.checks import tier1_secrets as t1
from invigil.config import InvigilConfig
from invigil.context import Context
from invigil.model import Status


def ctx(tmp_path: Path) -> Context:
    return Context(repo=tmp_path, config=InvigilConfig.load(tmp_path))


def wf(tmp_path: Path, name: str, body: str) -> None:
    d = tmp_path / ".github" / "workflows"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(body)


# --- G2 -------------------------------------------------------------------
def test_deep_health_skips_for_non_service(tmp_path):
    (tmp_path / "main.py").write_text("print('a cli')\n")
    assert g2.deep_health(ctx(tmp_path)).status is Status.SKIP


def test_deep_health_pass_and_fail_for_service(tmp_path):
    (tmp_path / "app.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n")
    r = g2.deep_health(ctx(tmp_path))
    assert r.status is Status.FAIL and r.fix
    (tmp_path / "sysdeps.py").write_text("# preflight\n")
    assert g2.deep_health(ctx(tmp_path)).status is Status.PASS


def test_error_correlation_id_service(tmp_path):
    (tmp_path / "app.py").write_text("import uvicorn\napp.add_exception_handler(500, h)\nerror_id = uuid4()\n")
    assert g2.error_correlation_id(ctx(tmp_path)).status is Status.PASS


# --- G3 -------------------------------------------------------------------
def test_smoke_published_needs_schedule(tmp_path):
    wf(tmp_path, "smoke-published.yml", "name: smoke\non:\n  schedule:\n    - cron: '0 3 * * *'\n")
    assert g3.smoke_published(ctx(tmp_path)).status is Status.PASS
    wf(tmp_path, "smoke-published.yml", "name: smoke\non:\n  push:\n")
    assert g3.smoke_published(ctx(tmp_path)).status is Status.FAIL


def test_actions_sha_pinned_detects_tags(tmp_path):
    wf(tmp_path, "ci.yml", "jobs:\n  x:\n    steps:\n      - uses: actions/checkout@v4\n")
    r = g3.actions_sha_pinned(ctx(tmp_path))
    assert r.status is Status.FAIL and "checkout" in r.detail
    sha = "a" * 40
    wf(tmp_path, "ci.yml", f"jobs:\n  x:\n    steps:\n      - uses: actions/checkout@{sha}\n")
    assert g3.actions_sha_pinned(ctx(tmp_path)).status is Status.PASS


def test_actions_sha_pinned_ignores_local(tmp_path):
    wf(tmp_path, "ci.yml", "jobs:\n  x:\n    steps:\n      - uses: ./\n")
    assert g3.actions_sha_pinned(ctx(tmp_path)).status is Status.PASS


def test_actions_sha_pinned_ignores_commented_examples(tmp_path):
    sha = "a" * 40
    body = (
        "# usage:\n#   uses: org/repo/.github/workflows/reusable.yml@v1\n"
        f"jobs:\n  x:\n    steps:\n      - uses: actions/checkout@{sha}\n"
    )
    wf(tmp_path, "reusable.yml", body)
    assert g3.actions_sha_pinned(ctx(tmp_path)).status is Status.PASS


def test_actions_sha_pinned_accepts_quoted_pin(tmp_path):
    sha = "b" * 40
    wf(tmp_path, "ci.yml", f'jobs:\n  x:\n    steps:\n      - uses: "actions/checkout@{sha}"\n')
    assert g3.actions_sha_pinned(ctx(tmp_path)).status is Status.PASS


def test_lockfile_and_coverage_and_matrix(tmp_path):
    wf(
        tmp_path,
        "ci.yml",
        "run: uv sync --locked\nrun: pytest --cov-fail-under=80\nstrategy:\n  matrix:\n    py: [3.11]\n",
    )
    c = ctx(tmp_path)
    assert g3.lockfile_enforced(c).status is Status.PASS
    assert g3.coverage_gate(c).status is Status.PASS
    assert g3.version_matrix(c).status is Status.PASS


def test_dependabot(tmp_path):
    assert g3.dependabot(ctx(tmp_path)).status is Status.FAIL
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "dependabot.yml").write_text("version: 2\n")
    assert g3.dependabot(ctx(tmp_path)).status is Status.PASS


# --- G4 -------------------------------------------------------------------
def test_scorecard_score_skips_without_remote(tmp_path):
    assert g4.scorecard_score(ctx(tmp_path)).status is Status.SKIP


def test_signed_releases_sbom(tmp_path):
    wf(tmp_path, "release.yml", "run: cosign sign-blob\nrun: syft . -o spdx-json\n")
    assert g4.signed_releases_sbom(ctx(tmp_path)).status is Status.PASS
    wf(tmp_path, "release.yml", "run: python -m build\n")
    assert g4.signed_releases_sbom(ctx(tmp_path)).status is Status.FAIL


def test_security_and_changelog(tmp_path):
    assert g4.security_policy(ctx(tmp_path)).status is Status.FAIL
    (tmp_path / "SECURITY.md").write_text("report to x\n")
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n")
    assert g4.security_policy(ctx(tmp_path)).status is Status.PASS
    assert g4.changelog(ctx(tmp_path)).status is Status.PASS


# --- G5 -------------------------------------------------------------------
def test_g5_doors(tmp_path):
    c = ctx(tmp_path)
    assert g5.contributor_door(c).status is Status.FAIL
    assert g5.ai_door(c).status is Status.FAIL
    (tmp_path / "CONTRIBUTING.md").write_text("dev setup\n")
    (tmp_path / "AGENTS.md").write_text("build/test\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "README.md").write_text("index\n")
    assert g5.contributor_door(ctx(tmp_path)).status is Status.PASS
    assert g5.ai_door(ctx(tmp_path)).status is Status.PASS
    assert g5.docs_index(ctx(tmp_path)).status is Status.PASS


# Regression: ai-door used to accept only llms.txt / AGENTS.md, so a repo with a
# CLAUDE.md (microsoft/playwright-python) was simultaneously "has agent context"
# to agents-md-actionable and "has no AI door" to ai-door. Two checks in one group
# must not disagree about what an agent door is.
@pytest.mark.parametrize("name", ["CLAUDE.md", "AGENTS.md", "llms.txt", ".cursorrules"])
def test_ai_door_accepts_every_agent_context_file(tmp_path, name):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("agent context\n")
    r = g5.ai_door(ctx(tmp_path))
    assert r.status is Status.PASS
    assert name in r.detail


def test_ai_door_agrees_with_agents_md_actionable(tmp_path):
    # The shared constant is the contract: whatever ai_native treats as agent
    # context, ai-door must count as a door.
    for name in ai_native.AGENT_CONTEXT_FILES:
        assert name in g5.AI_DOOR_FILES, f"{name} is agent context but not an AI door"


def test_good_first_issues_skips_without_remote(tmp_path):
    assert g5.good_first_issues(ctx(tmp_path)).status is Status.SKIP


# --- Tier-1 secrets -------------------------------------------------------
def _git(tmp_path, *args):
    subprocess.run(["git", *args], cwd=tmp_path, capture_output=True, check=False)


def test_no_tracked_secrets(tmp_path):
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "t@t.t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "app.py").write_text("x = 1\n")
    _git(tmp_path, "add", "app.py")
    assert t1.no_tracked_secrets(ctx(tmp_path)).status is Status.PASS
    (tmp_path / "server.key").write_text("PRIVATE KEY\n")
    _git(tmp_path, "add", "server.key")
    r = t1.no_tracked_secrets(ctx(tmp_path))
    assert r.status is Status.FAIL and "server.key" in r.detail


def test_public_key_is_allowed(tmp_path):
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "t@t.t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "id_rsa.pub").write_text("ssh-rsa AAAA\n")
    _git(tmp_path, "add", "id_rsa.pub")
    assert t1.no_tracked_secrets(ctx(tmp_path)).status is Status.PASS


def _repo_with(tmp_path, rel, body):
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "t@t.t")
    _git(tmp_path, "config", "user.name", "t")
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)
    _git(tmp_path, "add", "-A")
    return ctx(tmp_path)


# Regression: `.pem` is the extension for certificates and CSRs too. Invigil
# reported microsoft/playwright-python as tracking secrets when the files were
# published certificates. Accusing a project of leaking what it deliberately
# published is the most damaging thing this tool can get wrong.
@pytest.mark.parametrize(
    "armour",
    ["-----BEGIN CERTIFICATE-----", "-----BEGIN CERTIFICATE REQUEST-----", "-----BEGIN PUBLIC KEY-----"],
)
def test_public_pem_material_is_not_a_secret(tmp_path, armour):
    c = _repo_with(tmp_path, "certs/server_cert.pem", f"{armour}\nMIIB\n")
    assert t1.no_tracked_secrets(c).status is Status.PASS


# Regression: aws/aws-cli tracks tests/functional/ec2/testcli.pem — a throwaway
# RSA key a TLS test suite cannot exist without. Worth surfacing, but "rotate the
# key and scrub history" is wrong advice and blocker severity collapsed the gate.
@pytest.mark.parametrize("rel", ["tests/functional/ec2/testcli.pem", "test/fixtures/key.pem", "e2e/certs/client.key"])
def test_private_key_under_a_test_path_warns_not_fails(tmp_path, rel):
    c = _repo_with(tmp_path, rel, "-----BEGIN RSA PRIVATE KEY-----\nMIIE\n")
    r = t1.no_tracked_secrets(c)
    assert r.status is Status.WARN
    assert r.fix  # still tells you what to do either way


def test_private_key_outside_tests_still_fails(tmp_path):
    c = _repo_with(tmp_path, "deploy/id_rsa", "-----BEGIN OPENSSH PRIVATE KEY-----\nb3Bl\n")
    r = t1.no_tracked_secrets(c)
    assert r.status is Status.FAIL and "id_rsa" in r.detail


def test_unreadable_keystore_is_still_treated_as_a_secret(tmp_path):
    # Binary keystores cannot be content-classified; absence of proof is not proof
    # of absence, so they keep failing.
    c = _repo_with(tmp_path, "app.keystore", "\x00\x01binary")
    assert t1.no_tracked_secrets(c).status is Status.FAIL
