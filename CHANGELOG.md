# Changelog

All notable changes to Invigil are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

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

[1.3.2]: https://github.com/invigil/invigil/releases/tag/v1.3.2
[1.3.1]: https://github.com/invigil/invigil/releases/tag/v1.3.1
[1.3.0]: https://github.com/invigil/invigil/compare/v1.0.0...v1.3.0
[1.2.0]: https://github.com/invigil/invigil/compare/v1.0.0...v1.3.0
[1.1.0]: https://github.com/invigil/invigil/compare/v1.0.0...v1.3.0
[1.0.0]: https://github.com/invigil/invigil/releases/tag/v1.0.0
