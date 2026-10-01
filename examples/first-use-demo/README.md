# First-use demo: a wheel that installs but cannot greet its user

Run from the Invigil checkout using the environment containing the new wheel verifier:

```bash
.venv/bin/python examples/first-use-demo/run.py
```

This feature is currently unreleased; the existing PyPI version does not include it.
The script needs the checkout installed in that environment and Python's venv/pip
support. It builds tiny synthetic wheels with the standard library and installs
without package indexes. No API key, model, Docker, or external project is required.

The source checkout contains a greeting function and `greeting.txt`, so its source
check passes. The broken wheel omits that data file. Installation succeeds, but
calling the installed function fails with `FileNotFoundError`. The repaired wheel
includes the file; the identical first-use check passes.

Expected summary:

| Check | Broken wheel | Repaired wheel |
|---|---|---|
| Environment creation | PASS | PASS |
| Installation | PASS | PASS |
| Dependency inventory | PASS | PASS |
| First-use operation | FAIL | PASS |

The script invokes the real `invigil stranger` CLI for both cases and verifies
its exit codes and JSON outcomes. Its own exit code is zero only if the expected
failure and repaired success both occur. It prints the actual failing path and
leaves wheel files, configuration and JSON evidence in the displayed unique
`/tmp/invigil-first-use-demo-*` directory. `comparison.json` contains both reports.
The fixture-specific fix displayed by the demo is authored explanation; it is not
an automatically inferred fix from Invigil.

This is a controlled packaging example, not a reproduced upstream bug or proof
that ordinary smoke tests cannot catch the same defect. The proposed benefit is
repeatable installation checks and consistent diagnostics. A venv is not a
security boundary for arbitrary third-party code.
