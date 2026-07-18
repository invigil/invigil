"""Reporters render every format and always surface the fix."""

import json

from invigil import report
from invigil.model import Check, CheckResult, Scorecard, Status


def _sc():
    ok = CheckResult(Check(id="a", gate="G1", title="LICENSE"), Status.PASS, "LICENSE: Apache-2.0")
    bad = CheckResult(
        Check(id="b", gate="G1", title="README <=300 lines"),
        Status.FAIL,
        detail="640 lines",
        fix="split into docs/",
    )
    return Scorecard("demo", [ok, bad])


def test_text_leads_with_fix():
    out = report.as_text(_sc())
    assert "fix: split into docs/" in out
    assert "Grade:" in out and "Gate:" in out


def test_json_is_valid_and_keyed():
    data = json.loads(report.as_json(_sc()))
    assert data["repo"] == "demo"
    assert {"gate", "grade", "earned", "possible", "percent", "checks"} <= data.keys()
    assert data["checks"][1]["fix"] == "split into docs/"
    assert data["checks"][0]["duration_ms"] == 0.0


def test_markdown_has_failure_table():
    md = report.as_markdown(_sc())
    assert "| Gate | Check | Effort | Why | Fix |" in md
    assert "split into docs/" in md


def test_markdown_all_pass():
    sc = Scorecard("demo", [CheckResult(Check(id="a", gate="G1", title="x"), Status.PASS)])
    assert "All doctrine checks pass" in report.as_markdown(sc)


def test_badge_shape_and_color():
    badge = json.loads(report.as_badge(_sc()))
    assert badge["schemaVersion"] == 1
    assert badge["label"] == "invigil"
    assert badge["color"] in {"brightgreen", "green", "yellow", "orange", "red"}


def _ai_sc():
    def res(id_, status):
        return CheckResult(Check(id=id_, gate="G5", title=id_, group="ai"), status)

    return Scorecard(
        "demo",
        [
            res("llms-txt-shape", Status.PASS),
            res("agents-md-actionable", Status.PASS),
            res("agent-context-fresh", Status.FAIL),
            res("exit-codes-documented", Status.SKIP),  # excluded from applicable
            CheckResult(Check(id="license-present", gate="G1", title="x"), Status.PASS),  # not group ai
        ],
    )


def test_ai_readiness_counts_group_ai_only():
    assert _ai_sc().ai_readiness() == (2, 3)


def test_ai_badge_shape():
    badge = json.loads(report.as_ai_badge(_ai_sc()))
    assert badge["label"] == "ai-ready"
    assert badge["message"] == "2/3 agent-legible"
    assert badge["color"] == "yellow"  # 66% -> between 50 and 80


def test_ai_badge_na_when_nothing_applicable():
    sc = Scorecard("demo", [CheckResult(Check(id="a", gate="G1", title="x"), Status.PASS)])
    assert json.loads(report.as_ai_badge(sc))["message"] == "n/a"


def test_llm_format_is_terse_and_stable():
    out = report.as_llm(_sc())
    lines = out.splitlines()
    assert lines[0].startswith("invigil repo=demo gate=")
    assert "ai_ready=" in lines[0]
    assert lines[1] == "FAIL b | 640 lines | fix: split into docs/"
    assert lines[-1].startswith("summary pass=1 fail=1")
    assert len(out) < 1024  # context-budget honesty


def test_llm_format_healthy_repo_is_two_lines():
    sc = Scorecard("demo", [CheckResult(Check(id="a", gate="G1", title="x"), Status.PASS)])
    assert len(report.as_llm(sc).splitlines()) == 2
