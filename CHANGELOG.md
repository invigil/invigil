# Changelog

All notable changes to Invigil are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/rrskris/invigil/commits/main
