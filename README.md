# Invigil

**Linters check your code. Invigil checks whether your project is legible.**

[![CI](https://github.com/invigil/invigil/actions/workflows/ci.yml/badge.svg)](https://github.com/invigil/invigil/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/invigil)](https://pypi.org/project/invigil/)
[![GitHub Marketplace](https://img.shields.io/badge/Marketplace-Invigil-2088FF?logo=githubactions&logoColor=white)](https://github.com/marketplace/actions/invigil-product-quality-gate)
[![Docker](https://img.shields.io/badge/ghcr-invigil%2Finvigil-2496ed?logo=docker&logoColor=white)](https://github.com/invigil/invigil/pkgs/container/invigil)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/invigil/invigil/badge)](https://scorecard.dev/viewer/?uri=github.com/invigil/invigil)
[![Invigil grade](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/invigil/invigil/main/badges/invigil.json)](https://github.com/invigil/invigil)
[![AI-ready](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/invigil/invigil/main/badges/invigil-ai.json)](https://github.com/invigil/invigil#when-your-user-is-an-agent)

Ruff has your syntax. Dependabot has your dependencies. Scorecard has your supply chain.
**Nothing checks whether someone arriving cold can act on the project:** boot it in ten
minutes, get an error that tells them the fix, install the thing from PyPI *today*, read a
README that's still a landing page and not a 600-line wall.

That's the test every project takes when someone new finds it — a new engineer, or
increasingly an AI agent with a context window instead of patience. If they can't reach
"hello world" in 10 minutes, they leave. If the published artifact is broken because CI
only tests the source tree, they leave. If the error is a silent stack trace, they leave.
Nobody files an issue on the way out.

Invigil turns those promises into mechanical checks, runs them in CI, and prints the exact
fix for every failure — so the project speaks for itself.

> *invigilate* — to watch over an exam and enforce its rules.

---

## How Invigil fits in your stack

Invigil does not replace your existing tools; it covers the product-quality gaps they leave behind.

| Tool | Focus | What it misses (that Invigil catches) |
|---|---|---|
| **Linters / SonarQube** | Code style, static bugs, complexity | Does the *published artifact* actually boot? Is the README approachable? |
| **Dependabot / Renovate** | Keeping dependencies updated | Are you enforcing the lockfile in CI? Is there a version matrix? |
| **OpenSSF Scorecard** | Supply-chain security (branch rules, tokens) | Does the project have a Quick Start? Are failure modes actionable? |
| **Invigil** | Product quality, legibility, error hygiene | (Invigil relies on the above tools and enforces their presence) |

---

## Why

You already wrote the doctrine; you just enforce it by hand. Every failing Invigil check tells
you **what's wrong, why it matters, and the exact command to fix it** — because a gate that
can't tell you how to pass it is the same broken-error-message anti-pattern it's meant to catch.

It grades against seven **Gates**, each a legibility promise to a different cold-start reader:

| Gate | The promise |
|---|---|
| **G1** | Anyone arriving cold succeeds in 10 minutes on a clean machine |
| **G2** | Every failure mode tells the user the fix |
| **G3** | Published artifacts are machine-verified daily |
| **G4** | Supply-chain evidence is public (Scorecard ≥7, signed releases, SBOM) |
| **G5** | All five doors open and documented (newbie, operator, contributor, enterprise, AI) |
| **G6** | First external contributor merged without hand-holding |
| **G7** | Cited/integrated by projects you don't control |

A repo *reaches* `Gn` only when every mandatory check for gates ≤ n passes, and gets a letter
grade from its weighted score.

## Install

One tool, four doors — pick the one that matches where you run it:

| Channel | Where it fits | One-liner |
|---|---|---|
| **PyPI** | local runs, Python-friendly CI | `pip install invigil` |
| **GitHub Action** | GitHub PRs | `uses: invigil/invigil@v1` |
| **Docker (ghcr)** | GitLab, Jenkins, any non-Python CI | `docker run --rm -v "$PWD:/repo" ghcr.io/invigil/invigil score /repo` |
| **pre-commit** | offline checks on every commit | hooks `invigil-layout`, `invigil-secrets` (below) |
| **MCP server** | agents (Claude Code, any MCP client) | `pip install "invigil[mcp]"` → `invigil mcp` |

Every release ships all of it signed: cosign-signed wheel, sdist, and container image, plus an
SPDX SBOM — verifiable with `cosign verify` against the GitHub OIDC identity.

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
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1        # v7.0.1
      - uses: invigil/invigil@7f31330715bb7e42f26032ce3e921fcf78d4acea        # v1.7.1
        with:
          enforce: "false"              # flip to true once the grade is stable
```

Flip `enforce: "true"` (or set `project.enforce: true` in `.invigil.yml`) when you're ready for
it to block merges below the target gate.

> **Why the SHAs?** `invigil/invigil@v1` works and tracks the latest v1.x.y, but Invigil's own
> `actions-sha-pinned` check (G3) fails floating tags — including its own. Pin, and let
> Dependabot bump the pins; the trailing comment is what it reads.

The action exposes the report and both badges as step outputs — pipe the scorecard into the job
summary, publish the badge JSON wherever shields.io can reach it:

```yaml
      - uses: invigil/invigil@7f31330715bb7e42f26032ce3e921fcf78d4acea        # v1.7.1
        id: invigil
        with: { comment: "false" }
      - run: cat "${{ steps.invigil.outputs.report }}" >> "$GITHUB_STEP_SUMMARY"
      # outputs.badge → grade badge JSON · outputs.ai-badge → ai-ready badge JSON
```

## How it works

Two layers, matching the doctrine:

- **Static Doctrine Scorecard** (every PR, seconds) — inspects the repo filesystem and GitHub
  metadata: LICENSE, README length, `.env.example`, a deep-health endpoint, a global error-id
  handler, SHA-pinned actions, an enforced lockfile, a coverage gate, a daily published-artifact
  smoke test, ≥5 good-first-issues, docs index, `llms.txt`/`AGENTS.md`, and more. Emits text /
  JSON / Markdown / a shields.io badge.
- **Cold-Start Gate** (nightly, reusable — `invigil stranger`) — on a clean runner, installs
  and boots each *published* artifact you declare and probes its core surface within a
  10-minute budget. Web services get HTTP probes; a CLI image (an artifact with a `command:`)
  is run to completion and must exit 0. One reusable workflow replaces the 60-line
  `smoke-published.yml` every repo copy-pastes:

```yaml
# .github/workflows/stranger-gate.yml
name: Cold-start gate
on:
  schedule: [{ cron: "0 3 * * *" }]
  workflow_dispatch:
jobs:
  stranger:
    uses: invigil/invigil/.github/workflows/stranger-gate.yml@7f31330715bb7e42f26032ce3e921fcf78d4acea  # v1.7.1
```

### Fix by PR (Dependabot-for-legibility)

Opt in to a scheduled bot that applies Invigil's mechanical fixes on a work branch and opens
**one batched PR** — governance scaffolds, agent context files, config hygiene. Three
anti-noise rules are built in: it's opt-in only, one stable branch means one PR (never five),
and a PR you close unmerged is a "no" the bot respects — it stays silent until you delete the
`invigil/fixes` branch.

```yaml
# .github/workflows/legibility-fixes.yml
name: Legibility fixes
on:
  schedule: [{ cron: "0 6 1 * *" }]   # monthly — these are one-time scaffolds, not deps
  workflow_dispatch:
jobs:
  fix:
    uses: invigil/invigil/.github/workflows/fix-pr.yml@7f31330715bb7e42f26032ce3e921fcf78d4acea  # v1.7.1
```

Under the hood it runs `invigil score --fix --pr-mode`: the fix engine's CI-lockout stays
in force for protected branches — `--pr-mode` only permits fixes on a non-default branch,
so nothing automated ever lands on `main` without a human merging the PR.

## Configuration

Drop a `.invigil.yml` at the repo root. It's optional for the static scorecard (sensible
defaults apply) and required for the Cold-Start Gate (it declares what to boot and probe). Full
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
  - repo: https://github.com/invigil/invigil
    rev: v1        # tracks the latest v1.x.y
    hooks: [{ id: invigil-layout }, { id: invigil-secrets }]
  ```

  Heavier, network-bound checks (`scorecard`, the Cold-Start Gate) stay in CI.
  `invigil score --offline` / `--layer local` / `--group supply-chain` slice it any way.
- **It bends instead of forking.** `profile: strict | progressive | light`, per-check
  `weights`, `optional` (ding without gating), `thresholds.fail_on` — make it *your* doctrine.
- **Resilient by design.** A scorecard.dev timeout is a SKIP excluded from the grade — never a
  false A-to-C downgrade, never a crashed build.

  → [The doctrine and the Gates](docs/doctrine.md) covers both in full.

## When your user is an agent

Legibility now has two audiences. The reader arriving cold at your repo is, more often than
not, an AI agent: it has a context window instead of patience, exit codes instead of
intuition, and it acts only on what the repo states machine-readably. The `ai` check group
grades that surface — not just *presence* of `llms.txt`/`AGENTS.md`, but whether an agent can
actually act on them:

| Check | The promise to the agent |
|---|---|
| `agents-md-actionable` | Your `AGENTS.md`/`CLAUDE.md` contains runnable fenced commands, not prose |
| `llms-txt-shape` | `llms.txt` is spec-shaped and fits a 10 KB context budget |
| `agent-context-fresh` | Agent instructions aren't 90+ days staler than the source they describe |
| `readme-heading-hierarchy` | The README chunks cleanly (one H1, real H2 sections) |
| `exit-codes-documented` | A CLI's exit codes are enumerated — agents branch on codes, not prose |
| `llms-no-secrets` | The machine-readable surface leaks no credentials |
| `agent-scope-visibility` | Agent code declares its tool inventory (blast-radius precondition) |

Two artifacts fall out of it. **`invigil score --format llm`** — a deterministic report under
~1 KB, built to be read *by* an agent: a healthy repo costs it two lines of context. And an
**`ai-ready` badge**, a shields.io endpoint you can put in your own README:

```bash
invigil score . --format ai-badge --output badges/ai-ready.json   # commit this
```

```markdown
![AI-ready](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/OWNER/REPO/main/badges/ai-ready.json)
```

In CI the Action emits it for you — `steps.<id>.outputs.ai-badge` is the path to the same JSON.

### MCP server

Agents don't have to shell out — Invigil speaks MCP natively (`mcp-name: io.github.invigil/invigil`):

```bash
pip install "invigil[mcp]"    # optional extra; the core CLI stays zero-dep
invigil mcp                   # stdio server
```

```json
// e.g. .mcp.json for Claude Code — any MCP client works
{ "mcpServers": { "invigil": { "command": "uvx", "args": ["--from", "invigil[mcp]", "invigil", "mcp"] } } }
```

Three read-only tools: `evaluate_repo` (the scorecard, `llm` or `json` format),
`check_group` (one fast offline group), and `preview_fixes` (the mutation plan `--fix`
would apply — the agent applies changes with its own edit tools, so nothing here writes).

## The doctrine

*Absence of complaints is not absence of problems — silence is the loudest negative signal a
project gets.* That's the Silent User Doctrine, and Invigil is its enforcement:
[what the Gates mean and how to tune them](docs/doctrine.md).

## Contributing

Issues and PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) and
[good first issues](https://github.com/invigil/invigil/labels/good%20first%20issue). Invigil
grades itself in CI (`self-score` job); a PR that lowers Invigil's own grade won't merge.

## License

Apache-2.0 — see [LICENSE](LICENSE).
