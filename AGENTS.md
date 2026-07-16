# AGENTS.md — conventions for AI coding agents

Invigil is a Python 3.11+ package (src layout) that grades a repo against a
product-quality doctrine and ships as a GitHub Action.

## Build / test / lint

```bash
pip install -e . ruff pytest pytest-cov
ruff check . && ruff format --check .        # lint + format gate
pytest --cov=invigil --cov-fail-under=80     # tests + coverage floor
invigil score .                              # dogfood: grade Invigil with Invigil
```

## Layout

- `src/invigil/model.py` — Check / CheckResult / Scorecard, scoring + gate logic.
- `src/invigil/context.py` — repo/git/gh/workflow helpers handed to every check.
- `src/invigil/checks/gN_*.py` — checks grouped by Gate; each `@register(...)`-ed.
- `src/invigil/report.py` — text/json/markdown/badge renderers.
- `src/invigil/cli.py` — the `invigil score` entry point.

## Conventions (do these or CI/self-score will reject the change)

- Every check is `(Context) -> CheckResult`. **A FAIL must set `fix`** (the exact
  command/edit to pass). Read its own metadata via `fn.__invigil__`.
- Prefer `Status.SKIP` over `FAIL` when a check doesn't apply to the repo's shape
  (e.g. a web-only check on a CLI). Grade honestly.
- Never let a check crash the run; the registry wraps exceptions into WARN.
- Keep checks dependency-light: git/gh via subprocess, no new runtime deps beyond
  PyYAML without discussion.
