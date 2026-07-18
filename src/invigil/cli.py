"""`invigil` command-line entry point.

    invigil score [PATH] [--format text|json|markdown|badge] [--min-gate G4]
                  [--enforce] [--output FILE]

Exit codes:
    0  scorecard produced; gate satisfied (or report-only mode)
    1  --enforce (or config enforce=true) and below the min gate; or `--fix` changed files
    2  usage / IO error
    3  `--fix` refused because it's running under CI (CI-lockout)

Report-first is the default: without --enforce the command always exits 0, so
it can be wired into CI as a comment-and-badge step before it ever blocks a PR.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from . import __version__, engine
from .checks import GROUPS, LAYERS
from .config import InvigilConfig
from .context import Context
from .model import GATES, Scorecard, Status
from .report import RENDERERS, as_text


def score(
    path: Path,
    *,
    only_layers: set[str] | None = None,
    only_groups: set[str] | None = None,
    offline: bool | None = None,
    profile: str | None = None,
) -> tuple[Scorecard, InvigilConfig]:
    """Score `path`. `only_layers`/`offline` = None means "defer to the repo's
    profile"; an explicit value overrides it (e.g. a CLI flag)."""
    from .checks import run_all  # imported here so registration happens once

    config = InvigilConfig.load(path)
    if profile:
        config.profile = profile
    eff = engine.resolve(config)
    layers = eff.only_layers if only_layers is None else only_layers
    off = eff.offline if offline is None else offline
    ctx = Context(repo=path, config=config)
    results = run_all(ctx, only_layers=layers, only_groups=only_groups, offline=off)
    # Apply per-check weight/mandatory overrides without mutating the registry.
    results = [replace(r, check=eff.adjust(r.check)) for r in results]
    sc = Scorecard(repo=config.name or path.name, results=results)
    return sc, config


def _gate_ge(reached: str, target: str) -> bool:
    """True if `reached` gate is at or above `target` in the G1..G7 order."""
    if reached not in GATES:
        return False
    return GATES.index(reached) >= GATES.index(target)


def _run_fixes(repo: Path, config: InvigilConfig, results: list) -> bool | None:
    """Apply fixes for failing checks and stage them. Returns True if any file
    changed, False if nothing changed, or None if refused under CI (caller exits 3)."""
    from .fixer import apply_fixes, ci_active

    if ci_active():
        print("invigil: --fix is disabled under CI (CI-lockout) — run it locally", file=sys.stderr)
        return None
    ctx = Context(repo=repo, config=config)
    rep = apply_fixes(ctx, results)
    if rep.changed_files:
        ctx.git("add", *rep.changed_files)
    if rep.fixed:
        print(f"fixed: {', '.join(rep.fixed)}")
    if rep.unresolved:
        print(f"unresolved (fix ran, still failing): {', '.join(rep.unresolved)}", file=sys.stderr)
    if rep.changed_files:
        print(f"changed + staged: {', '.join(rep.changed_files)}")
    return rep.changed


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
    sc_cmd.add_argument("--offline", action="store_true", help="skip network checks (no internet access)")
    sc_cmd.add_argument("--layer", action="append", choices=LAYERS, help="only run this layer (repeatable)")
    sc_cmd.add_argument("--group", action="append", choices=GROUPS, help="only run this group (repeatable)")
    sc_cmd.add_argument("--profile", choices=list(engine.PROFILES), help="override the .invigil.yml profile")
    sc_cmd.add_argument("--fix", action="store_true", help="apply available fixes for failing checks, then re-score")
    sc_cmd.add_argument("-q", "--quiet", action="store_true", help="suppress passing checks, show only failures/warnings + summary")

    ck_cmd = sub.add_parser("check", help="run one check group, offline (fast — for pre-commit)")
    ck_cmd.add_argument("group", choices=GROUPS, help="the check group to run")
    ck_cmd.add_argument("path", nargs="?", default=".", help="repo path (default: .)")
    ck_cmd.add_argument("--online", action="store_true", help="allow this group's network checks to run")
    ck_cmd.add_argument("--fix", action="store_true", help="apply fixes for failing checks and stage them")

    st_cmd = sub.add_parser("stranger", help="boot published artifacts and probe them (Layer 2)")
    st_cmd.add_argument("path", nargs="?", default=".", help="repo path holding .invigil.yml (default: .)")

    pf_cmd = sub.add_parser("portfolio", help="score several repos into one grade table (C5)")
    pf_cmd.add_argument("paths", nargs="+", help="repo paths to score")
    pf_cmd.add_argument("--update", help="replace the invigil:portfolio marker block in this file")
    pf_cmd.add_argument("--date", default=None, help="override the generated-on date (for reproducible output)")
    pf_cmd.add_argument("--badges-dir", help="write a shields.io endpoint badge <repo>.json per repo into DIR")

    args = parser.parse_args(argv)

    if args.cmd == "score":
        repo = Path(args.path).resolve()
        if not repo.exists():
            print(f"invigil: path not found: {repo}", file=sys.stderr)
            return 2
        score_kwargs = dict(
            only_layers=set(args.layer) if args.layer else None,
            only_groups=set(args.group) if args.group else None,
            offline=True if args.offline else None,
            profile=args.profile,
        )
        sc, config = score(repo, **score_kwargs)
        if args.fix:
            changed = _run_fixes(repo, config, sc.results)
            if changed is None:
                return 3
            sc, config = score(repo, **score_kwargs)  # re-score to reflect fixes
        if args.format == "text":
            rendered = as_text(sc, quiet=args.quiet)
        else:
            rendered = RENDERERS[args.format](sc)
        if args.output:
            Path(args.output).write_text(rendered + "\n")
        else:
            print(rendered)

        eff = engine.resolve(config)
        target = args.min_gate or eff.fail_on or config.min_gate
        enforce = args.enforce or config.enforce or config.profile == "strict"
        if enforce and target and not _gate_ge(sc.gate_level(), target):
            print(f"invigil: gate {sc.gate_level()} is below target {target}", file=sys.stderr)
            return 1
        return 0

    if args.cmd == "check":
        repo = Path(args.path).resolve()
        if not repo.exists():
            print(f"invigil: path not found: {repo}", file=sys.stderr)
            return 2
        # A group run is offline-by-default (pre-commit speed); --online opts in.
        changed = False
        sc, config = score(repo, only_groups={args.group}, offline=not args.online)
        if args.fix and sc.failures():
            result = _run_fixes(repo, config, sc.results)
            if result is None:
                return 3
            changed = result
            sc, config = score(repo, only_groups={args.group}, offline=not args.online)
        fails = sc.failures()
        for r in fails:
            print(f"FAIL [{args.group}] {r.check.title}\n      why: {r.detail}\n      fix: {r.fix}")
        passed = sum(1 for r in sc.results if r.status == Status.PASS)
        print(f"invigil check {args.group}: {passed} passed, {len(fails)} failing")
        if fails:
            return 1
        return 1 if changed else 0  # pre-commit: files were fixed+staged, re-commit

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
        if args.badges_dir:
            from .report import as_badge

            bdir = Path(args.badges_dir)
            bdir.mkdir(parents=True, exist_ok=True)
            for sc in scorecards:
                (bdir / f"{sc.repo}.json").write_text(as_badge(sc) + "\n")
            print(f"wrote {len(scorecards)} badge(s) to {bdir}")

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
