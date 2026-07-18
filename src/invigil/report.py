"""Render a Scorecard as terminal text, JSON, Markdown (PR comment), or a
shields.io endpoint badge.

The terminal/Markdown renderers lead with failures and always print the fix —
the report is itself a product surface (D2). The badge renderer emits the JSON
shape shields.io's `endpoint` badge expects, so a repo can host a live grade
badge without a third-party service.
"""

from __future__ import annotations

import json

from .model import GATE_SHORT_TITLES, GATE_TITLES, Scorecard, Status

_EFFORT_ORDER = {"minutes": 0, "hours": 1, "days": 2, "": 3}


def _sorted_failures(sc: Scorecard) -> list:
    """Return failures sorted by effort so quick wins surface first."""
    return sorted(sc.failures(), key=lambda r: _EFFORT_ORDER.get(r.check.effort, 3))


def as_text(sc: Scorecard, *, quiet: bool = False) -> str:
    """Terminal report. `quiet` prints only FAIL/WARN blocks — no header, no
    summary — so a fully passing repo produces no output at all (script- and
    pre-commit-friendly: silence is the pass signal)."""
    failures = _sorted_failures(sc)
    warns = [r for r in sc.results if r.status == Status.WARN]
    lines: list[str] = []
    if not quiet:
        lines += [
            f"Invigil scorecard — {sc.repo}",
            f"  Gate: {sc.gate_level()}   Grade: {sc.grade()}   Score: {sc.earned}/{sc.possible} ({sc.percent:.0f}%)",
            "",
        ]
    if failures:
        if not quiet:
            lines.append("Failing checks (fix these to raise the gate):")
        for r in failures:
            effort_tag = f"  [{r.check.effort}]" if r.check.effort else ""
            lines.append(f"  [{r.check.gate}] {r.check.title}{effort_tag}")
            lines.append(f"        why: {r.detail}")
            lines.append(f"        fix: {r.fix}")
        if not quiet:
            lines.append("")
    if quiet:
        for r in warns:
            lines.append(f"  [warn] {r.check.title}: {r.detail}")
        return "\n".join(lines)
    passed = [r for r in sc.results if r.status == Status.PASS]
    lines.append(
        f"Passing: {len(passed)}   Failing: {len(failures)}   "
        f"Skipped: {sum(1 for r in sc.results if r.status == Status.SKIP)}"
    )
    return "\n".join(lines)


def as_json(sc: Scorecard) -> str:
    return json.dumps(
        {
            "repo": sc.repo,
            "gate": sc.gate_level(),
            "grade": sc.grade(),
            "earned": sc.earned,
            "possible": sc.possible,
            "percent": round(sc.percent, 1),
            "checks": [
                {
                    "id": r.check.id,
                    "gate": r.check.gate,
                    "title": r.check.title,
                    "status": r.status.value,
                    "detail": r.detail,
                    "fix": r.fix,
                    "duration_ms": r.duration_ms,
                }
                for r in sc.results
            ],
        },
        indent=2,
    )


def as_markdown(sc: Scorecard) -> str:
    out = [
        f"### Invigil — `{sc.repo}`",
        "",
        f"**Gate {sc.gate_level()}** · **Grade {sc.grade()}** · {sc.earned}/{sc.possible} ({sc.percent:.0f}%)",
        "",
        f"> {GATE_TITLES.get(sc.gate_level(), 'below G1')}",
        "",
    ]
    failures = _sorted_failures(sc)
    if failures:
        out += ["| Gate | Check | Effort | Why | Fix |", "|---|---|---|---|---|"]
        for r in failures:
            out.append(f"| {r.check.gate} | {r.check.title} | {r.check.effort or '—'} | {r.detail} | {r.fix} |")
        out.append("")
    else:
        out += ["All doctrine checks pass. :white_check_mark:", ""]
    out.append(
        f"<sub>{sum(1 for r in sc.results if r.status == Status.PASS)} passing · "
        f"{len(failures)} failing · "
        f"{sum(1 for r in sc.results if r.status == Status.SKIP)} skipped · "
        f"report-only</sub>"
    )
    return "\n".join(out)


def as_badge(sc: Scorecard) -> str:
    gate = sc.gate_level()
    grade = sc.grade()
    subtitle = GATE_SHORT_TITLES.get(gate, "")
    message = f"{gate} · {grade} · {subtitle}" if subtitle else f"{gate} · {grade}"
    color = (
        "brightgreen"
        if grade.startswith("A")
        else "green"
        if grade.startswith("B")
        else "yellow"
        if grade.startswith("C")
        else "orange"
        if grade.startswith("D")
        else "red"
    )
    return json.dumps(
        {
            "schemaVersion": 1,
            "label": "invigil",
            "message": message,
            "color": color,
            "cacheSeconds": 3600,
        }
    )


def as_ai_badge(sc: Scorecard) -> str:
    """Shields endpoint badge for the AI-readiness sub-score (group `ai`)."""
    passed, applicable = sc.ai_readiness()
    pct = 100.0 * passed / applicable if applicable else 0.0
    return json.dumps(
        {
            "schemaVersion": 1,
            "label": "ai-ready",
            "message": f"{passed}/{applicable} agent-legible" if applicable else "n/a",
            "color": "brightgreen" if pct >= 80 else "yellow" if pct >= 50 else "orange",
            "cacheSeconds": 3600,
        }
    )


def as_llm(sc: Scorecard) -> str:
    """Token-economical report for agent consumption: one line per finding,
    stable ordering (effort, then id), no decoration. A healthy repo costs the
    reading agent two lines."""
    ai_pass, ai_app = sc.ai_readiness()
    lines = [
        f"invigil repo={sc.repo} gate={sc.gate_level()} grade={sc.grade()} "
        f"score={sc.earned}/{sc.possible} ai_ready={ai_pass}/{ai_app}"
    ]
    for r in sorted(sc.failures(), key=lambda r: (_EFFORT_ORDER.get(r.check.effort, 3), r.check.id)):
        lines.append(f"FAIL {r.check.id} | {r.detail} | fix: {r.fix}")
    for r in sorted((r for r in sc.results if r.status == Status.WARN), key=lambda r: r.check.id):
        lines.append(f"WARN {r.check.id} | {r.detail}")
    lines.append(
        f"summary pass={sum(1 for r in sc.results if r.status == Status.PASS)} "
        f"fail={len(sc.failures())} "
        f"warn={sum(1 for r in sc.results if r.status == Status.WARN)} "
        f"skip={sum(1 for r in sc.results if r.status == Status.SKIP)}"
    )
    return "\n".join(lines)


RENDERERS = {"text": as_text, "json": as_json, "markdown": as_markdown, "badge": as_badge, "llm": as_llm}
