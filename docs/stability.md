# What Invigil promises not to break

Invigil is **Alpha** (`Development Status :: 3 - Alpha`), and that is a deliberate,
accurate label rather than modesty. This page says exactly what it means for you, because
"Alpha" on its own tells you nothing you can plan around — and a tool that grades other
projects on legibility owes you a straight answer about its own.

Every report Invigil emits carries a **`doctrine_version`** (`doctrine=N` in
`--format llm`, `doctrine_version` in `--format json`). It is independent of the package
version and it moves whenever a change could alter your verdict without you changing
anything.

## Stable — build on these

These are the surfaces automation should depend on. Breaking any of them is a major
version bump with a deprecation period, Alpha or not.

| Surface | Contract |
|---|---|
| **CLI invocation** | `invigil score`/`evaluate`, `check`, `stranger`, `portfolio`, `mcp` and their documented flags keep working. New flags may be added. |
| **Exit codes** | `0` ok · `1` below gate / failures found · `2` usage error · `3` refused (CI lockout). Enforced by a test that reads `docs/cli-reference.md` — if the code can return it, the table documents it. |
| **JSON report shape** | Top-level keys and the per-check object keys are additive-only. New keys may appear; existing ones do not change meaning or disappear. |
| **Badge JSON** | `--format badge` and `--format ai-badge` emit the shields.io endpoint shape. |
| **MCP tool names and signatures** | `evaluate_repo`, `check_group`, `preview_fixes`. All three are read-only; `preview_fixes` returns a plan and never writes. |
| **`.invigil.yml` v1** | Fields in [the schema](../schema/invigil.schema.json) keep working. A test keeps the schema in sync with the code, so it cannot silently drift. |

## Not stable — read, don't gate on

This is the doctrine itself, and it is *supposed* to move. Invigil is only worth running if
its findings are true, so a finding that turns out to be wrong gets fixed rather than
preserved for compatibility.

- **Individual check verdicts.** A check may go FAIL → WARN → PASS as its accuracy improves.
- **Which checks exist**, their **weights**, whether they are **mandatory**, and their
  **gate** assignment.
- **The letter grade and the gate level**, which are derived from all of the above.
- **Profile contents** — which checks a profile treats as advisory or zero-weight.

Recent example, and the reason this page exists: in July 2026 `no-tracked-secrets` moved
from FAIL to WARN for key material under test paths, because it had been reporting
published TLS certificates as leaked secrets. That was a behaviour change for anyone
running `enforce: true`. It was also unambiguously the right change. **That trade is what
Alpha buys.**

### How to depend on Invigil safely today

- **Do** parse the JSON report, store it, and diff it over time.
- **Do** branch on exit codes.
- **Do** record `doctrine_version` alongside any stored score — it is how you tell *"our
  repo regressed"* apart from *"the ruler moved"*. Without it that distinction is
  unrecoverable.
- **Don't** hard-code a numeric score or letter grade as a pass threshold across upgrades.
- **Don't** gate a release on one specific check id until it reaches Beta.
- **Do** use `profile: progressive` (the default, report-only). `strict` is for repos that
  have accepted the doctrine deliberately.

## What Beta requires

Beta is not a date — it is a set of conditions. Invigil moves to
`Development Status :: 4 - Beta` when all of these hold:

1. **A published false-positive rate.** 30+ real third-party repos scored, every finding
   manually audited, the per-check error rate published with its methodology and known
   limits. Until Invigil can state how often it is wrong, nobody should gate on it.
   In progress and published as it stands in
   [How often Invigil is wrong](false-positives.md) — 27 repos of 30, 331 of 402
   findings still unaudited, so this condition is **not yet met**.
2. **Two consecutive minor releases with no `doctrine_version` bump.** The doctrine has to
   demonstrate it has settled, not merely assert it.
3. **Bus factor above one.** A second maintainer with commit and release rights, or a
   documented and exercised handover. This is the honest blocker for enterprise adoption,
   and no classifier string substitutes for it.

Until then the Alpha label stands. It is not a disclaimer to route around — it is the
accurate description of a tool whose ruler is still being calibrated, published by a
project that would rather say so than be found out.
