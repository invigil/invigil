"""Fixes — mechanical, safe corrections for checks whose failure is "a required
file is missing". Each returns `create_file` mutations with a real, generic
starter template; the fix engine applies them and re-runs the one check.

Only checks with an unambiguous, non-destructive fix get one. Content-specific
checks (LICENSE needs a copyright holder; README needs a pitch; error handlers
need code) are deliberately left for a human — a wrong auto-fix is worse than an
honest FAIL.
"""

from __future__ import annotations

from ..context import Context
from ..mutator import Mutation
from . import fix

SECURITY_MD = """\
# Security Policy

## Reporting a vulnerability

Report suspected vulnerabilities privately to **security@example.com** (replace with a real
address). Do not open a public issue. You'll get an acknowledgement within 72 hours.

## Supported versions

| Version | Supported |
|---------|-----------|
| latest  | ✅        |
"""

CONTRIBUTING_MD = """\
# Contributing

Thanks for contributing!

## Dev setup

```bash
# clone, create a virtualenv, install dev deps, run the tests
```

## Before you open a PR

- Run the linters and the test suite locally.
- Keep commits small and reviewable; sign off your commits (`git commit -s`, DCO).
- Describe *what* changed and *why* in the PR body.
"""

CODE_OF_CONDUCT_MD = """\
# Code of Conduct

This project adopts the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/),
version 2.1. Be respectful, assume good faith, keep it technical.

Report unacceptable behavior privately to **conduct@example.com** (replace with a real address).
"""

CHANGELOG_MD = """\
# Changelog

All notable changes are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Initial changelog.
"""

DEPENDABOT_YML = """\
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
"""

DOCS_INDEX_MD = """\
# Documentation

The README is the landing page; deep docs live here.

## Index

- (add links to your architecture, configuration, and guide pages)
"""

AGENTS_MD = """\
# AGENTS.md — conventions for AI coding agents

## Build / test / lint

```bash
# replace with the exact commands for this project:
make install   # or: pip install -e ".[dev]" / npm ci
make test      # or: pytest -q / npm test
make lint      # or: ruff check . / npm run lint
```

## Conventions

- (project-specific rules an agent must follow to contribute correctly)
"""

LLMS_TXT = """\
# (project name)

> One-paragraph summary: what this is, who it serves, and the one command that
> proves it works. Agents read this file first — keep it under 10 KB.

## Quickstart

```bash
# the install + hello-world commands, exactly as a cold-start reader would run them
```

## Key files

- [README](README.md) — landing page
- (link the API/CLI reference and the config schema)
"""


def _create(path: str, content: str) -> list[Mutation]:
    return [Mutation(action="create_file", path=path, content=content)]


@fix("security-policy")
def fix_security_policy(ctx: Context) -> list[Mutation]:
    return _create("SECURITY.md", SECURITY_MD)


@fix("contributor-door")
def fix_contributing(ctx: Context) -> list[Mutation]:
    return _create("CONTRIBUTING.md", CONTRIBUTING_MD)


@fix("code-of-conduct")
def fix_code_of_conduct(ctx: Context) -> list[Mutation]:
    return _create("CODE_OF_CONDUCT.md", CODE_OF_CONDUCT_MD)


@fix("changelog")
def fix_changelog(ctx: Context) -> list[Mutation]:
    return _create("CHANGELOG.md", CHANGELOG_MD)


@fix("dependabot")
def fix_dependabot(ctx: Context) -> list[Mutation]:
    return _create(".github/dependabot.yml", DEPENDABOT_YML)


@fix("docs-index")
def fix_docs_index(ctx: Context) -> list[Mutation]:
    return _create("docs/README.md", DOCS_INDEX_MD)


@fix("ai-door")
def fix_ai_door(ctx: Context) -> list[Mutation]:
    # Both halves of the AI door: standing instructions (AGENTS.md) and the
    # machine entry point (llms.txt). A malformed-but-present llms.txt is
    # llms-txt-shape's FAIL and deliberately has no auto-fix — that's a human's
    # judgment call.
    return _create("AGENTS.md", AGENTS_MD) + _create("llms.txt", LLMS_TXT)
