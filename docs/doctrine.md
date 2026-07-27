# The doctrine

Invigil encodes a specific product-quality doctrine — the **Silent User Doctrine** and its
Five Disciplines. The premise:

> Absence of complaints is not absence of problems. Silence is the loudest negative signal
> a project gets.

Users who bounce don't file issues. They close the tab. You tested at release time; they
arrive months later, after dependencies drifted, registries changed, and the install path
you verified once quietly stopped working. Only automation is awake then. Invigil is that
automation.

## The Gates

Each Gate is a legibility promise to a different cold-start reader — the table lives in
the [README](../README.md#why) so it stays on the landing page where a stranger meets it.

Two things the table doesn't say. First, a repo *reaches* `Gn` only when every mandatory
check for gates ≤ n passes; the letter grade is separate, computed from the weighted score
across everything that ran. You can hold G3 with a B, or fail G3 with an A on volume of
passing checks — the gate is the floor and the letter is the finish.

Second, G1–G5 are mechanically checkable from the repo. **G6 and G7 are earned, not
configured** — an external contributor merging without hand-holding, and someone you don't
control choosing to depend on you. No amount of scaffolding fakes those, which is why they
sit at the top.

## Why every FAIL carries a fix

A gate that can't tell you how to pass it is the same broken-error-message anti-pattern
it exists to catch. So every check returns *what's wrong, why it matters, and the exact
command or edit that fixes it* — enforced in the check model itself
([`src/invigil/model.py`](../src/invigil/model.py)); a `FAIL` without a `fix` is a bug.

## Bending it without forking it

Doctrine you can't tune is doctrine people bypass, and a gate developers bypass is dead
weight. `.invigil.yml` gives you the dials:

- **Profiles** — `profile: strict | progressive | light`. `progressive` (report-only) is
  the adoption default: see the grade for weeks, flip `enforce: true` when it's stable.
- **Per-check `weights`** — decide what actually matters to your project.
- **`optional: true`** — a check that dings the score without gating the build.
- **`thresholds.fail_on`** — where your line sits, not where ours does.
- **`checks.disable`** — turn off what doesn't apply. Grade honestly; a disabled check is
  visible in the report.

Full field reference: [`schema/invigil.schema.json`](../schema/invigil.schema.json) and
[`examples/`](../examples/).

## Resilient by design

A check that crashes the build teaches people to remove the check. Two rules follow:

- **Network failures SKIP, never FAIL.** A scorecard.dev timeout is excluded from the
  grade entirely — never a false A-to-C downgrade, never a red build for someone else's
  outage.
- **A crashing check becomes a WARN.** The registry wraps exceptions, so a bug in one
  check can't take down the run.

Checks are tagged `local` / `network` / `heavy`, so you can slice the run to fit where
it's running: `--offline`, `--layer local`, `--group supply-chain`. The filesystem checks
finish in ~120ms, which is what makes the pre-commit hooks usable.

## AI-era native

Legibility now has two audiences, and the second one arrives with a context window
instead of patience. The `ai` check group grades whether an agent can *act* on your repo,
not merely whether `llms.txt` exists — see
[When your user is an agent](../README.md#when-your-user-is-an-agent) in the README for
the full check table.

The `agent-scope-visibility` check is the first slice of a harder question the ecosystem
hasn't answered yet: *what's the blast radius if this agent is prompt-injected?* Agent
code that declares its tool inventory can at least be reasoned about.
