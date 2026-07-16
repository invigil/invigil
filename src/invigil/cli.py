"""`invigil` command-line entry point.

    invigil score [PATH] [--format text|json|markdown|badge] [--min-gate G4]
                  [--enforce] [--output FILE]

Exit codes:
    0  scorecard produced; gate satisfied (or report-only mode)
    1  --enforce (or config enforce=true) and the repo is below its min gate
    2  usage / IO error

Report-first is the default: without --enforce the command always exits 0, so
it can be wired into CI as a comment-and-badge step before it ever blocks a PR.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import InvigilConfig
from .context import Context
from .model import GATES, Scorecard
from .report import RENDERERS


def score(path: Path) -> tuple[Scorecard, InvigilConfig]:
    from .checks import run_all  # imported here so registration happens once

    config = InvigilConfig.load(path)
    ctx = Context(repo=path, config=config)
    sc = Scorecard(repo=config.name or path.name, results=run_all(ctx))
    return sc, config


def _gate_ge(reached: str, target: str) -> bool:
    """True if `reached` gate is at or above `target` in the G1..G7 order."""
    if reached not in GATES:
        return False
    return GATES.index(reached) >= GATES.index(target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="invigil", description="Grade a repo against the quality doctrine.")
    parser.add_argument("--version", action="version", version=f"invigil {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sc_cmd = sub.add_parser("score", help="score a repo against the doctrine")
    sc_cmd.add_argument("path", nargs="?", default=".", help="repo path (default: .)")
    sc_cmd.add_argument("--format", choices=list(RENDERERS), default="text")
    sc_cmd.add_argument("--min-gate", default=None, help="override target gate (e.g. G4)")
    sc_cmd.add_argument("--enforce", action="store_true", help="exit non-zero if below the target gate")
    sc_cmd.add_argument("--output", help="write to FILE instead of stdout")

    st_cmd = sub.add_parser("stranger", help="boot published artifacts and probe them (Layer 2)")
    st_cmd.add_argument("path", nargs="?", default=".", help="repo path holding .invigil.yml (default: .)")

    pf_cmd = sub.add_parser("portfolio", help="score several repos into one grade table (C5)")
    pf_cmd.add_argument("paths", nargs="+", help="repo paths to score")
    pf_cmd.add_argument("--update", help="replace the invigil:portfolio marker block in this file")
    pf_cmd.add_argument("--date", default=None, help="override the generated-on date (for reproducible output)")

    args = parser.parse_args(argv)

    if args.cmd == "score":
        repo = Path(args.path).resolve()
        if not repo.exists():
            print(f"invigil: path not found: {repo}", file=sys.stderr)
            return 2
        sc, config = score(repo)
        rendered = RENDERERS[args.format](sc)
        if args.output:
            Path(args.output).write_text(rendered + "\n")
        else:
            print(rendered)

        target = args.min_gate or config.min_gate
        enforce = args.enforce or config.enforce
        if enforce and not _gate_ge(sc.gate_level(), target):
            print(f"invigil: gate {sc.gate_level()} is below target {target}", file=sys.stderr)
            return 1
        return 0

    if args.cmd == "stranger":
        from .stranger import StrangerError, run

        repo = Path(args.path).resolve()
        config = InvigilConfig.load(repo)
        try:
            run(config)
        except StrangerError as exc:
            print(f"invigil stranger: {exc}", file=sys.stderr)
            return 1
        return 0

    if args.cmd == "portfolio":
        from datetime import date

        from .portfolio import build_table, update_block

        scorecards = []
        for p in args.paths:
            repo = Path(p).resolve()
            if not repo.exists():
                print(f"invigil: path not found: {repo}", file=sys.stderr)
                return 2
            sc, _ = score(repo)
            scorecards.append(sc)
        table = build_table(scorecards, args.date or date.today().isoformat())
        if args.update:
            target = Path(args.update)
            target.write_text(update_block(target.read_text(), table))
            print(f"updated portfolio block in {target}")
        else:
            print(table)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
