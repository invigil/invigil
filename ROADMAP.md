# Invigil Roadmap

Phased plan for the ecosystem defined in [ARCHITECTURE.md](ARCHITECTURE.md). Invigil dogfoods
its own doctrine, so each phase is expected to hold or raise Invigil's own gate level.

## Shipped — v1.x ✅

- **Static Doctrine Scorecard** — ~25 checks across Gates G1–G5 + Tier-1 secrets; weighted
  score → gate level + letter grade; every failure prints the exact fix. Text / JSON / Markdown
  / shields-badge output.
- **Stranger Gate** — `invigil stranger` boot-and-probe engine + reusable workflow; HTTP web
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

Sibling repos exist under `github.com/invigil` (`github-action`, `invigil.dev`,
`plugin-template`, `awesome-invigil`) and the three teams are created (`core-maintainers`,
`ecosystem-reviewers`, `automation-bots`). Pending: real content in each repo (docs site
deploy, working plugin-template CI, catalog criteria), branch protection + CODEOWNERS, and a
decision on whether `github-action` stays (the core repo's `action.yml` already serves
`uses: invigil/invigil@v1`).

## Maturity criteria (Invigil grading itself)

Invigil is category-credible when it passes its own gates: **G3** requires v1.3.0 published on
PyPI + GHCR with nightly smoke green; **G4** requires OpenSSF Scorecard ≥ 7 (signing and SBOM
done; today's score is 5.2 — branch protection, workflow token permissions, SAST, and full
dependency pinning are the actionable gaps, while Maintained/Contributors need calendar time);
**G5** (all five doors documented).
