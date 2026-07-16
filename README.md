# Invigil

**A CI quality gate that grades a repo against a product-quality *doctrine* — not code style.**

[![CI](https://github.com/rrskris/invigil/actions/workflows/ci.yml/badge.svg)](https://github.com/rrskris/invigil/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/invigil)](https://pypi.org/project/invigil/)

Linters check your *code*. Dependabot checks your *dependencies*. **Nothing checks whether
your project keeps the promises a stranger relies on:** that they can boot it in ten minutes,
that every error tells them the fix, that the thing on PyPI actually installs today, that the
README is still a landing page and not a 600-line wall.

Invigil turns those promises into mechanical, exact-fix-reporting checks and runs them in CI —
so the project speaks for itself.

> *invigilate* — to watch over an exam and enforce its rules.

---

## Why

You already wrote the doctrine; you just enforce it by hand. Every failing Invigil check tells
you **what's wrong, why it matters, and the exact command to fix it** — because a gate that
can't tell you how to pass it is the same broken-error-message anti-pattern it's meant to catch.

It grades against seven **Gates**, each a promise to a different stranger:

| Gate | The promise |
|---|---|
| **G1** | A stranger succeeds in 10 minutes on a clean machine |
| **G2** | Every failure mode tells the user the fix |
| **G3** | Published artifacts are machine-verified daily |
| **G4** | Supply-chain evidence is public (Scorecard ≥7, signed releases, SBOM) |
| **G5** | All five doors open and documented (newbie, operator, contributor, enterprise, AI) |
| **G6** | First external contributor merged without hand-holding |
| **G7** | Cited/integrated by projects you don't control |

A repo *reaches* `Gn` only when every mandatory check for gates ≤ n passes, and gets a letter
grade from its weighted score.

## Quick Start

Run it locally on any repo:

```bash
pip install invigil
invigil score .            # human-readable scorecard + the exact fix for every failure
invigil score . --format markdown   # a PR-comment-ready table
invigil score . --format json       # machine-readable
```

Add it to CI as a report-only gate (posts a scorecard comment + badge, never blocks a PR):

```yaml
# .github/workflows/quality-gate.yml
name: Quality gate
on: [pull_request]
permissions: { contents: read, pull-requests: write }
jobs:
  invigil:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: rrskris/invigil@v1        # the doctrine scorecard
        with:
          enforce: "false"              # flip to true once the grade is stable
```

Flip `enforce: "true"` (or set `project.enforce: true` in `.invigil.yml`) when you're ready for
it to block merges below the target gate.

## How it works

Two layers, matching the doctrine:

- **Static Doctrine Scorecard** (every PR, seconds) — inspects the repo filesystem and GitHub
  metadata: LICENSE, README length, `.env.example`, a deep-health endpoint, a global error-id
  handler, SHA-pinned actions, an enforced lockfile, a coverage gate, a daily published-artifact
  smoke test, ≥5 good-first-issues, docs index, `llms.txt`/`AGENTS.md`, and more. Emits text /
  JSON / Markdown / a shields.io badge.
- **Stranger Gate** (nightly, reusable) — on a clean runner, installs and boots each *published*
  artifact you declare and probes its core surface within a 10-minute budget. One reusable
  workflow replaces the 60-line `smoke-published.yml` every repo copy-pastes:

```yaml
# .github/workflows/stranger-gate.yml
name: Stranger gate
on:
  schedule: [{ cron: "0 3 * * *" }]
  workflow_dispatch:
jobs:
  stranger:
    uses: rrskris/invigil/.github/workflows/stranger-gate.yml@v1
```

## Configuration

Drop a `.invigil.yml` at the repo root. It's optional for the static scorecard (sensible
defaults apply) and required for the Stranger Gate (it declares what to boot and probe). Full
schema in [`schema/invigil.schema.json`](schema/invigil.schema.json); examples in
[`examples/`](examples/).

```yaml
version: 1
project:
  name: my-app
  language: python
  min_gate: G4
  enforce: false
artifacts:
  - type: pypi
    name: "my-app[all]"
  - type: ghcr
    image: ghcr.io/me/my-app:latest
    port: 8000
probes:
  - { url: "/", expect_status: 200 }
  - { url: "/api/things", expect_json_count: { min: 5 } }
boot_budget_minutes: 10
```

## Lightweight & modular

A gate developers bypass is dead weight, so Invigil is built for zero friction:

- **Fast offline groups for pre-commit** — each check is tagged `local`/`network`/`heavy`.
  `invigil check layout` runs the filesystem checks with no network in ~120ms:

  ```yaml
  # .pre-commit-config.yaml
  - repo: https://github.com/rrskris/invigil
    rev: v1.0.0
    hooks: [{ id: invigil-layout }, { id: invigil-secrets }]
  ```

  Heavier, network-bound checks (`scorecard`, the Stranger Gate) stay in CI.
  `invigil score --offline` / `--layer local` / `--group supply-chain` slice it any way.
- **Profiles, so it bends instead of forking.** `profile: strict | progressive | light`, plus
  per-check `weights`, `optional` (ding without gating), and `thresholds.fail_on`. Make it your
  doctrine, not a hardcoded one.
- **Resilient by design.** A scorecard.dev timeout is a SKIP that's excluded from the grade —
  never a false A-to-C downgrade, never a crashed build.
- **AI-era native.** The `ai` group checks that your `llms.txt`/`AGENTS.md` leak no secrets and
  that agent code declares its tool inventory — the first slice of "what's the blast radius if
  this agent is prompt-injected?"

## The doctrine

Invigil encodes a specific product-quality doctrine (the Silent User Doctrine and its Five
Disciplines): *absence of complaints is not absence of problems — silence is the loudest
negative signal a project gets.* You test at release time; users arrive after dependencies
drift and registries change. Only automation is awake then. Invigil is that automation.

## Contributing

Issues and PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) and
[good first issues](https://github.com/rrskris/invigil/labels/good%20first%20issue). Invigil
grades itself in CI (`self-score` job); a PR that lowers Invigil's own grade won't merge.

## License

Apache-2.0 — see [LICENSE](LICENSE).
