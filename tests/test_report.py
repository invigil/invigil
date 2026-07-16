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


def test_markdown_has_failure_table():
    md = report.as_markdown(_sc())
    assert "| Gate | Check | Why | Fix |" in md
    assert "split into docs/" in md


def test_markdown_all_pass():
    sc = Scorecard("demo", [CheckResult(Check(id="a", gate="G1", title="x"), Status.PASS)])
    assert "All doctrine checks pass" in report.as_markdown(sc)


def test_badge_shape_and_color():
    badge = json.loads(report.as_badge(_sc()))
    assert badge["schemaVersion"] == 1
    assert badge["label"] == "invigil"
    assert badge["color"] in {"brightgreen", "green", "yellow", "orange", "red"}
