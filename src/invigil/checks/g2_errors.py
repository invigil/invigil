"""G2 — every failure mode tells the user the fix (Discipline D2).

Errors are a product surface: a deep-health/preflight surface that names missing
prerequisites before work starts, a global handler that returns a correlatable
id instead of a leaked traceback, and error-path tests written first. These are
detected heuristically from source; they're best-effort on non-Python stacks, so
the softer ones are non-mandatory.
"""

from __future__ import annotations

from ..context import Context
from ..model import CheckResult, Status
from . import register


@register(
    id="deep-health", gate="G2", title="Deep-health / dependency-preflight surface exists", weight=1, discipline="D2"
)
def deep_health(ctx: Context) -> CheckResult:
    check = deep_health.__invigil__  # type: ignore[attr-defined]
    if not ctx.is_web_service():
        return CheckResult(check, Status.SKIP, "not an HTTP service")
    # A health route that inspects deps, or a dedicated sysdeps/preflight module.
    has_module = bool(ctx.rglob("**/sysdeps.py") or ctx.rglob("**/preflight.py"))
    has_route = ctx.source_contains('"/health"', "'/health'", "/api/system/deps", "health?deep")
    if has_module or has_route:
        return CheckResult(check, Status.PASS, "sysdeps/health surface found")
    return CheckResult(
        check,
        Status.FAIL,
        "no deep-health / preflight surface",
        "add a /health?deep=1 endpoint (or a sysdeps.py) that reports missing prereqs with the install command",
    )


@register(
    id="error-correlation-id",
    gate="G2",
    title="Global handler returns a correlatable error id",
    weight=1,
    discipline="D2",
)
def error_correlation_id(ctx: Context) -> CheckResult:
    check = error_correlation_id.__invigil__  # type: ignore[attr-defined]
    if not ctx.is_web_service():
        return CheckResult(check, Status.SKIP, "not an HTTP service")
    has_handler = ctx.source_contains("exception_handler", "errorhandler", "add_exception_handler")
    has_id = ctx.source_contains("error_id", "correlation_id", "request_id", "trace_id")
    if has_handler and has_id:
        return CheckResult(check, Status.PASS, "global handler + correlation id found")
    return CheckResult(
        check,
        Status.FAIL,
        "no global handler with a correlation id",
        "add a global exception handler that logs a traceback under an error_id and returns that id (no leaked stack)",
    )


@register(
    id="error-path-tests",
    gate="G2",
    title="Error-path tests exist (write them first)",
    weight=1,
    mandatory=False,
    discipline="D2",
)
def error_path_tests(ctx: Context) -> CheckResult:
    check = error_path_tests.__invigil__  # type: ignore[attr-defined]
    named = bool(ctx.rglob("**/test_error*.py") or ctx.rglob("**/*error*_test.go"))
    tagged = ctx.source_contains("ERR-", suffixes=(".py", ".go", ".ts", ".js"))
    if named or tagged:
        return CheckResult(check, Status.PASS, "error-path tests found")
    return CheckResult(
        check,
        Status.FAIL,
        "no obvious error-path tests",
        "add tests for the failure modes (e.g. tests/test_error_surfacing.py), ideally before the fix",
    )
