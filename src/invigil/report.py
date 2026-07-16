"""Render a Scorecard as terminal text, JSON, Markdown (PR comment), or a
shields.io endpoint badge.

The terminal/Markdown renderers lead with failures and always print the fix —
the report is itself a product surface (D2). The badge renderer emits the JSON
shape shields.io's `endpoint` badge expects, so a repo can host a live grade
badge without a third-party service.
"""

from __future__ import annotations

import json

from .model import GATE_TITLES, Scorecard, Status


def as_text(sc: Scorecard) -> str:
    lines = [
        f"Invigil scorecard — {sc.repo}",
        f"  Gate: {sc.gate_level()}   Grade: {sc.grade()}   Score: {sc.earned}/{sc.possible} ({sc.percent:.0f}%)",
        "",
    ]
    failures = sc.failures()
    if failures:
        lines.append("Failing checks (fix these to raise the gate):")
        for r in failures:
            lines.append(f"  [{r.check.gate}] {r.check.title}")
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
    failures = sc.failures()
    if failures:
        out += ["| Gate | Check | Why | Fix |", "|---|---|---|---|"]
        for r in failures:
            out.append(f"| {r.check.gate} | {r.check.title} | {r.detail} | {r.fix} |")
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
    grade = sc.grade()
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
        {"schemaVersion": 1, "label": "invigil", "message": f"{sc.gate_level()} · {grade}", "color": color}
    )


RENDERERS = {"text": as_text, "json": as_json, "markdown": as_markdown, "badge": as_badge}
