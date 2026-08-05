"""Execution context handed to every check: the repo path, the loaded config,
and small filesystem/git/gh helpers so checks stay one-liners.

Kept dependency-free on purpose: git and GitHub metadata are read via the
`git` and `gh` CLIs (subprocess), not a Python SDK, so Invigil runs anywhere
those binaries exist (which, in a GitHub Action, they always do).
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import InvigilConfig

# Vendored / generated trees that would drown out real signal in any walk.
_SKIP_DIRS = frozenset({".git", "node_modules", ".venv", "venv", "dist", "build", "target", "vendor", "third_party"})


@dataclass
class Context:
    repo: Path
    config: InvigilConfig

    # --- filesystem helpers -------------------------------------------------
    def path(self, *parts: str) -> Path:
        return self.repo.joinpath(*parts)

    def exists(self, *parts: str) -> bool:
        return self.path(*parts).exists()

    def first_existing(self, *candidates: str) -> Path | None:
        for c in candidates:
            if self.exists(c):
                return self.path(c)
        return None

    def first_matching(self, pattern: str, *, dirs: tuple[str, ...] = (".",), depth: int = 1) -> Path | None:
        """First file whose *name* matches `pattern` (a case-insensitive regex).

        `first_existing` asks whether a project used our spelling. This asks whether
        the artifact is there at all — `COPYING`, `LICENCE`, `Changelog.rst` and
        `readme.md` are the same artifacts as ours to every human who reads them,
        and treating a naming convention as an absence is how a presence check turns
        into a false accusation.
        """
        rx = re.compile(pattern, re.IGNORECASE)
        for d in dirs:
            root = self.path(d)
            if not root.is_dir():
                continue
            stack = [(root, 0)]
            found: list[Path] = []
            while stack:
                cur, lvl = stack.pop()
                try:
                    entries = sorted(cur.iterdir())
                except OSError:
                    continue
                for p in entries:
                    if p.is_file() and rx.fullmatch(p.name):
                        found.append(p)
                    elif p.is_dir() and lvl + 1 < depth and p.name not in _SKIP_DIRS:
                        stack.append((p, lvl + 1))
            if found:
                return sorted(found, key=lambda p: (len(p.parts), p.name))[0]
        return None

    def read(self, *parts: str) -> str:
        p = self.path(*parts)
        try:
            return p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def glob(self, pattern: str) -> list[Path]:
        return sorted(self.repo.glob(pattern))

    def rglob(self, pattern: str) -> list[Path]:
        # Skip vendored / VCS dirs that would drown out real signal.
        skip = ("/node_modules/", "/.git/", "/.venv/", "/dist/", "/build/")
        return sorted(p for p in self.repo.rglob(pattern) if not any(s in str(p) for s in skip))

    # --- process helpers ----------------------------------------------------
    def _run(self, *cmd: str) -> tuple[int, str]:
        try:
            r = subprocess.run(cmd, cwd=self.repo, capture_output=True, text=True, timeout=120)
            return r.returncode, (r.stdout + r.stderr)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return 127, str(exc)

    def git(self, *args: str) -> tuple[int, str]:
        return self._run("git", *args)

    def gh(self, *args: str) -> tuple[int, str]:
        return self._run("gh", *args)

    def tracked_files(self) -> list[str]:
        code, out = self.git("ls-files")
        return out.splitlines() if code == 0 else []

    def repo_slug(self) -> str | None:
        """owner/name from the origin remote, for scorecard.dev / gh API lookups."""
        code, out = self.git("config", "--get", "remote.origin.url")
        if code != 0 or not out.strip():
            return None
        url = out.strip().removesuffix(".git")
        # git@github.com:owner/name  or  https://github.com/owner/name
        if ":" in url and "github.com" in url:
            tail = url.split("github.com", 1)[1].lstrip(":/")
            parts = tail.split("/")
            if len(parts) >= 2:
                return f"{parts[-2]}/{parts[-1]}"
        return None

    # --- workflow / source helpers ------------------------------------------
    def workflow_files(self) -> list[Path]:
        d = self.path(".github", "workflows")
        if not d.is_dir():
            return []
        return sorted(p for p in d.iterdir() if p.suffix in (".yml", ".yaml"))

    def workflows_text(self) -> str:
        return "\n".join(p.read_text(errors="replace") for p in self.workflow_files())

    def source_files(self, *suffixes: str) -> list[Path]:
        sufs = suffixes or (".py",)
        return [p for p in self.rglob("**/*") if p.suffix in sufs and p.is_file()]

    def source_contains(self, *needles: str, suffixes: tuple[str, ...] = (".py",)) -> bool:
        """True if any (non-Invigil) source file contains any needle."""
        for p in self.source_files(*suffixes):
            if "/invigil/" in str(p):  # never match the tool's own source
                continue
            text = p.read_text(errors="replace")
            if any(n in text for n in needles):
                return True
        return False

    def source_matches(self, pattern: re.Pattern[str], suffixes: tuple[str, ...] = (".py",)) -> bool:
        """True if any (non-Invigil) source file matches `pattern`.

        The regex sibling of `source_contains`, for when a bare substring is too
        blunt to be honest — e.g. the package name `autogen` also occurs inside
        the word "autogenerated", which appears in most repos that have never
        seen an agent framework.
        """
        for p in self.source_files(*suffixes):
            if "/invigil/" in str(p):
                continue
            if pattern.search(p.read_text(errors="replace")):
                return True
        return False

    def is_web_service(self) -> bool:
        """Heuristic: does this repo serve HTTP? Gates the web-only D2 checks
        (a deep-health endpoint / a 500 handler mean nothing for a pure CLI or
        library, so those checks SKIP rather than FAIL such repos).

        Scans application source only — test files routinely name web frameworks
        as fixtures, which would otherwise misdetect a CLI's test suite as a
        service (Invigil's own tests do exactly this)."""
        markers = (
            "fastapi",
            "FastAPI(",
            "flask",
            "Flask(",
            "django",
            "starlette",
            "aiohttp",
            "express(",
            "http.ListenAndServe",
            "gin.Default",
            "uvicorn",
        )
        for p in self.source_files(".py", ".js", ".ts", ".go"):
            parts = set(p.parts)
            if "/invigil/" in str(p) or "tests" in parts or "test" in parts:
                continue  # tool's own source, or a test directory
            if p.name.startswith("test_") or p.name.endswith(("_test.py", "_test.go", ".test.ts", ".test.js")):
                continue  # a test file
            text = p.read_text(errors="replace")
            if any(m in text for m in markers):
                return True
        return False
