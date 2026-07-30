# Invigil Roadmap

Phased plan for the ecosystem defined in [ARCHITECTURE.md](ARCHITECTURE.md). Invigil dogfoods
its own doctrine, so each phase is expected to hold or raise Invigil's own gate level.

## Shipped — v1.x ✅

- **Static Doctrine Scorecard** — ~25 checks across Gates G1–G5 + Tier-1 secrets; weighted
  score → gate level + letter grade; every failure prints the exact fix. Text / JSON / Markdown
  / shields-badge output.
- **Cold-Start Gate** — `invigil stranger` boot-and-probe engine + reusable workflow; HTTP web
  services *and* CLI images (`command:` → run to completion, exit 0).
- **Modular + offline** — checks tagged `local`/`network`/`heavy`; `invigil check <group>` runs
  one group offline (~120 ms) for pre-commit; `--offline`/`--layer`/`--group` slicing.
- **Profiles + overrides** — `strict`/`progressive`/`light` + `.invigil.yml`
  `weights`/`optional`/`thresholds.fail_on` (bend the doctrine, don't fork it).
- **Resilience** — a network flake is a SKIP excluded from the grade; never a false downgrade.
- **AI-native `ai` group** — `llms-no-secrets` + `agent-scope-visibility` (the statically-honest
  slice of "agent blast radius").
- **Cross-repo portfolio** — `invigil portfolio` grade table + per-repo endpoint badges.
- **Supply chain** — cosign-signed wheel / sdist / GHCR image + SPDX SBOM; four distribution
  channels (PyPI / Action / Docker / pre-commit); moving `v1` tag maintained per release.

## Phase A — the `invigil fix` engine ✅ (shipped v1.2.0)

Turned the gate into a proactive fixer. `src/invigil/mutator.py` (safe create/append/replace/delete
broker, path-jailed + logged), `checks.FIXES` (fixes for the missing-governance-file checks),
`fixer.py` (the **single-pass rule**), a `--fix` flag on `score`/`check`, and **CI-lockout**
(`--fix` exits 3 when `CI=true`). Self-contained; no registry break.

## Phase B — plugin architecture ✅ (shipped v1.3.0)

`hookspecs.py` (`InvigilPlugin` Protocol) + `manager.py` (discovery/validation/registry) —
zero-dependency (`importlib`, not pluggy); project plugins in `.invigil/plugins/*.py`, broken
plugins degrade to WARN. Profiles externalized to `src/invigil/profiles/*.json`. Also shipped:
effort/blocker check model, badge subtitles, OSS positioning (`license-present` blocker split
from advisory `license-apache2`).

**Still open from the original Phase B scope:** polyglot script plugins (JSON stdin/stdout for
non-Python hooks) and pre-commit `additional_dependencies` for third-party plugin packages —
deferred until there is a real external plugin author.

## Phase C — org topology 🟡 (scaffolded)

Sibling repos exist under `github.com/invigil` (`invigil.dev`, `plugin-template`,
`awesome-invigil`) and the three teams are created (`core-maintainers`,
`ecosystem-reviewers`, `automation-bots`). **All three are private as of 2026-07-30** —
they were public scaffolds with no content, which is the silent failure this project exists
to catch. Each goes public when it has something to say. `github-action` is **retired**: the
core repo's `action.yml` already serves `uses: invigil/invigil@v1` and backs the Marketplace
listing, so a second action repo could only drift out of sync (see `ARCHITECTURE.md`).
Pending: real content in each repo (docs site deploy, working plugin-template CI, catalog
criteria), branch protection + CODEOWNERS.

## Phase E — AI-legibility ✅ (shipped v1.5.0)

**Legibility's second audience.** The primary reader of a repo is increasingly an AI agent —
a context window instead of patience, exit codes instead of intuition. v1.5.0 grades the
machine-readable surface for *actionability*, not just presence: `agents-md-actionable`,
`llms-txt-shape`, `agent-context-fresh`, `readme-heading-hierarchy`, `exit-codes-documented`
(all group `ai`, statically honest, SKIP when not applicable), plus an `ai-ready` shields
badge and `invigil score --format llm` — a sub-1 KB deterministic report built to be read by
an agent.

## Phase F — fix-by-PR bot ✅ (shipped v1.6.0)

Dependabot-for-legibility: the reusable `fix-pr.yml` workflow applies mechanical fixes on a
stable `invigil/fixes` branch and opens one batched PR. Anti-noise by design: opt-in only,
one PR, a closed-unmerged PR is a "no" the bot respects. Enabled by `--fix --pr-mode`, a
scoped CI-lockout exemption that still refuses the default branch. The scaffolded
`AGENTS.md`/`llms.txt` templates now recruit agents (`invigil evaluate . --format llm`
as the pre-PR step) — every adopting repo teaches future agents to run the gate.

**Next (v1.7.0):** an MCP server (`invigil mcp`, stdio, optional `[mcp]` extra) + a
published agent skill + registry listings (MCP registries; pre-commit.com hooks listing);
`docs-commands-exist` once the false-positive story is designed. Phase 2 of the bot — a
hosted GitHub App (`invigil[bot]`, Checks API annotations) — waits for adoption signal.

## Maturity criteria (Invigil grading itself)

Invigil is category-credible when it passes its own gates: **G3** requires v1.3.0 published on
PyPI + GHCR with nightly smoke green; **G4** requires OpenSSF Scorecard ≥ 7 — **met: 7.2 on
the 2026-07-30 crawl** (signing, SBOM, SHA-pinned actions and hash-pinned build requirements
all landed; watch for regressions when workflows change — a new unpinned `pip install` slips
the score); **G5** (all five doors documented).
