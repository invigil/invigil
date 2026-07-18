# Invigil documentation

The [README](../README.md) is the landing page. Deep docs live here.

## Index

- [The doctrine and the Gates](doctrine.md) — what G1–G7 mean and why they're the
  checks that matter.
- [Writing checks](writing-checks.md) — the `Check` / `CheckResult` model, the
  registry, and the "every FAIL carries a fix" rule.
- [`.invigil.yml` reference](config.md) — every field, with the schema and examples.
- [The Cold-Start Gate](stranger-gate.md) — the reusable workflow that boots and probes
  your published artifacts.

> These pages are stubs pending the C-track build-out; the authoritative reference
> today is the [`.invigil.yml` JSON schema](../schema/invigil.schema.json), the
> [examples](../examples/), and [AGENTS.md](../AGENTS.md).
