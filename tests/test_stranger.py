"""Stranger Gate pure logic: probe parsing, evaluation, URL resolution, budget.

The docker/pip orchestration shells out and is exercised in real CI, not here;
these tests pin the logic that decides pass/fail so it can't regress.
"""

import pytest

from invigil import stranger
from invigil.config import InvigilConfig
from invigil.stranger import Probe, StrangerError, resolve_url, run, run_probes


def test_probe_from_dict():
    p = Probe.from_dict({"url": "/api/x", "auth": "a:b", "expect_json_count": {"min": 18}})
    assert p.url == "/api/x" and p.auth == "a:b" and p.expect_json_count_min == 18
    assert p.expect_status == 200


def test_evaluate_status():
    p = Probe(url="/", expect_status=200)
    assert p.evaluate(200, "")[0] is True
    ok, detail = p.evaluate(500, "")
    assert ok is False and "500" in detail


def test_evaluate_contains():
    p = Probe(url="/login", expect_contains="kaaval")
    assert p.evaluate(200, "<h1>Kaaval</h1>".lower())[0] is True
    assert p.evaluate(200, "<h1>other</h1>")[0] is False


def test_evaluate_json_count():
    p = Probe(url="/api", expect_json_count_min=18)
    assert p.evaluate(200, "[" + ",".join(["1"] * 20) + "]")[0] is True
    assert p.evaluate(200, "[1,2,3]")[0] is False
    ok, detail = p.evaluate(200, "not json")
    assert ok is False and "JSON" in detail


def test_resolve_url():
    assert resolve_url("http://127.0.0.1:3000/login", None) == "http://127.0.0.1:3000/login"
    assert resolve_url("/api", 8000) == "http://127.0.0.1:8000/api"
    with pytest.raises(StrangerError):
        resolve_url("/api", None)


def test_run_probes_all_pass(monkeypatch):
    monkeypatch.setattr(stranger, "_fetch", lambda url, auth, timeout=5.0: (200, "[1,2,3]"))
    run_probes([Probe(url="/", expect_status=200), Probe(url="/api", expect_json_count_min=3)], 8000, 60)


def test_run_probes_reports_failure(monkeypatch):
    monkeypatch.setattr(stranger, "_fetch", lambda url, auth, timeout=5.0: (200, "[1]"))
    with pytest.raises(StrangerError) as e:
        run_probes([Probe(url="/api", expect_json_count_min=18)], 8000, 60)
    assert "json count" in str(e.value)


def test_run_probes_budget_timeout(monkeypatch):
    def boom(url, auth, timeout=5.0):
        raise OSError("connection refused")

    monkeypatch.setattr(stranger, "_fetch", boom)
    # budget 0 -> the readiness loop never runs, so it fails fast with the D1 message
    with pytest.raises(StrangerError) as e:
        run_probes([Probe(url="/")], 8000, 0)
    assert "did not serve" in str(e.value)


def test_run_requires_artifacts():
    with pytest.raises(StrangerError):
        run(InvigilConfig(name="x"))


def test_run_orchestration_happy_path(monkeypatch):
    """Boot a ghcr artifact + service and probe it, with docker/http mocked."""
    import subprocess

    calls = []

    def fake_run(*cmd, check=True):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(stranger, "_run", fake_run)
    monkeypatch.setattr(stranger, "_fetch", lambda url, auth, timeout=5.0: (200, "ok"))

    cfg = InvigilConfig(
        name="demo",
        services={"postgres": {"image": "postgres:16-alpine", "env": {"POSTGRES_DB": "d"}, "ports": ["5432:5432"]}},
        artifacts=[{"type": "ghcr", "image": "ghcr.io/demo/app:edge", "port": 8000, "env": {"TOKEN": "smoke"}}],
        probes=[{"url": "/", "expect_status": 200}],
        boot_budget_minutes=1,
    )
    run(cfg)  # must not raise
    # docker run for the service and the artifact both happened; teardown ran.
    assert any("postgres:16-alpine" in c for c in calls)
    assert any("ghcr.io/demo/app:edge" in c for c in calls)
    assert any("rm" in c for c in calls)  # _teardown
