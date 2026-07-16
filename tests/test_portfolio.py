"""Portfolio table building + marker-block replacement (C5)."""

from invigil import portfolio
from invigil.model import Check, CheckResult, Scorecard, Status


def _sc(repo, results):
    return Scorecard(repo, results)


def _pass(gate="G1"):
    return CheckResult(Check(id="p", gate=gate, title="ok"), Status.PASS)


def _fail(title):
    return CheckResult(Check(id="f", gate="G4", title=title), Status.FAIL, "why", "fix")


def test_build_table_sorted_by_score():
    a = _sc("low", [_pass(), _fail("x"), _fail("y")])
    b = _sc("high", [_pass(), _pass()])
    table = portfolio.build_table([a, b], "2026-07-16")
    assert portfolio.START in table and portfolio.END in table
    # higher score sorts first
    assert table.index("**high**") < table.index("**low**")
    assert "2026-07-16" in table


def test_top_gaps_truncates():
    sc = _sc("r", [_fail("a"), _fail("b"), _fail("c")])
    gaps = portfolio._top_gaps(sc, n=2)
    assert "a; b" in gaps and "+1 more" in gaps


def test_top_gaps_none():
    assert portfolio._top_gaps(_sc("r", [_pass()])) == "—"


def test_update_block_replaces_between_markers():
    doc = f"# Title\n\n{portfolio.START}\nOLD\n{portfolio.END}\n\nfooter\n"
    new = portfolio.build_table([_sc("r", [_pass()])], "2026-07-16")
    out = portfolio.update_block(doc, new)
    assert "OLD" not in out
    assert "# Title" in out and "footer" in out
    assert out.count(portfolio.START) == 1  # not duplicated


def test_update_block_appends_when_absent():
    doc = "# Title\n\nno markers here\n"
    new = portfolio.build_table([_sc("r", [_pass()])], "2026-07-16")
    out = portfolio.update_block(doc, new)
    assert "no markers here" in out and portfolio.START in out
