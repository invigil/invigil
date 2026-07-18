# Good First Issues to Seed

*Copy and paste these into new GitHub issues on `invigil/invigil` and apply the `good first issue` label.*

---

## 1. Add `--quiet` flag to CLI to suppress non-failing output
**Description**: Currently, `invigil score .` prints the full scorecard. For CI environments where users only want to see the failures, a `--quiet` or `-q` flag would be extremely helpful.
**Acceptance Criteria**:
- Add `-q/--quiet` to the `argparse` setup in `src/invigil/cli.py`.
- If set, only print checks that have `Status.FAIL` or `Status.WARN`.
- The final summary line (Gate, Grade, Score) should still be printed.
**Local Verify**: Run `uv run invigil score . -q` and verify passing checks are hidden.

---

## 2. Support YAML arrays for `disabled_checks` in `.invigil.yml`
**Description**: Right now, disabling checks in `.invigil.yml` uses a dictionary syntax under `checks.disable`. We should support a standard YAML list as well to make it more intuitive.
**Acceptance Criteria**:
- Modify `config.py` to accept either a list of strings or the existing structure for `checks.disable`.
- Add a test case in `tests/test_config.py`.
**Local Verify**: Create a `.invigil.yml` with a list format for `disable`, run `uv run invigil score .`, and verify the check is skipped.

---

## 3. Implement a `format=junit` reporter
**Description**: We currently support `text`, `json`, and `markdown` output formats. To integrate natively with GitLab CI and Jenkins, we need a JUnit XML output format.
**Acceptance Criteria**:
- Add a `junit` option to the `--format` flag.
- Add a new function in `report.py` that maps `CheckResult` to JUnit XML. `PASS` is a passing test, `FAIL` is a `<failure>`, `SKIP` is a `<skipped>`.
- Add tests in `tests/test_report.py`.
**Local Verify**: Run `uv run invigil score . --format junit` and verify valid XML is emitted.

---

## 4. Add `weight` override validation
**Description**: The `.invigil.yml` allows overriding check weights via `checks.weights`. However, we don't validate if the user provides a negative weight or a string.
**Acceptance Criteria**:
- Update `config.py` to ensure all values in `checks.weights` are positive integers.
- If an invalid weight is found, log a warning and fall back to the default weight.
**Local Verify**: Put a negative weight in `.invigil.yml`, run the tool, and ensure a warning is printed and the app doesn't crash.

---

## 5. Add `duration` to JSON output
**Description**: We want to track how long checks take to execute, especially for `network` and `heavy` layers.
**Acceptance Criteria**:
- Modify `run_all` in `checks/__init__.py` to track the execution time (in milliseconds) of each check callback.
- Add a `duration_ms` field to `CheckResult` in `model.py`.
- Update the `json` output format in `report.py` to include this field.
**Local Verify**: Run `uv run invigil score . --format json` and verify the `duration_ms` field exists and is populated.
