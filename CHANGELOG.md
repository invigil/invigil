# Changelog

All notable changes to Invigil are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [1.1.0] - 2026-07-16

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

[1.1.0]: https://github.com/invigil/invigil/releases/tag/v1.1.0
[1.0.0]: https://github.com/invigil/invigil/releases/tag/v1.0.0
