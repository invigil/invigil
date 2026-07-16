"""The Stranger Gate engine (Layer 2).

Boots each published artifact a user actually downloads on a clean machine and
probes its core surface within a 10-minute budget — the mechanized version of
D1's "be the stranger". Driven entirely by `.invigil.yml`, so one reusable
workflow replaces every repo's hand-rolled `smoke-published.yml`.

The pure logic (probe evaluation, URL resolution, the budget) is import-safe and
unit-tested; the orchestration shells out to `docker` / `pip` (never a Python SDK)
so it runs anywhere a GitHub runner does. Nothing here is imported by the static
scorecard, so `invigil score` stays dependency-light.
"""

from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from .config import InvigilConfig


class StrangerError(RuntimeError):
    """A boot or probe step failed — the artifact a stranger downloads is broken."""


@dataclass
class Probe:
    url: str
    auth: str | None = None
    expect_status: int = 200
    expect_contains: str | None = None
    expect_json_count_min: int | None = None

    @classmethod
    def from_dict(cls, d: dict) -> Probe:
        jc = d.get("expect_json_count") or {}
        return cls(
            url=d["url"],
            auth=d.get("auth"),
            expect_status=int(d.get("expect_status", 200)),
            expect_contains=d.get("expect_contains"),
            expect_json_count_min=(int(jc["min"]) if "min" in jc else None),
        )

    def evaluate(self, status: int, body: str) -> tuple[bool, str]:
        """Pure check of one response against this probe's expectations."""
        if status != self.expect_status:
            return False, f"status {status} != {self.expect_status}"
        if self.expect_contains and self.expect_contains not in body:
            return False, f"body missing {self.expect_contains!r}"
        if self.expect_json_count_min is not None:
            try:
                data = json.loads(body)
                n = len(data)
            except (ValueError, TypeError):
                return False, "response is not a JSON array/object"
            if n < self.expect_json_count_min:
                return False, f"json count {n} < {self.expect_json_count_min}"
        return True, "ok"


def resolve_url(probe_url: str, default_port: int | None) -> str:
    """Absolute URLs pass through; a bare path is served from the artifact's port."""
    if probe_url.startswith(("http://", "https://")):
        return probe_url
    if default_port is None:
        raise StrangerError(f"probe {probe_url!r} is a path but no artifact port is known")
    return f"http://127.0.0.1:{default_port}{probe_url}"


def _fetch(url: str, auth: str | None, timeout: float = 5.0) -> tuple[int, str]:
    req = urllib.request.Request(url)
    if auth:
        import base64

        req.add_header("Authorization", "Basic " + base64.b64encode(auth.encode()).decode())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (localhost/http probe)
            return resp.status, resp.read().decode(errors="replace")
    except urllib.error.HTTPError as e:  # a 4xx/5xx is still a real, evaluable response
        return e.code, e.read().decode(errors="replace")


def run_probes(probes: list[Probe], default_port: int | None, budget_seconds: int) -> None:
    """Wait for the first probe to come up (within budget), then assert all probes."""
    if not probes:
        return
    deadline = time.monotonic() + budget_seconds
    first = resolve_url(probes[0].url, default_port)
    while time.monotonic() < deadline:
        try:
            _fetch(first, probes[0].auth, timeout=3.0)
            break
        except (urllib.error.URLError, OSError, TimeoutError):
            time.sleep(2.0)
    else:
        raise StrangerError(f"artifact did not serve {first} within {budget_seconds}s (D1 10-minute rule)")

    failures = []
    for p in probes:
        url = resolve_url(p.url, default_port)
        try:
            status, body = _fetch(url, p.auth)
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            failures.append(f"{url}: unreachable ({exc})")
            continue
        ok, detail = p.evaluate(status, body)
        print(f"  {'PASS' if ok else 'FAIL'}  {url}  ({detail})")
        if not ok:
            failures.append(f"{url}: {detail}")
    if failures:
        raise StrangerError("probe failures:\n  - " + "\n  - ".join(failures))


# --- orchestration (shells out; not unit-tested) --------------------------
@dataclass
class _Started:
    containers: list[str] = field(default_factory=list)


def _run(*cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    print("  $", " ".join(cmd), flush=True)  # flush so the echo precedes any stderr in CI logs
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise StrangerError(f"{' '.join(cmd[:2])} failed: {r.stderr.strip() or r.stdout.strip()}")
    return r


def _start_services(cfg: InvigilConfig, state: _Started) -> None:
    for name, svc in cfg.services.items():
        args = ["docker", "run", "-d", "--name", f"invigil-svc-{name}"]
        for k, v in (svc.get("env") or {}).items():
            args += ["-e", f"{k}={v}"]
        for port in svc.get("ports") or []:
            args += ["-p", port]
        args.append(svc["image"])
        state.containers.append(f"invigil-svc-{name}")
        _run(*args)


def _boot_artifacts(cfg: InvigilConfig, state: _Started) -> int | None:
    """Boot each artifact; return the port of the last HTTP-serving (ghcr) one."""
    default_port = None
    for i, art in enumerate(cfg.artifacts):
        if art.get("type") == "ghcr":
            name = f"invigil-art-{i}"
            args = ["docker", "run", "-d", "--network", "host", "--name", name]
            for k, v in (art.get("env") or {}).items():
                args += ["-e", f"{k}={v}"]
            args.append(art["image"])
            state.containers.append(name)
            _run(*args)
            default_port = int(art.get("port", default_port or 8000))
        elif art.get("type") == "pypi":
            _run("python", "-m", "venv", "/tmp/invigil-venv")
            _run("/tmp/invigil-venv/bin/pip", "install", "--quiet", art["name"])
            boot = art.get("boot")
            if boot:
                r = subprocess.run(
                    ["/tmp/invigil-venv/bin/python", "-c", boot], capture_output=True, text=True, env={**_env(art)}
                )
                if r.returncode != 0:
                    raise StrangerError(f"pypi boot failed: {r.stderr.strip()}")
    return default_port


def _env(art: dict) -> dict:
    import os

    return {**os.environ, **{k: str(v) for k, v in (art.get("env") or {}).items()}}


def _teardown(state: _Started) -> None:
    for c in state.containers:
        _run("docker", "logs", c, check=False)
        _run("docker", "rm", "-f", c, check=False)


def run(cfg: InvigilConfig) -> None:
    """Full Stranger Gate: services up, artifacts booted, probes asserted, teardown."""
    if not cfg.artifacts:
        raise StrangerError("no artifacts declared in .invigil.yml — nothing for the stranger to boot")
    probes = [Probe.from_dict(p) for p in cfg.probes]
    state = _Started()
    try:
        _start_services(cfg, state)
        default_port = _boot_artifacts(cfg, state)
        run_probes(probes, default_port, cfg.boot_budget_minutes * 60)
        print(f"Stranger gate OK: {len(cfg.artifacts)} artifact(s), {len(probes)} probe(s).")
    finally:
        _teardown(state)
