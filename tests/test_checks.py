from types import SimpleNamespace

from invigil import checks
from invigil.model import Check, CheckResult, Status


def test_run_all_records_callback_duration(monkeypatch, tmp_path):
    check = Check(id="timed", gate="G1", title="timed check")

    def run(_ctx):
        return CheckResult(check, Status.PASS)

    monkeypatch.setattr("invigil.manager.build_registry", lambda _repo: ([(check, run)], []))
    ticks = iter([10.0, 10.01234])
    monkeypatch.setattr(checks, "perf_counter", lambda: next(ticks))
    ctx = SimpleNamespace(
        repo=tmp_path,
        config=SimpleNamespace(disabled_checks=[]),
    )

    result = checks.run_all(ctx)[0]

    assert result.duration_ms == 12.34
