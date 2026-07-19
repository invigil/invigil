# Changelog

All notable changes to Invigil are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [1.7.0] - 2026-07-19

### Added
- **`invigil mcp`** — a stdio MCP server so agents can call the gate as a native
  tool. Three read-only tools: `evaluate_repo` (llm/json scorecard),
  `check_group` (one fast offline group), `preview_fixes` (the dry-run mutation
  plan; agents apply changes with their own edit tools). Ships as the optional
  `[mcp]` extra — the core CLI stays zero-dep; without it, `invigil mcp` prints
  the install fix and exits 3. Registry: `io.github.invigil/invigil`
  (`server.json`).
- `-q`/`--quiet` on `score`/`evaluate`/`check`: only FAIL/WARN lines, no header
  or summary — a fully passing run prints nothing. Closes #6; supersedes #12
  (thanks @gandzekas for the initiative).
- `checks.disable` in `.invigil.yml` now accepts a plain YAML list as well as
  the legacy mapping form; an empty `disable:` key no longer crashes the loader.
  Closes #7 (thanks @leemeo3).

### Fixed
- **Action outputs (#13)**: `action.yml` now declares the top-level `outputs:`
  block composite actions require — `steps.<id>.outputs.report` and `.badge`
  were silently empty for every consumer. Found dogfooding Kaaval's CI.

### Changed
- Supply-chain hardening toward Scorecard ≥7: CI installs uv via the SHA-pinned
  `astral-sh/setup-uv` action, and the release build installs `build` from a
  hash-pinned requirements file (`--require-hashes`).
- PyPI keywords + README/llms.txt now cover the MCP/agent surface.

## [1.6.0] - 2026-07-18

### Added
- **Fix by PR** (Dependabot-for-legibility): reusable `fix-pr.yml` workflow applies
  mechanical fixes on a stable `invigil/fixes` branch and opens one batched PR.
  Opt-in only; one PR ever open; a PR closed unmerged is a "no" the bot respects.
- **`--pr-mode`** on `score`/`check` (with `--fix`): lifts the CI-lockout for
  PR-bot flows but refuses the default branch — automated fixes only land on a
  work branch a human merges.
- Scaffolded `AGENTS.md`/`llms.txt` templates now include
  `invigil evaluate . --format llm` as the pre-PR verification step.
- `invigil evaluate` — exact alias of `score`.

### Fixed
- `actions-sha-pinned` false positives: `uses:` references inside YAML comments
  are no longer counted, and quoted pins (`uses: "org/action@<sha>"`) are
  recognized as pinned. Caught by dogfood — the new fix-pr.yml's usage example
  comment tripped the old parser.

## [1.5.1] - 2026-07-18

### Changed
- **"Legibility" replaces the "stranger" framing** across all user-visible
  surfaces: the boot-and-probe engine is now the **Cold-Start Gate**, G1 reads
  "Anyone arriving cold succeeds in 10 minutes", the G1 badge subtitle is
  "cold-start ready", and the Action description grades "a repo's legibility to
  newcomers and AI agents". Compatibility unbroken: the `invigil stranger`
  subcommand and the `stranger-gate.yml` reusable-workflow path keep their
  names (renaming published API is a v2 decision).

## [1.5.0] - 2026-07-18

### Added
- **AI-legibility checks** (group `ai`): the stranger reading your repo is now an
  agent. Five new checks grade the machine-readable surface for actionability,
  not just presence — `agents-md-actionable` (fenced runnable commands in
  AGENTS.md/CLAUDE.md), `llms-txt-shape` (spec shape + 10 KB context budget),
  `agent-context-fresh` (instructions not 90+ days staler than the source),
  `readme-heading-hierarchy` (one H1, real H2 sections — agents chunk by
  heading), `exit-codes-documented` (CLI repos enumerate exit codes).
- **`ai-ready` badge**: `--badges-dir` now also writes `<repo>-ai.json`, a
  shields endpoint for the AI-readiness sub-score (`Scorecard.ai_readiness()`).
- **`--format llm`**: a deterministic, token-economical report built to be read
  by an agent — one line per finding, stable ordering, a healthy repo costs two
  lines of context.
- The `ai-door` fix now scaffolds both `AGENTS.md` and a spec-shaped `llms.txt`.

## [1.4.0] - 2026-07-18

### Added
- JSON reports now include `duration_ms` per check — callback execution time
  measured in `run_all`, recorded for errored (WARN) checks too. Contributed by
  @floze-the-genius in [#11](https://github.com/invigil/invigil/pull/11) —
  Invigil's first external contribution. Closes #10.

### Changed
- Marketplace branding icon is now `eye` (invigilate — to watch over an exam),
  replacing the generic `check-circle`.
- Listed on the GitHub Marketplace as "Invigil — Product Quality Gate"
  (Continuous integration · Code quality).
- `main` is now a protected branch; CodeQL analysis runs on every push and PR.

## [1.3.2] - 2026-07-18

### Changed
- Action metadata reworded for the GitHub Marketplace listing: name is now
  "Invigil — Product Quality Gate", description fits the 125-char limit.
- Scorecard hardening: portfolio workflow token scoped to its job, scheduled
  CodeQL analysis, Docker base image pinned by digest.

## [1.3.1] - 2026-07-18

### Fixed
- Release pipeline: `cosign sign-blob` updated for cosign v3's bundle format
  (`--bundle *.sigstore.json`); the v1.3.0 release run published to PyPI but
  failed at signing, so 1.3.0 on PyPI is unsigned and shipped no Docker image
  or GitHub Release. 1.3.1 is the first fully signed release since 1.0.0.
- Source formatting drift that failed CI's `ruff format --check`.

## [1.3.0] - 2026-07-18 (PyPI only, unsigned — superseded by 1.3.1)

> **Note:** first version published since 1.0.0. The 1.1.0 and 1.2.0 changes
> below were merged to `main` but never tagged or published; their artifacts
> first ship with 1.3.x (the Docker image and signatures with 1.3.1).

### Added
- **Structured plugin architecture**: Invigil now supports local-first project plugins via `.invigil/plugins/*.py`. Drop a script exporting `invigil_register_check()` and it seamlessly integrates into the scorecard.
  - Zero dependencies: implemented using native `importlib` and `typing.Protocol` instead of heavy dependencies like `pluggy`.
  - Resilience: a broken plugin emits a `WARN` result and never crashes the gate.
- **Improved model & reporting**:
  - Checks now specify an `effort` field (`minutes`, `hours`, `days`). Reports sort failures by effort so teams see quick wins first.
  - Checks can be marked as `severity="blocker"`. A blocker failure hard-stops the gate, preventing it from being papered over by other passing scores.
  - Badges now include a human-readable subtitle (e.g., `G3 · B+ · artifact verified daily`).
- **OSS Positioning**:
  - The `license-apache2` check is now split: `license-present` is mandatory (blocker), while `license-apache2` is purely advisory. MIT/GPL/MPL projects are no longer penalised.
  - Removed "doctrine" jargon from user-visible check titles and fix messages.
  - New `nightly-smoke.yml` workflow enforces the Stranger Gate on Invigil itself.
  - Profiles (`strict`, `progressive`, `light`) are now externalized to JSON configs.
  - CLI reference published at `docs/cli-reference.md`.

## [1.2.0] - 2026-07-18 (never published — first shipped in 1.3.0)

### Added
- **`invigil fix` engine** — `score`/`check` gain `--fix`, which applies mechanical
  corrections for failing checks and stages them. Turns Invigil from a gate into a
  proactive fixer.
  - **Safe mutation broker** (`mutator.py`): fixes return structured `Mutation`
    intents (`create_file` / `append_file` / `replace_string` / `delete_file`) — never
    shell — and the broker path-jails every write inside the repo and logs it.
  - **Single-pass rule:** after a fix runs, its one check is re-run; a second failure is
    flagged unresolved instead of looping.
  - **CI-lockout:** `--fix` hard-errors (exit 3) when `CI` is set, so it can't trigger
    cascading automated commits on a protected branch.
  - Ships fixes for the missing-governance-file checks (SECURITY.md, CONTRIBUTING.md,
    CODE_OF_CONDUCT.md, CHANGELOG.md, dependabot.yml, docs/README.md, AGENTS.md).

## [1.1.0] - 2026-07-16 (never published — first shipped in 1.3.0)

### Added
- **Docker distribution:** the CLI ships as a container image at
  `ghcr.io/invigil/invigil` (`latest`, `X`, `X.Y.Z` tags), built and
  cosign-signed by the same release workflow as the PyPI artifacts — Invigil now
  runs in GitLab/Jenkins/any CI without a Python setup.
- **Stranger Gate CLI artifacts:** a `ghcr` artifact with `command:` runs to
  completion (`docker run --rm`) and asserts exit 0 + optional
  `expect_contains`, instead of booting a daemon. Invigil's own `.invigil.yml`
  now dogfoods both published channels nightly.
- **`v1` moving major tag** is maintained automatically on every release, so
  `uses: invigil/invigil@v1` and pre-commit `rev: v1` track the newest v1.x.y.
- README install matrix covering all four channels (PyPI / Action / Docker /
  pre-commit).

## [1.0.0] - 2026-07-16

### Added
- Static Doctrine Scorecard: check registry mapped to Gates G1–G5, weighted
  scoring, gate-level + letter grade, and text/JSON/Markdown/badge reporters.
- `invigil score` CLI with report-first behavior and an `--enforce` mode.
- `.invigil.yml` config + JSON schema; example configs for a Python app and a
  multi-image app.
- Composite GitHub Action (`action.yml`) that posts a scorecard PR comment.
- Stranger Gate: `invigil stranger` boot+probe engine + reusable workflow.
- Cross-repo aggregation: `invigil portfolio` regenerates a grade table.
- **Modular execution:** every check tagged with a `layer` (local/network/heavy)
  and `group`; `invigil check <group>` runs one group offline (<500ms, for
  pre-commit) and `invigil score` gained `--offline`/`--layer`/`--group`.
- **Profiles + rule overrides:** `profile: strict|progressive|light` plus
  `.invigil.yml` `checks.optional`/`weights`/`thresholds.fail_on` — so teams can
  bend the doctrine instead of forking it.
- **Resilience:** a network flake (e.g. scorecard.dev timeout) is a SKIP that
  cannot move the grade — never a false downgrade, never a crashed build.
- **pre-commit hooks:** `.pre-commit-hooks.yaml` (`invigil-layout`, `invigil-secrets`).
- **AI-native group (`ai`):** `llms-no-secrets` and `agent-scope-visibility` — the
  statically-honest first slice of "agent blast radius".

[1.6.0]: https://github.com/invigil/invigil/releases/tag/v1.6.0
[1.5.1]: https://github.com/invigil/invigil/releases/tag/v1.5.1
[1.5.0]: https://github.com/invigil/invigil/releases/tag/v1.5.0
[1.4.0]: https://github.com/invigil/invigil/releases/tag/v1.4.0
[1.3.2]: https://github.com/invigil/invigil/releases/tag/v1.3.2
[1.3.1]: https://github.com/invigil/invigil/releases/tag/v1.3.1
[1.3.0]: https://github.com/invigil/invigil/compare/v1.0.0...v1.3.0
[1.2.0]: https://github.com/invigil/invigil/compare/v1.0.0...v1.3.0
[1.1.0]: https://github.com/invigil/invigil/compare/v1.0.0...v1.3.0
[1.0.0]: https://github.com/invigil/invigil/releases/tag/v1.0.0
