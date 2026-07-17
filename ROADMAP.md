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

## Phase B — plugin architecture (pluggy) ⬜

`hookspecs.py` (`invigil_register_check() -> manifest`) + `manager.py` (discovery/sort/registry);
migrate the `checks/*` registry onto pluggy; **polyglot** script plugins in `.invigil/plugins/`
(JSON stdin/stdout); pre-commit `additional_dependencies` for third-party plugin packages.
Externalize `engine.py` presets to `profiles/*.json`.

## Phase C — org topology ⬜

Stand up the sibling repos under `github.com/invigil`: `github-action` (Marketplace wrapper),
`invigil.dev` (doctrine site), `plugin-template`, `awesome-invigil`; create the three teams
(`core-maintainers`, `ecosystem-reviewers`, `automation-bots`).

## Maturity criteria (Invigil grading itself)

Invigil is category-credible when it passes its own gates: G3 today (published artifacts
machine-verified daily), targeting **G4** (Scorecard ≥ 7 + signed releases + SBOM — signing and
SBOM done; Scorecard score pending) and **G5** (all five doors documented).
