"""Real offline installs of broken/fixed wheels, not mocked pip outcomes."""

import csv
import io
import sys
import zipfile
from pathlib import Path

import pytest

from invigil.wheel_check import verify_wheel


def make_wheel(root: Path, files: dict[str, str], *, requires: str = "") -> Path:
    wheel = root / "firstuse_demo-1.0-py3-none-any.whl"
    info = "firstuse_demo-1.0.dist-info"
    contents = {
        f"{info}/METADATA": f"Metadata-Version: 2.1\nName: firstuse-demo\nVersion: 1.0\n{requires}\n",
        f"{info}/WHEEL": "Wheel-Version: 1.0\nGenerator: invigil-tests\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        **files,
    }
    record = io.StringIO()
    writer = csv.writer(record)
    for name in [*contents, f"{info}/RECORD"]:
        writer.writerow((name, "", ""))
    contents[f"{info}/RECORD"] = record.getvalue()
    with zipfile.ZipFile(wheel, "w") as archive:
        for name, content in contents.items():
            archive.writestr(name, content)
    return wheel


@pytest.mark.parametrize("defect", ["module", "resource", "entrypoint", "dependency"])
@pytest.mark.parametrize("fixed", [False, True])
def test_broken_and_fixed_artifacts(tmp_path, monkeypatch, defect, fixed):
    files = {"firstuse_demo/__init__.py": ""}
    command = ["python", "-c", "import firstuse_demo; print('verified')"]
    if defect == "module" and not fixed:
        files.clear()
    elif defect == "resource":
        command = [
            "python",
            "-c",
            "from importlib.resources import files; print(files('firstuse_demo').joinpath('data.txt').read_text())",
        ]
        if fixed:
            files["firstuse_demo/data.txt"] = "verified"
    elif defect == "entrypoint":
        command = ["firstuse-demo"]
        files["firstuse_demo/__init__.py"] = "def main():\n    print('verified')\n"
        if fixed:
            files["firstuse_demo-1.0.dist-info/entry_points.txt"] = (
                "[console_scripts]\nfirstuse-demo = firstuse_demo:main\n"
            )
    elif defect == "dependency":
        files["firstuse_demo/__init__.py"] = "import missing_dependency\n"
        if fixed:
            files["missing_dependency.py"] = "# bundled replacement for the fixture dependency\n"
    wheel = make_wheel(tmp_path, files)
    # A working checkout and inherited PYTHONPATH must not rescue a broken wheel.
    (tmp_path / "firstuse_demo").mkdir()
    (tmp_path / "firstuse_demo" / "__init__.py").write_text("")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYTHONPATH", str(tmp_path))
    result = verify_wheel(
        {"path": wheel.name, "command": command, "expect_contains": "verified", "wheelhouse": "."},
        tmp_path,
        60,
    )
    assert result.status == ("PASS" if fixed else "FAIL"), result
    assert result.phase == "first-use"
    assert len(result.sha256) == 64
    assert "installation" in result.phases


def test_missing_dependency_is_installation_error(tmp_path):
    wheel = make_wheel(tmp_path, {}, requires="Requires-Dist: nonexistent-invigil-test-dependency==1.0")
    result = verify_wheel({"path": wheel.name, "command": ["python"], "wheelhouse": "."}, tmp_path, 60)
    assert result.status == "ERROR"
    assert result.phase == "installation"
    assert "first-use" not in result.phases


@pytest.mark.parametrize(
    "override",
    [
        {"command": []},
        {"command": "python"},
        {"command": [sys.executable]},
        {"path": "*.whl"},
        {"env": {"PYTHONPATH": "."}},
        {"wheelhouse": "missing"},
    ],
)
def test_invalid_configuration(tmp_path, override):
    wheel = make_wheel(tmp_path, {})
    result = verify_wheel({"path": wheel.name, "command": ["python"], **override}, tmp_path, 60)
    assert result.status == "ERROR"
    assert result.phase == "configuration"


def test_clean_environment_and_cleanup(tmp_path, monkeypatch):
    wheel = make_wheel(tmp_path, {})
    monkeypatch.setenv("INVIGIL_HOST_SECRET", "not-for-artifacts")
    command = [
        "python",
        "-c",
        (
            "import os,sys; assert 'INVIGIL_HOST_SECRET' not in os.environ; "
            "assert os.environ['EXPLICIT_VALUE'] == 'provided'; print(sys.prefix)"
        ),
    ]
    result = verify_wheel(
        {
            "path": wheel.name,
            "command": command,
            "wheelhouse": ".",
            "env": {"EXPLICIT_VALUE": "provided"},
        },
        tmp_path,
        60,
    )
    assert result.status == "PASS", result
    assert not Path(result.output.strip()).exists()


def test_first_use_timeout(tmp_path):
    wheel = make_wheel(tmp_path, {})
    result = verify_wheel(
        {
            "path": wheel.name,
            "command": ["python", "-c", "import time; print('started', flush=True); time.sleep(120)"],
            "wheelhouse": ".",
        },
        tmp_path,
        10,
    )
    assert result.status == "ERROR"
    assert "time budget" in result.detail
    assert result.steps[-1].status == "ERROR"
    assert "started" in result.steps[-1].output


def test_expected_output_is_required(tmp_path):
    wheel = make_wheel(tmp_path, {})
    result = verify_wheel(
        {
            "path": wheel.name,
            "command": ["python", "-c", "print('wrong')"],
            "expect_contains": "verified",
            "wheelhouse": ".",
        },
        tmp_path,
        60,
    )
    assert result.status == "FAIL"
    assert "expected text" in result.detail


def test_cli_resolves_wheel_relative_to_config(tmp_path, monkeypatch, capsys):
    from invigil.cli import main

    repo = tmp_path / "repo"
    repo.mkdir()
    wheel = make_wheel(repo, {"firstuse_demo/__init__.py": ""})
    (repo / ".invigil.yml").write_text(
        f"artifacts:\n  - type: wheel\n    path: {wheel.name}\n    wheelhouse: .\n"
        "    command: [python, '-c', 'import firstuse_demo; print(42)']\n    expect_contains: '42'\n"
    )
    monkeypatch.chdir(tmp_path)
    assert main(["stranger", str(repo)]) == 0
    assert "PASS" in capsys.readouterr().out


def test_json_report_preserves_failure_and_not_run(tmp_path, capsys):
    import json

    from invigil.cli import main

    wheel = make_wheel(tmp_path, {})
    (tmp_path / ".invigil.yml").write_text(
        f"artifacts:\n  - type: wheel\n    path: {wheel.name}\n    wheelhouse: .\n"
        "    command: [python, '-c', 'print(42)']\n    expect_contains: 'missing'\n"
        "  - type: wheel\n    path: later.whl\n    command: [python, '--version']\n"
    )
    assert main(["stranger", str(tmp_path), "--format", "json"]) == 1
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert report["schema_version"] == 1
    assert report["status"] == "FAIL"
    failed, skipped = report["wheels"]
    assert failed["steps"][-1]["status"] == "FAIL"
    assert failed["steps"][-1]["returncode"] == 0
    assert failed["dependencies"]
    assert failed["duration_seconds"] > 0
    assert skipped["status"] == "NOT_RUN"
    assert all(step["status"] == "NOT_RUN" for step in skipped["steps"])
    assert "sha256" in captured.err


def test_report_file_on_configuration_failure(tmp_path, capsys):
    import json

    from invigil.cli import main

    (tmp_path / ".invigil.yml").write_text("artifacts: []\n")
    output = tmp_path / "report.json"
    assert main(["stranger", str(tmp_path), "--format", "json", "--output", str(output)]) == 1
    assert json.loads(output.read_text())["status"] == "ERROR"
    assert not capsys.readouterr().out
    assert main(["stranger", str(tmp_path), "--output", str(tmp_path / "absent" / "report")]) == 2


def test_explicit_values_redacted_in_report(tmp_path):
    import json
    from dataclasses import asdict

    wheel = make_wheel(tmp_path, {})
    secret = "sentinel-secret-12345"
    result = verify_wheel(
        {
            "path": wheel.name,
            "wheelhouse": ".",
            "env": {"TOKEN": secret},
            "command": ["python", "-c", f"print('{secret}')"],
        },
        tmp_path,
        60,
    )
    assert result.status == "PASS"
    assert secret not in json.dumps(asdict(result))
    assert "[redacted]" in result.output
