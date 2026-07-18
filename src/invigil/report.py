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


def as_text(sc: Scorecard) -> str:
    lines = [
        f"Invigil scorecard — {sc.repo}",
        f"  Gate: {sc.gate_level()}   Grade: {sc.grade()}   Score: {sc.earned}/{sc.possible} ({sc.percent:.0f}%)",
        "",
    ]
    failures = _sorted_failures(sc)
    if failures:
        lines.append("Failing checks (fix these to raise the gate):")
        for r in failures:
            effort_tag = f"  [{r.check.effort}]" if r.check.effort else ""
            lines.append(f"  [{r.check.gate}] {r.check.title}{effort_tag}")
            lines.append(f"        why: {r.detail}")
            lines.append(f"        fix: {r.fix}")
        lines.append("")
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


RENDERERS = {"text": as_text, "json": as_json, "markdown": as_markdown, "badge": as_badge}
