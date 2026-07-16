"""Scoring math + gate-level semantics."""

from invigil.model import Check, CheckResult, Scorecard, Status


def _r(gate, status, weight=1, mandatory=True, cid="x"):
    return CheckResult(Check(id=cid, gate=gate, title=cid, weight=weight, mandatory=mandatory), status)


def test_percent_and_grade():
    sc = Scorecard("r", [_r("G1", Status.PASS), _r("G1", Status.PASS), _r("G1", Status.FAIL)])
    assert sc.earned == 2
    assert sc.possible == 3
    assert round(sc.percent) == 67
    assert sc.grade() == "C-"


def test_skip_is_excluded_from_possible():
    sc = Scorecard("r", [_r("G1", Status.PASS), _r("G1", Status.SKIP)])
    assert sc.possible == 1
    assert sc.percent == 100.0
    assert sc.grade() == "A+"


def test_gate_level_is_contiguous():
    # G1 clean, G2 clean, G3 has a failing mandatory -> stops at G2.
    sc = Scorecard(
        "r",
        [
            _r("G1", Status.PASS),
            _r("G2", Status.PASS),
            _r("G3", Status.FAIL),
            _r("G4", Status.PASS),  # passing G4 must NOT rescue the gate past the G3 break
        ],
    )
    assert sc.gate_level() == "G2"


def test_non_mandatory_failure_does_not_lower_gate():
    sc = Scorecard("r", [_r("G1", Status.PASS), _r("G2", Status.FAIL, mandatory=False)])
    assert sc.gate_level() == "G2"


def test_failing_g1_yields_no_gate():
    sc = Scorecard("r", [_r("G1", Status.FAIL)])
    assert sc.gate_level() == "—"
