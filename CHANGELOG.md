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
- Stranger Gate reusable workflow (skeleton) for daily published-artifact probing.

[Unreleased]: https://github.com/rrskris/invigil/commits/main
