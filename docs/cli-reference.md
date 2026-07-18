# Invigil CLI Reference

Full reference for every `invigil` subcommand, flag, and exit code.

---

## Installation

```bash
# PyPI
pip install invigil

# Docker
docker run --rm -v $(pwd):/repo ghcr.io/invigil/invigil:latest score /repo

# pre-commit (add to .pre-commit-config.yaml)
repos:
  - repo: https://github.com/invigil/invigil
    rev: v1
    hooks:
      - id: invigil-layout
      - id: invigil-secrets
```

---

## Exit codes (all subcommands)

| Code | Meaning |
|---|---|
| `0` | Success / gate satisfied (or report-only mode) |
| `1` | `--enforce` active and gate is below target; or `invigil check` found failures; or `--fix` staged changes (pre-commit signal) |
| `2` | Usage error or path not found |
| `3` | `--fix` refused because `CI=true` (CI-lockout safety) |

---

## `invigil score [PATH]`

Score a repo against all quality gates. Report-only by default — never blocks a build unless `--enforce` is set. `invigil evaluate` is an exact alias — the spelling an AI agent (or a human instructing one) tends to reach for.

`--fix` applies available mechanical fixes (refused under CI: exit 3). `--fix --pr-mode` lifts that CI-lockout for PR-bot flows, but refuses (exit 3) on the repo's default branch — automated fixes may only land on a work branch that a human merges via PR. The same flags exist on `invigil check`.

`-q`/`--quiet` (text format, also on `invigil check`): print only FAIL/WARN lines with their fixes — no header, no summary. A fully passing run produces no output: silence is the pass signal, so it composes cleanly in scripts and pre-commit hooks.

```bash
invigil score .
invigil score /path/to/repo --format markdown --output score.md
invigil score . --enforce --min-gate G3
invigil score . --offline --profile light
invigil score . --fix   # apply mechanical fixes for failing checks
```

### Options

| Flag | Default | Description |
|---|---|---|
| `PATH` | `.` | Path to the repo root |
| `--format` | `text` | Output format: `text`, `json`, `markdown`, `badge` |
| `--min-gate` | profile default | Hard-fail below this gate (e.g. `G3`) |
| `--enforce` | off | Exit 1 if gate is below target |
| `--output FILE` | stdout | Write output to FILE instead of stdout |
| `--offline` | off | Skip all network checks (scorecard.dev, GitHub API) |
| `--layer LAYER` | all | Only run checks on this layer: `local`, `network`, `heavy` |
| `--group GROUP` | all | Only run checks in this group: `layout`, `secrets`, `errors`, `supply-chain`, `evidence`, `doors`, `ai` |
| `--profile` | config | Override the `.invigil.yml` profile: `strict`, `progressive`, `light` |
| `--fix` | off | Apply safe mechanical fixes for failing checks; stages changed files |

### Output formats

**`text`** — human-readable terminal output with failures sorted by effort:
```
Invigil scorecard — my-repo
  Gate: G3   Grade: B+   Score: 24/29 (83%)

Failing checks (fix these to raise the gate):
  [G5] docs/ has an index  [minutes]
        why: no docs index
        fix: add docs/README.md linking every deep doc
```

**`json`** — machine-readable, suitable for dashboards and CI parsers.

**`markdown`** — GitHub PR comment format with a failures table.

**`badge`** — shields.io endpoint JSON:
```json
{
  "schemaVersion": 1,
  "label": "invigil",
  "message": "G3 · B+ · artifact verified daily",
  "color": "green",
  "cacheSeconds": 3600
}
```

Use with:
```markdown
![invigil](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/ORG/REPO/main/badges/REPO.json)
```

---

## `invigil check GROUP [PATH]`

Run one check group offline — fast (\<200ms), designed for pre-commit hooks.
Exits 1 if any check in the group fails.

```bash
invigil check layout .
invigil check secrets .
invigil check supply-chain . --online   # allow network checks in this group
invigil check layout . --fix            # auto-fix and stage
```

### Available groups

| Group | Checks | Layer |
|---|---|---|
| `layout` | README, LICENSE, quickstart, .env.example | local |
| `secrets` | tracked secret files, gitleaks history scan | local |
| `errors` | deep-health endpoint, correlation id, error tests | local |
| `supply-chain` | smoke-published, dependabot, SHA-pinned, lockfile, coverage, matrix | local |
| `evidence` | Scorecard workflow, score, signed releases, SECURITY, CHANGELOG | local + network |
| `doors` | docs index, CONTRIBUTING, CoC, CLI reference, good-first-issues | local + network |
| `ai` | llms.txt/AGENTS.md, no secrets in AI docs, agent scope visibility | local |

### Options

| Flag | Default | Description |
|---|---|---|
| `GROUP` | required | Check group to run (see table above) |
| `PATH` | `.` | Path to the repo root |
| `--online` | off | Allow network checks in this group (default: offline-only) |
| `--fix` | off | Apply fixes and stage; exits 1 as pre-commit signal to re-commit |

---

## `invigil stranger [PATH]`

Boot every published artifact declared in `.invigil.yml` on the local machine and probe its core surface. This is the Layer 2 Cold-Start Gate (the subcommand keeps its original `stranger` name for compatibility) — run in CI, not pre-commit.

```bash
invigil stranger .
invigil stranger /path/to/repo
```

`.invigil.yml` artifact declaration:
```yaml
artifacts:
  - type: pypi
    name: my-package
  - type: ghcr
    image: ghcr.io/org/image:latest
    command: ["--version"]
    expect_contains: "my-package"

probes:
  - url: http://localhost:8080/health
    expect_status: 200
    expect_contains: "ok"

boot_budget_minutes: 10
```

---

## `invigil portfolio PATHS...`

Score multiple repos and emit a portfolio grade table. Used by the scheduled `portfolio.yml` workflow to keep the grade table current without hand-typing.

```bash
invigil portfolio . ../other-repo --update PORTFOLIO.md
invigil portfolio . ../repo-a ../repo-b --badges-dir badges/
```

### Options

| Flag | Default | Description |
|---|---|---|
| `PATHS` | required | One or more repo paths to score |
| `--update FILE` | stdout | Replace the `invigil:portfolio` marker block in FILE |
| `--badges-dir DIR` | — | Write `<repo>.json` shields.io badge files to DIR |
| `--date DATE` | today | Override the generated-on date (for reproducible output) |

---

## `.invigil.yml` configuration

```yaml
version: 1

project:
  name: my-repo           # display name in reports (default: directory name)
  language: python        # python | node | go | rust (affects lockfile/coverage detection)
  min_gate: G3            # target gate for --enforce
  enforce: false          # flip to true to hard-fail PRs below min_gate

profile: progressive      # strict | progressive | light

checks:
  disable:
    - external-scorecard-lookup   # skip the live scorecard.dev API call
  optional:
    - version-matrix              # demote to advisory (ding, don't gate)
  weights:
    license-apache2: 3            # make this check count more
    readme-length: 0              # effectively disable
  thresholds:
    fail_on: G3                   # hard-fail at/below this gate; report-only above

# Layer 2 — Cold-Start Gate
artifacts:
  - type: pypi
    name: my-package
  - type: ghcr
    image: ghcr.io/org/image:latest
    command: ["--version"]
    expect_contains: "my-package"

probes:
  - url: http://localhost:8080/health
    expect_status: 200

boot_budget_minutes: 10
```

### Profile presets

| Profile | Layers | Offline | Fail on | Notes |
|---|---|---|---|---|
| `strict` | all | no | G4 | Highest bar; use for release gates |
| `progressive` | all | no | G3 | Default; report-first, enforce G3 |
| `light` | local only | yes | none | All checks advisory; use for experiments |

---

## Project plugin API (`.invigil/plugins/`)

Drop a `.py` file in `.invigil/plugins/` to add custom checks. No imports from Invigil required — just define `invigil_register_check()`:

```python
# .invigil/plugins/my_check.py

def invigil_register_check() -> list[dict]:
    return [{
        "id":             "my-check",          # unique, kebab-case
        "gate":           "G2",                # G1..G7
        "title":          "My custom rule",
        "weight":         1,
        "mandatory":      False,               # True = gate failure; False = advisory ding
        "layer":          "local",             # local | network | heavy
        "group":          "layout",            # any existing group name
        "effort":         "minutes",           # minutes | hours | days
        "check_callback": run_check,
        "fix_callback":   None,                # optional
    }]


def run_check(ctx):
    from invigil.model import Check, CheckResult, Status
    check = Check(id="my-check", gate="G2", title="My custom rule")
    if (ctx.repo / "MY_REQUIRED_FILE.md").exists():
        return CheckResult(check, Status.PASS, "found")
    return CheckResult(check, Status.FAIL, "missing", "add MY_REQUIRED_FILE.md")
```

Invigil discovers all `*.py` files in `.invigil/plugins/` automatically. A plugin that fails to import or returns an invalid manifest emits a `WARN` result and never crashes the scorecard.
