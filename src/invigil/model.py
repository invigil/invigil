"""Core data model shared by the check registry, scorer, and reporters.

A Check inspects a repo and yields a CheckResult. Results roll up into a
Scorecard with a weighted score, a Gate level (G1..G7), and a letter grade.
Every failing result must carry a `fix` — the exact command or edit that
resolves it. That is D2 ("errors are a product surface") applied to the gate
itself: a red check that doesn't tell you how to fix it is a bug.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Status(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"


# Ordered gates, lowest first. A repo "reaches" Gn only when every mandatory
# check tagged for gates <= n passes. See QUALITY-PLAYBOOK.md "The Gates".
GATES = ["G1", "G2", "G3", "G4", "G5", "G6", "G7"]

GATE_TITLES = {
    "G1": "A stranger succeeds in 10 minutes on a clean machine",
    "G2": "Every failure mode tells the user the fix",
    "G3": "Published artifacts are machine-verified daily",
    "G4": "Supply-chain evidence is public (Scorecard >=7, signed, SBOM)",
    "G5": "All five doors open and documented",
    "G6": "First external contributor merged without hand-holding",
    "G7": "Cited/integrated by projects you don't control",
}


@dataclass
class Check:
    """A single doctrine check. `gate` is the highest gate this check gates on;
    `mandatory` checks must pass for that gate to be considered reached.

    `layer` decides *when* a check runs — `local` (offline, fast, pre-commit),
    `network` (needs the internet), or `heavy` (boots artifacts). `group` is the
    human-facing bundle (`layout`, `secrets`, `supply-chain`, `ai`, ...) selected
    by `invigil check <group>`."""

    id: str
    gate: str
    title: str
    weight: int = 1
    mandatory: bool = True
    discipline: str = ""  # D1..D5, for grouping in the report
    layer: str = "local"  # local | network | heavy
    group: str = ""  # layout | secrets | errors | supply-chain | evidence | doors | ai


@dataclass
class CheckResult:
    check: Check
    status: Status
    detail: str = ""  # what was observed
    fix: str = ""  # exact command/edit to resolve (required when status == FAIL)

    @property
    def ok(self) -> bool:
        return self.status in (Status.PASS, Status.SKIP)


@dataclass
class Scorecard:
    repo: str
    results: list[CheckResult] = field(default_factory=list)

    @property
    def earned(self) -> int:
        return sum(r.check.weight for r in self.results if r.status == Status.PASS)

    @property
    def possible(self) -> int:
        return sum(r.check.weight for r in self.results if r.status != Status.SKIP)

    @property
    def percent(self) -> float:
        return 100.0 * self.earned / self.possible if self.possible else 0.0

    def gate_level(self) -> str:
        """Highest contiguous gate whose mandatory checks all pass.

        Capped at the highest gate that actually has a check in the registry:
        a gate with no evidence is never *awarded* by pass-through. This keeps
        G6/G7 (contributor merged, cited by others — not mechanically checkable)
        out of reach of the automated scorecard, and keeps a partial registry
        honest instead of reporting a spurious G7.
        """
        defined = {r.check.gate for r in self.results}
        if not defined:
            return "—"
        ceiling = max(GATES.index(g) for g in defined)
        reached = ""
        for g in GATES[: ceiling + 1]:
            mandatory = [r for r in self.results if r.check.gate == g and r.check.mandatory]
            if any(r.status == Status.FAIL for r in mandatory):
                break
            reached = g
        return reached or "—"

    def grade(self) -> str:
        """Letter grade matching the OSS-LAUNCH-CHECKLIST portfolio table style."""
        p = self.percent
        if p >= 97:
            return "A+"
        if p >= 93:
            return "A"
        if p >= 90:
            return "A-"
        if p >= 87:
            return "B+"
        if p >= 83:
            return "B"
        if p >= 80:
            return "B-"
        if p >= 75:
            return "C+"
        if p >= 70:
            return "C"
        if p >= 65:
            return "C-"
        if p >= 55:
            return "D"
        return "F"

    def failures(self) -> list[CheckResult]:
        return [r for r in self.results if r.status == Status.FAIL]
