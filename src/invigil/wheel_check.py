"""First-use checks of local wheels, in a fresh environment outside the checkout.

This isolates Python dependencies, not hostile code. Run untrusted artifacts in
disposable CI workers without credentials.
"""

from __future__ import annotations

import codecs
import hashlib
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PhaseResult:
    name: str
    status: str = "NOT_RUN"
    returncode: int | None = None
    duration_seconds: float = 0
    output: str = ""


@dataclass
class WheelResult:
    artifact: str
    sha256: str = ""
    status: str = "ERROR"
    phase: str = "configuration"
    detail: str = ""
    output: str = ""
    fix: str = "Correct the wheel path and first-use command in .invigil.yml, then rerun invigil stranger."
    phases: list[str] = field(default_factory=list)
    steps: list[PhaseResult] = field(
        default_factory=lambda: [
            PhaseResult(name) for name in ("environment", "installation", "inventory", "first-use")
        ]
    )
    command: list[str] = field(default_factory=list)
    python_version: str = field(default_factory=platform.python_version)
    platform: str = field(default_factory=platform.platform)
    dependencies: list[dict[str, str]] = field(default_factory=list)
    duration_seconds: float = 0


def verify_wheel(artifact: dict, repo: Path, budget_seconds: float) -> WheelResult:
    """Install and exercise a wheel. All subprocesses share one time budget."""
    result = WheelResult(artifact=str(artifact.get("path", "")))
    started = time.monotonic()
    try:
        if os.name != "posix":
            raise ValueError("wheel verification currently requires a POSIX worker")
        path = artifact.get("path")
        if not isinstance(path, str) or not path:
            raise ValueError("wheel artifact requires an explicit path")
        wheel = (repo / path).resolve()
        if wheel.suffix != ".whl" or not wheel.is_file():
            raise ValueError("path must identify one existing .whl file (no glob)")
        command = artifact.get("command")
        if not isinstance(command, list) or not command or any(not isinstance(v, str) for v in command):
            raise ValueError("wheel artifact requires a nonempty command argv list")
        if not command[0] or "/" in command[0] or "\\" in command[0]:
            raise ValueError("command must name python or a console script installed in the new environment")
        result.command = list(command)
        expected = artifact.get("expect_contains")
        if expected is not None and not isinstance(expected, str):
            raise ValueError("expect_contains must be a string")
        extra_env = artifact.get("env", {})
        if not isinstance(extra_env, dict) or any(
            not isinstance(k, str) or not isinstance(v, str) for k, v in extra_env.items()
        ):
            raise ValueError("env must map names to strings")
        protected = {"PATH", "HOME", "VIRTUAL_ENV", "LD_PRELOAD", "LD_LIBRARY_PATH"}
        if any(k in protected or k.startswith(("PYTHON", "PIP", "DYLD_")) for k in extra_env):
            raise ValueError("env cannot override Python, pip, loader or environment isolation settings")
        if budget_seconds <= 0:
            raise ValueError("boot budget must be positive")
        wheelhouse = artifact.get("wheelhouse")
        if wheelhouse is not None:
            if not isinstance(wheelhouse, str) or not (repo / wheelhouse).is_dir():
                raise ValueError("wheelhouse must identify an existing directory")
            wheelhouse = str((repo / wheelhouse).resolve())

        deadline = time.monotonic() + budget_seconds
        with tempfile.TemporaryDirectory(prefix="invigil-wheel-") as directory:
            root = Path(directory)
            work = root / "work"
            work.mkdir()
            home = root / "home"
            home.mkdir()
            candidate = root / wheel.name
            shutil.copyfile(wheel, candidate)
            with candidate.open("rb") as source:
                result.sha256 = hashlib.file_digest(source, "sha256").hexdigest()
            scripts = root / "venv" / "bin"
            env = {
                "PATH": os.pathsep.join((str(scripts), os.defpath)),
                "HOME": str(home),
                "LANG": "C.UTF-8",
                "PYTHONNOUSERSITE": "1",
                "PIP_CONFIG_FILE": os.devnull,
                "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                "PIP_NO_INPUT": "1",
            }

            def execute(phase: str, args: list[str], child_env: dict) -> bool:
                result.phase = phase
                result.fix = {
                    "environment": "Install Python venv/ensurepip support, then rerun invigil stranger.",
                    "inventory": "Inspect the dependency inventory failure and rerun verification.",
                    "installation": "Inspect the install output; correct the wheel or dependency source, then rerun.",
                    "first-use": "Correct the first-use operation or packaged files, rebuild the wheel, and rerun.",
                }[phase]
                step = next(step for step in result.steps if step.name == phase)
                step.status = "ERROR"
                phase_started = time.monotonic()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("verification exceeded its time budget")
                # Spool output to disk so noisy children do not exhaust RAM.
                timed_out = False
                with tempfile.TemporaryFile() as log:
                    with subprocess.Popen(
                        args, cwd=work, env=child_env, stdout=log, stderr=log, start_new_session=True
                    ) as child:
                        try:
                            code = child.wait(timeout=remaining)
                        except subprocess.TimeoutExpired:
                            timed_out = True
                            code = None
                        finally:
                            # Reap descendants even when the command exits before them.
                            try:
                                os.killpg(child.pid, signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                            child.wait()
                    log.seek(0)
                    # Match expectations over the entire output, with bounded memory.
                    found = expected is None or expected == ""
                    carry = ""
                    decoder = codecs.getincrementaldecoder("utf-8")("replace")
                    tail = ""
                    while chunk := log.read(8192):
                        decoded = decoder.decode(chunk)
                        combined = carry + decoded
                        if expected and expected in combined:
                            found = True
                        carry = combined[-len(expected) :] if expected else ""
                        tail = (tail + decoded)[-16000:]
                    tail += decoder.decode(b"", final=True)
                    for value in extra_env.values():
                        if value:
                            tail = tail.replace(value, "[redacted]")
                    result.output = tail
                    step.output = tail
                    step.returncode = code
                    step.duration_seconds = round(time.monotonic() - phase_started, 3)
                if timed_out:
                    raise TimeoutError("verification exceeded its time budget")
                if code != 0:
                    result.status = "FAIL" if phase == "first-use" else "ERROR"
                    step.status = result.status
                    result.detail = f"{phase} exited {code}"
                    return False
                if phase == "first-use" and not found:
                    result.status = "FAIL"
                    step.status = "FAIL"
                    result.detail = "first-use output did not contain the expected text"
                    return False
                step.status = "PASS"
                result.phases.append(phase)
                return True

            if not execute("environment", [sys.executable, "-I", "-m", "venv", str(root / "venv")], env):
                return result
            install = [str(scripts / "python"), "-I", "-m", "pip", "install", "--no-cache-dir"]
            if wheelhouse:
                install += ["--no-index", "--find-links", wheelhouse]
            if not execute("installation", [*install, str(candidate)], env):
                return result
            inventory = root / "inventory.json"
            inventory_code = (
                "import importlib.metadata as m,json,pathlib,sys; "
                "pathlib.Path(sys.argv[1]).write_text(json.dumps(sorted("
                "[{'name': d.metadata['Name'], 'version': d.version} for d in m.distributions()], "
                "key=lambda d:d['name'])))"
            )
            if not execute("inventory", [str(scripts / "python"), "-I", "-c", inventory_code, str(inventory)], env):
                return result
            if inventory.stat().st_size > 1_000_000:
                raise ValueError("dependency inventory exceeds 1 MB")
            result.dependencies = json.loads(inventory.read_text())
            result.phase = "first-use"
            executable = scripts / command[0]
            if not executable.is_file():
                result.status = "FAIL"
                result.steps[-1].status = "FAIL"
                result.detail = f"console script {command[0]!r} is not installed in the environment"
                result.fix = "Declare the console script in package metadata or correct command[0], rebuild, and rerun."
                return result
            if not execute("first-use", [str(executable), *command[1:]], {**env, **extra_env}):
                return result
            result.status = "PASS"
            result.fix = ""
            result.detail = "installed wheel completed the declared first-use check"
    except (ValueError, OSError, TimeoutError) as exc:
        result.detail = str(exc)
        for step in result.steps:
            if step.name == result.phase:
                step.status = "ERROR"
    finally:
        result.duration_seconds = round(time.monotonic() - started, 3)
        # Apply explicit-value redaction to metadata too, not just process output.
        values = artifact.get("env", {})
        if isinstance(values, dict):
            for value in values.values():
                if isinstance(value, str) and value:
                    result.command = [arg.replace(value, "[redacted]") for arg in result.command]
                    for name in ("artifact", "detail", "fix", "output"):
                        setattr(result, name, getattr(result, name).replace(value, "[redacted]"))
    return result
