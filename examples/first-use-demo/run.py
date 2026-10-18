"""Run a real, offline broken/fixed wheel demonstration using the local Invigil."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

PACKAGE = "hello_firstuse"
VERSION = "1.0"
GREETING = "Hello from the installed wheel!"
MODULE = (
    "from importlib.resources import files\n\n"
    "def hello():\n"
    "    return files(__package__).joinpath('greeting.txt').read_text().strip()\n"
)
COMMAND = ["python", "-c", "from hello_firstuse import hello; print(hello())"]


def build_fixture(directory: Path, *, include_data: bool) -> Path:
    """Construct a tiny valid wheel directly: no build backend or network needed."""
    info = f"{PACKAGE}-{VERSION}.dist-info"
    contents = {
        f"{PACKAGE}/__init__.py": MODULE,
        f"{info}/METADATA": f"Metadata-Version: 2.1\nName: hello-firstuse\nVersion: {VERSION}\n",
        f"{info}/WHEEL": "Wheel-Version: 1.0\nGenerator: invigil-demo\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
    }
    if include_data:
        contents[f"{PACKAGE}/greeting.txt"] = GREETING + "\n"
    manifest = io.StringIO(newline="")
    writer = csv.writer(manifest)
    for name, value in contents.items():
        data = value.encode()
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
        writer.writerow([name, f"sha256={digest}", len(data)])
    writer.writerow([f"{info}/RECORD", "", ""])
    contents[f"{info}/RECORD"] = manifest.getvalue()
    wheel = directory / f"{PACKAGE}-{VERSION}-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, value in contents.items():
            archive.writestr(name, value)
    return wheel


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="invigil-first-use-demo-"))
    print("Invigil demo: source works, but does the installed wheel work?", flush=True)
    print(f"Artifacts and reports: {root}\n", flush=True)

    checkout = root / "checkout"
    package = checkout / PACKAGE
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(MODULE)
    (package / "greeting.txt").write_text(GREETING + "\n")
    source = subprocess.run([sys.executable, *COMMAND[1:]], cwd=checkout, capture_output=True, text=True, timeout=20)
    if source.returncode or source.stdout.strip() != GREETING:
        raise RuntimeError(f"source demonstration failed: {source.stderr}")
    print(f"SOURCE CHECK: PASS — {source.stdout.strip()}", flush=True)

    reports = {}
    for name, include_data, expected_status in [("broken", False, "FAIL"), ("fixed", True, "PASS")]:
        directory = root / name
        directory.mkdir()
        wheel = build_fixture(directory, include_data=include_data)
        config = {
            "artifacts": [
                {
                    "type": "wheel",
                    "path": wheel.name,
                    "wheelhouse": ".",
                    "command": COMMAND,
                    "expect_contains": GREETING,
                }
            ],
            "boot_budget_minutes": 1,
        }
        # JSON is valid YAML; avoid even a fixture-generation dependency.
        (directory / ".invigil.yml").write_text(json.dumps(config, indent=2) + "\n")
        report_path = directory / "report.json"
        invocation = [
            sys.executable,
            "-m",
            "invigil.cli",
            "stranger",
            str(directory),
            "--format",
            "json",
            "--output",
            str(report_path),
        ]
        run = subprocess.run(invocation, cwd=root, capture_output=True, text=True, timeout=90)
        if not report_path.exists():
            raise RuntimeError(f"Invigil produced no report: {run.stderr}")
        report = json.loads(report_path.read_text())
        reports[name] = report
        if run.returncode != (1 if name == "broken" else 0) or report["status"] != expected_status:
            raise RuntimeError(f"unexpected {name} result: {json.dumps(report, indent=2)}\n{run.stderr}")
        result = report["wheels"][0]
        print(f"\n{name.upper()} WHEEL:", flush=True)
        for step in result["steps"]:
            print(f"  {step['name']}: {step['status']}", flush=True)
        if not include_data:
            failure = next((line for line in result["output"].splitlines() if "FileNotFoundError" in line), None)
            if failure is None:
                raise RuntimeError("broken wheel failed for an unexpected reason")
            print(f"  Evidence: {failure}", flush=True)
            print("  Demo fix: include hello_firstuse/greeting.txt in the wheel.", flush=True)
        else:
            print(f"  Output: {result['output'].strip()}", flush=True)
        print(f"  JSON: {report_path}", flush=True)

    (root / "comparison.json").write_text(json.dumps(reports, indent=2) + "\n")
    print("\nDemo passed: both wheels install; only the repaired wheel completes first use.", flush=True)
    print("Synthetic packaging example. No API keys, downloads, model calls, or publishing.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
