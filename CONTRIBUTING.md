# Contributing to Invigil

Thanks for helping grade the ungradeable. Invigil holds itself to the doctrine it
enforces — the `self-score` CI job runs Invigil against Invigil, and a PR that lowers
its own grade won't merge.

## Dev setup

```bash
git clone https://github.com/rrskris/invigil
cd invigil
python -m venv .venv && . .venv/bin/activate
pip install -e . ruff pytest pytest-cov
```

## Run the checks locally (the same ones CI runs)

```bash
ruff check . && ruff format --check .
pytest --cov=invigil --cov-fail-under=80
invigil score .              # dogfood: grade Invigil with Invigil
```

## Adding a doctrine check

1. Add a function `(Context) -> CheckResult` in the right `src/invigil/checks/gN_*.py`
   module, decorated with `@register(id=..., gate=..., title=..., discipline=...)`.
2. **Every FAIL must carry a `fix`** — the exact command or edit. A red check that
   can't tell you how to pass it is the bug it's meant to catch.
3. Add tests in `tests/` covering pass, fail (with a non-empty fix), and skip.
4. Prefer SKIP over FAIL when a check doesn't apply to a repo's shape (e.g. a
   web-only check on a CLI) — grade honestly, don't punish inapplicability.

## PRs

- Conventional-ish commit subjects, small and reviewable.
- Sign off your commits (DCO): `git commit -s`.
- Green CI (lint + tests + self-score) before review.
