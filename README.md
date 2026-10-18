# Invigil

**Verify the path from installation to first successful use—for people and agents.**

[![CI](https://github.com/invigil/invigil/actions/workflows/ci.yml/badge.svg)](https://github.com/invigil/invigil/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/invigil)](https://pypi.org/project/invigil/)
[![GitHub Marketplace](https://img.shields.io/badge/Marketplace-Invigil-2088FF?logo=githubactions&logoColor=white)](https://github.com/marketplace/actions/invigil-product-quality-gate)
[![Docker](https://img.shields.io/badge/ghcr-invigil%2Finvigil-2496ed?logo=docker&logoColor=white)](https://github.com/invigil/invigil/pkgs/container/invigil)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/invigil/invigil/badge)](https://scorecard.dev/viewer/?uri=github.com/invigil/invigil)
[![Invigil grade](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/invigil/invigil/main/badges/invigil.json)](https://github.com/invigil/invigil)
[![AI-ready](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/invigil/invigil/main/badges/invigil-ai.json)](https://github.com/invigil/invigil#when-your-user-is-an-agent)

A package can install successfully and still fail its first useful command. Invigil
combines repository-quality checks with a Cold-Start Gate that exercises declared
operations and reports the evidence needed to diagnose failures.

**New in development:** verify an exact Python wheel before publication, outside the
source checkout. The existing scorecard, published-artifact checks, and agent tools
remain available. Wheel verification is **unreleased**; `pip install invigil` and the
release pins below do not include it yet.

## Try the first-use demo (source preview)

On Linux with Python 3.11+ and venv support, use the source-preview branch:

```bash
git clone --branch feat/wheel-first-use-preview https://github.com/invigil/invigil.git
cd invigil
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python examples/first-use-demo/run.py
```

The demo runs offline and checks real wheels. Both install; one omits a required data file and fails its first-use command. Adding that file makes the same
check pass. It prints the failure and saves JSON reports in a temporary directory.
This is a synthetic example, not a claim about an upstream project's current release.

[Demo details](examples/first-use-demo/README.md) ·
[Verify your own wheel](docs/cli-reference.md#invigil-stranger-path) ·
[CI workflow template](examples/wheel-first-use.yml)

The preview requires an explicit command and optional expected output. A successful
run proves that operation worked in the recorded environment; it is not a general
release-safety guarantee. Run unfamiliar artifacts in disposable workers without
credentials—a Python venv is not a security sandbox.

> *invigilate* — to watch over an exam and enforce its rules.

---

## How Invigil fits in your stack

Invigil does not replace your existing tools; it covers the product-quality gaps they leave behind.

| Capability | Role |
|---|---|
| Repository scorecard | Checks documentation, configuration and quality conventions; suggests fixes |
| Published-artifact Cold-Start Gate | Exercises configured package/container operations and HTTP probes |
| Local-wheel first use (unreleased) | Verifies the candidate artifact; records its hash, phases and dependencies |
| Existing linters, scanners and tests | Continue checking code correctness and security alongside Invigil |

A clean-install smoke script can detect the same packaging defects. Invigil aims
to make that workflow easier to configure and its reports consistent across projects.

---

## Why

The scorecard checks whether the project is legible to newcomers and agents.
Every failing static check includes a suggested command or edit. Execution reports
retain the failed step and output; they cannot infer every application's root cause.

The [seven Gates](docs/doctrine.md) cover onboarding, errors, artifact verification,
supply-chain evidence, audience documentation, contribution and adoption. A grade
summarizes implemented repository checks; it does not establish that an artifact
was executed successfully. Use the Cold-Start Gate for execution evidence.

## Install

Published channels — pick the one that matches where you run it:

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

These commands use the published scorecard. For wheel verification, use the source
preview above.

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
  and boots configured published artifacts and probes their declared surfaces.
  The new local-wheel path additionally bounds setup/install/first use with one
  per-wheel budget and records phase results; legacy paths retain their behavior. Web services get HTTP probes; a CLI image (an artifact with a `command:`)
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

### Fix by PR

The optional [fix workflow](.github/workflows/fix-pr.yml) applies mechanical fixes
on a work branch and opens one batched PR. It uses `invigil score --fix --pr-mode`;
protected-branch safeguards remain in place. Closing its PR without merging is
respected until the work branch is deleted. See the
[CLI reference](docs/cli-reference.md) for configuration and limits.

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

## Stability

Invigil is **Alpha**, and [`docs/stability.md`](docs/stability.md) says exactly what that
buys you: the CLI, exit codes, JSON shape, badge JSON and MCP tools are stable enough to
automate against; individual check verdicts are not, and every report carries a
`doctrine_version` so you can tell *your repo regressed* from *the ruler moved*.

## Contributing

Issues and PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) and
[good first issues](https://github.com/invigil/invigil/labels/good%20first%20issue). Invigil
grades itself in CI; self-score is currently report-only. See the scoped
[beginner tasks](https://github.com/invigil/invigil/issues?q=is%3Aopen+label%3A%22good+first+issue%22)
and [benchmark tasks](https://github.com/invigil/invigil/issues?q=is%3Aopen+label%3A%22help+wanted%22).

## License

Apache-2.0 — see [LICENSE](LICENSE).
