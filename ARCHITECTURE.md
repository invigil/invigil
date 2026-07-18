# Invigil Architecture & Ecosystem Blueprint

Structural, architectural, and governance specification for the Invigil ecosystem: the GitHub
organization topology, the core engine, the local-first plugin engine, and the structured
auto-fix mutation loop.

> **Status legend:** ✅ shipped · 🟡 partial · ⬜ planned (see [ROADMAP.md](ROADMAP.md) for
> sequencing). Sections below describe the target design; the legend marks where today's code
> already meets it.

---

## 1. GitHub organization topology

To scale cleanly while keeping an ultra-fast core engine, the [github.com/invigil](https://github.com/invigil)
org isolates distribution layers, developer tools, and community extensions into decoupled,
domain-driven repositories.

```
github.com/invigil/
├── invigil           # ✅ Core Python engine, CLI, base profiles, Docker recipe, Action
├── github-action     # ⬜ Isolated GitHub Marketplace deployment wrapper
├── invigil.dev       # ⬜ Static docs site for the Silent User Doctrine
├── plugin-template    # ⬜ Boilerplate repo for third-party plugin developers
└── awesome-invigil   # ⬜ Community-curated catalog of verified profiles and plugins
```

### Teams & permissions
- **@invigil/core-maintainers** — full admin/write across all repos; handles release signing.
- **@invigil/ecosystem-reviewers** — write to `awesome-invigil` and `plugin-template`; audit
  third-party plugin submissions.
- **@invigil/automation-bots** — machine users bound to OIDC for automated registry pushes.

---

## 2. Core repository structure (`invigil/invigil`)

A lean engine monorepo. Standard gate validators ship as core-packaged plugins; dev fixtures are
decoupled from production modules.

```
invigil/invigil/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml               # ✅ unit tests, lint, self-score, PyPI/GHCR staging
│   │   ├── stranger-gate.yml    # ✅ reusable Cold-Start Gate workflow for nightly artifact smoke runs
│   │   └── self-score.yml       # 🟡 (today: a `self-score` job inside ci.yml)
│   └── ISSUE_TEMPLATE/          # ⬜
├── src/invigil/
│   ├── cli.py               # ✅ arg parsing, context flags (--offline, --fix)
│   ├── hookspecs.py         # ✅ extension boundaries (typing.Protocol, no deps)
│   ├── manager.py           # ✅ plugin discovery, sorting, runtime registry
│   ├── mutator.py           # ✅ safe file-system mutation broker for the fix engine
│   ├── gates/               # 🟡 (today: checks/ modules, @register + central TAGS)
│   └── profiles/            # ✅ JSON config profiles (strict, progressive, light)
├── schema/invigil.schema.json   # ✅ validation contract for .invigil.yml
├── hooks/                       # 🟡 (today: pre-commit entries via `invigil check <group>`)
├── tests/{unit,fixtures}/       # 🟡 (today: flat tests/ ; add deliberately-broken fixtures)
├── Dockerfile                   # ✅ multi-stage recipe for ghcr.io
├── pyproject.toml               # ✅ (hatchling build backend, not poetry)
└── README.md                    # ✅
```

---

## 3. Local-first plugin architecture (✅ shipped v1.3.0)

Invigil uses a **structured, zero-dependency plugin system** via native `importlib` and a `typing.Protocol` contract, decoupling the engine from specific frameworks and letting developers run custom rules offline before pushing. No heavy dependencies like `pluggy` — keeping Invigil fast and light.

### Execution-context classification
Every check declares a performance profile so the engine can filter heavy/remote work out of
fast pre-commit runs.

- **local** — zero network, target < 50 ms (schema/layout validation, secret footprint checks).
- **network** — external reads, target < 2 s (PyPI status, Scorecard lookups).
- **heavy** — prolonged orchestration (the 10-minute Cold-Start Gate container bootstrap).

### The Python extension contract (`hookspecs.py`)
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class InvigilPlugin(Protocol):
    def invigil_register_check(self) -> list[dict]:
        """Return one manifest dict per check.
        {
            "id": "plugin-identifier",
            "gate": "G1".."G7",
            "title": "Human readable title",
            "layer": "local" | "network" | "heavy",
            "group": "layout" | "secrets" | "ai",
            "check_callback": callable,
            "fix_callback": callable,  # optional
        }
        """
```

### Polyglot script context (external binaries)
Non-Python hooks communicate via **JSON-in / JSON-out over stdin/stdout**. A script in the
project's `.invigil/plugins/` folder is invoked directly.

**stdin:**
```json
{ "repo_root": "/abs/path/to/project", "execution_layer": "local", "config": {} }
```

**stdout:**
```json
{
  "passed": false,
  "gate": "G2",
  "reason": "Missing public error directory mapping standard exit codes.",
  "mutation": { "action": "create_file", "path": "docs/errors.md", "content": "# Error Codes\n..." }
}
```

---

## 4. Pre-commit integration lifecycle (🟡 partial)

Third-party plugins load through isolated pre-commit configs — no global installs. `pre-commit`
sets everything up in an isolated venv via `additional_dependencies`:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/invigil/invigil
    rev: v1                       # tracks the latest v1.x.y
    hooks:
      - id: invigil-layout
        additional_dependencies:
          - invigil-plugin-corporate-policy==2.1.0
          - invigil-plugin-rust-checks==0.4.2
```

On commit, `invigil` runs with `--offline`, matches only `local` plugin hooks, evaluates, and
hands control back to git within milliseconds. (Today: `invigil check layout`/`secrets` run
offline in ~120 ms; `additional_dependencies` plugin injection is planned with §3.)

---

## 5. The `invigil fix` engine (✅ shipped v1.2.0 — Phase A)

Shifts Invigil from an enforcement gate into a proactive correction tool. Evaluation is separated
from mutation to protect developers from destructive behavior.

### The automated pre-commit fixing loop
```
[git commit] → [Invigil hook] → [gate fails]
     → [execute structured mutation] → [stage changed files] → [abort commit, exit 1]
     → [developer reviews] → [git add && git commit] → [passes]
```

### Safe file-system mutations
Plugins never execute arbitrary shell. They return **structured intents** to a central
orchestrator (`invigil/mutator.py`), which runs and logs every change. Four operations:
- **create_file** — create a path if absent; populate it.
- **append_file** — append structural config to an existing asset.
- **replace_string** — swap a localized regex target for a clean alternative.
- **delete_file** — unlink a redundant legacy layout/config.

### Defensive loop countermeasures
- **Single-pass rule** — after a fix module runs, the engine immediately re-runs that one check.
  A second consecutive failure breaks out, exits non-zero, and surfaces the unresolvable problem.
- **CI-lockout** — if `CI` is truthy, the `--fix` path hard-errors, so a misconfigured fix can
  never trigger cascading automated commits on a protected branch.

---

## 6. Supply chain & release security (✅ shipped)

To satisfy its own **G4** gate, every release artifact is transparently signed and verifiable via
OIDC keyless **Sigstore / cosign**:

```yaml
permissions:
  id-token: write   # keyless OIDC
  contents: write
  packages: write
steps:
  - run: python -m build
  - run: |
      cosign sign --yes "$IMAGE_URI"
      cosign sign-blob --yes --output-signature dist/invigil.whl.sig dist/invigil-*.whl
```

Every distribution target — the **PyPI package**, the **GHCR image**, and the **Action payload** —
ships an **SPDX SBOM** for full downstream supply-chain traceability. (Implemented in
`.github/workflows/release.yml`.)
