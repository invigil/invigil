"""S2 — error-path tests: verify the gate's own failure modes are surfaced correctly.

These tests satisfy the `error-path-tests` check (which looks for test_error*.py)
and prove the gate practices what it preaches: every failure mode produces a
clear, actionable result rather than an opaque crash.
"""

from __future__ import annotations

from invigil.checks import run_all
from invigil.cli import main
from invigil.config import InvigilConfig
from invigil.context import Context
from invigil.model import Check, CheckResult, Scorecard, Status

# ---------------------------------------------------------------------------
# 1. A check that raises an exception → WARN result, never crashes run_all
# ---------------------------------------------------------------------------

def test_crashing_check_produces_warn_not_exception(tmp_path):
    """run_all must never propagate an exception from a check function."""
    from invigil.checks import REGISTRY as _REG

    def boom(ctx: Context) -> CheckResult:
        raise RuntimeError("simulated check failure")

    bad_check = Check(id="test-boom", gate="G1", title="Boom", layer="local", group="layout")
    _REG.append((bad_check, boom))
    try:
        ctx = Context(repo=tmp_path, config=InvigilConfig())
        results = run_all(ctx)
        boom_results = [r for r in results if r.check.id == "test-boom"]
        assert len(boom_results) == 1
        assert boom_results[0].status == Status.WARN
        assert "check errored" in boom_results[0].detail
    finally:
        _REG.pop()


# ---------------------------------------------------------------------------
# 2. --enforce with gate below target → exit 1
# ---------------------------------------------------------------------------

def test_enforce_exits_1_when_below_gate(tmp_path):
    """--enforce flag must exit non-zero when gate is below --min-gate."""
    result = main(["score", str(tmp_path), "--enforce", "--min-gate", "G4"])
    assert result == 1


# ---------------------------------------------------------------------------
# 3. invigil score on non-existent path → exit 2 with message
# ---------------------------------------------------------------------------

def test_missing_path_exits_2(capsys):
    result = main(["score", "/no/such/path/xyz"])
    assert result == 2
    captured = capsys.readouterr()
    assert "not found" in captured.err


# ---------------------------------------------------------------------------
# 4. Every FAIL result carries a non-empty fix string (D2 on the gate itself)
# ---------------------------------------------------------------------------

def test_all_fail_results_have_fix_strings(tmp_path):
    """A FAIL without a fix is a bug — check D2 on the gate itself."""
    ctx = Context(repo=tmp_path, config=InvigilConfig())
    results = run_all(ctx, offline=True)
    failures = [r for r in results if r.status == Status.FAIL]
    missing_fix = [r for r in failures if not r.fix.strip()]
    assert missing_fix == [], (
        "These checks FAIL without providing a fix message:\n"
        + "\n".join(f"  {r.check.id}: {r.check.title}" for r in missing_fix)
    )


# ---------------------------------------------------------------------------
# 5. --fix under CI → exit 3 (CI-lockout)
# ---------------------------------------------------------------------------

def test_fix_under_ci_exits_3(tmp_path, monkeypatch):
    """--fix must refuse to run when CI=true (prevents cascading auto-commits)."""
    monkeypatch.setenv("CI", "true")
    result = main(["score", str(tmp_path), "--fix"])
    assert result == 3


# ---------------------------------------------------------------------------
# 6. Blocker check that FAILs collapses gate_level to "—"
# ---------------------------------------------------------------------------

def test_blocker_fail_collapses_gate():
    """A severity=blocker FAIL must return '—' regardless of other passes."""
    blocker = Check(id="b", gate="G1", title="Blocker", severity="blocker")
    passer = Check(id="p", gate="G3", title="Passer")
    sc = Scorecard(
        repo="test",
        results=[
            CheckResult(blocker, Status.FAIL, "oops", "fix it"),
            CheckResult(passer, Status.PASS, "ok"),
        ],
    )
    assert sc.gate_level() == "—"


# ---------------------------------------------------------------------------
# 7. invigil check <group> exits 1 on failures, 0 on pass
# ---------------------------------------------------------------------------

def test_check_group_exits_nonzero_on_failures(tmp_path):
    """invigil check layout must exit 1 when layout checks fail."""
    result = main(["check", "layout", str(tmp_path)])
    assert result == 1  # tmp_path has no README, LICENSE etc.


def test_check_group_exits_0_on_clean_secrets(tmp_path):
    """invigil check secrets on a repo with no secrets should exit 0.

    secrets group: no-tracked-secrets (needs git), gitleaks (needs binary)
    Both degrade to SKIP on a non-git tmp_path -> no failures -> exit 0.
    """
    result = main(["check", "secrets", str(tmp_path)])
    assert result == 0
