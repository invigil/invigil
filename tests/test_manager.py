"""B5 — Tests for manager.py (all four pipeline stages + integration).

Each test targets one specific function in isolation so failures are easy to
diagnose. The integration test at the bottom proves the full pipeline works
end-to-end with a real plugin file.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from invigil.checks import REGISTRY, run_all
from invigil.config import InvigilConfig
from invigil.context import Context
from invigil.manager import (
    PluginLoadError,
    build_registry,
    discover_plugins,
    load_plugin,
    merge_registry,
    validate_manifest,
)
from invigil.model import Check, Status

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_plugin(plugin_dir: Path, name: str, content: str) -> Path:
    plugin_dir.mkdir(parents=True, exist_ok=True)
    p = plugin_dir / name
    p.write_text(content)
    return p


MINIMAL_PLUGIN = """\
def invigil_register_check():
    from invigil.model import Check, CheckResult, Status

    def _check(ctx):
        check = Check(id="hello-world", gate="G1", title="Hello World",
                      layer="local", group="layout")
        return CheckResult(check, Status.PASS, "hello")

    return [{
        "id": "hello-world",
        "gate": "G1",
        "title": "Hello World",
        "layer": "local",
        "group": "layout",
        "effort": "minutes",
        "check_callback": _check,
    }]
"""

BAD_IMPORT_PLUGIN = """\
import this_module_does_not_exist_xyz
"""

NO_FUNCTION_PLUGIN = """\
def some_other_function():
    pass
"""

BAD_MANIFEST_PLUGIN = """\
def invigil_register_check():
    return [{"id": "broken"}]   # missing required keys
"""

RAISING_CALL_PLUGIN = """\
def invigil_register_check():
    raise RuntimeError("boom in register")
"""


# ---------------------------------------------------------------------------
# Stage 1 — discover_plugins
# ---------------------------------------------------------------------------


def test_discover_no_plugin_dir(tmp_path):
    """No .invigil/plugins/ → empty list."""
    assert discover_plugins(tmp_path) == []


def test_discover_finds_py_files(tmp_path):
    plugin_dir = tmp_path / ".invigil" / "plugins"
    _write_plugin(plugin_dir, "alpha.py", "")
    _write_plugin(plugin_dir, "beta.py", "")
    (plugin_dir / "not_a_plugin.txt").write_text("")
    found = discover_plugins(tmp_path)
    assert [p.name for p in found] == ["alpha.py", "beta.py"]  # sorted


def test_discover_empty_plugin_dir(tmp_path):
    (tmp_path / ".invigil" / "plugins").mkdir(parents=True)
    assert discover_plugins(tmp_path) == []


# ---------------------------------------------------------------------------
# Stage 2 — load_plugin
# ---------------------------------------------------------------------------


def test_load_plugin_success(tmp_path):
    p = _write_plugin(tmp_path, "good.py", MINIMAL_PLUGIN)
    module = load_plugin(p)
    assert hasattr(module, "invigil_register_check")
    assert callable(module.invigil_register_check)


def test_load_plugin_bad_import_raises(tmp_path):
    p = _write_plugin(tmp_path, "bad.py", BAD_IMPORT_PLUGIN)
    with pytest.raises(PluginLoadError, match="import error"):
        load_plugin(p)


def test_load_plugin_no_function_raises(tmp_path):
    p = _write_plugin(tmp_path, "nofn.py", NO_FUNCTION_PLUGIN)
    with pytest.raises(PluginLoadError, match="invigil_register_check"):
        load_plugin(p)


# ---------------------------------------------------------------------------
# Stage 3 — validate_manifest
# ---------------------------------------------------------------------------


def _minimal_manifest(**overrides) -> dict:
    base = {
        "id": "test-check",
        "gate": "G2",
        "title": "Test check",
        "layer": "local",
        "group": "layout",
        "check_callback": lambda ctx: None,
    }
    base.update(overrides)
    return base


def test_validate_manifest_valid():
    m = validate_manifest(_minimal_manifest())
    assert m["id"] == "test-check"
    assert m["effort"] == "hours"  # default applied
    assert m["severity"] == "standard"  # default applied
    assert m["mandatory"] is True  # default applied


def test_validate_manifest_missing_key():
    bad = _minimal_manifest()
    del bad["id"]
    with pytest.raises(ValueError, match="missing required keys"):
        validate_manifest(bad)


def test_validate_manifest_bad_gate():
    with pytest.raises(ValueError, match="invalid gate"):
        validate_manifest(_minimal_manifest(gate="Z9"))


def test_validate_manifest_bad_layer():
    with pytest.raises(ValueError, match="invalid layer"):
        validate_manifest(_minimal_manifest(layer="cosmic"))


def test_validate_manifest_bad_effort():
    with pytest.raises(ValueError, match="invalid effort"):
        validate_manifest(_minimal_manifest(effort="weeks"))


def test_validate_manifest_bad_severity():
    with pytest.raises(ValueError, match="invalid severity"):
        validate_manifest(_minimal_manifest(severity="critical"))


def test_validate_manifest_non_callable_callback():
    with pytest.raises(ValueError, match="check_callback.*callable"):
        validate_manifest(_minimal_manifest(check_callback="not callable"))


def test_validate_manifest_non_callable_fix_callback():
    with pytest.raises(ValueError, match="fix_callback.*callable"):
        validate_manifest(_minimal_manifest(fix_callback="not callable"))


def test_validate_manifest_source_in_error(tmp_path):
    bad = _minimal_manifest()
    del bad["gate"]
    with pytest.raises(ValueError, match=r"\[myplugin\.py\]"):
        validate_manifest(bad, source="myplugin.py")


# ---------------------------------------------------------------------------
# Stage 4 — merge_registry
# ---------------------------------------------------------------------------


def _make_pair(check_id: str, gate: str = "G1") -> tuple[Check, object]:
    check = Check(id=check_id, gate=gate, title=check_id)
    return (check, lambda ctx: None)


def test_merge_no_extras():
    builtins = [_make_pair("a"), _make_pair("b")]
    merged = merge_registry(builtins, [])
    assert merged == builtins


def test_merge_adds_extras():
    builtins = [_make_pair("a")]
    extras = [_make_pair("b"), _make_pair("c")]
    merged = merge_registry(builtins, extras)
    ids = [check.id for check, _ in merged]
    assert ids == ["a", "b", "c"]


def test_merge_dedup_builtin_wins(caplog):
    import logging

    builtins = [_make_pair("a")]
    extras = [_make_pair("a")]  # same id as builtin
    with caplog.at_level(logging.WARNING, logger="invigil.manager"):
        merged = merge_registry(builtins, extras)
    ids = [check.id for check, _ in merged]
    assert ids == ["a"]  # only one 'a'
    assert "shadows builtin" in caplog.text


# ---------------------------------------------------------------------------
# Top-level — build_registry
# ---------------------------------------------------------------------------


def test_build_no_plugin_dir_returns_builtins(tmp_path):
    registry, warns = build_registry(tmp_path, builtins=REGISTRY)
    assert registry is not REGISTRY  # new list
    assert len(registry) == len(REGISTRY)
    assert warns == []


def test_build_broken_import_emits_warn(tmp_path):
    _write_plugin(tmp_path / ".invigil" / "plugins", "broken.py", BAD_IMPORT_PLUGIN)
    registry, warns = build_registry(tmp_path, builtins=REGISTRY)
    assert len(warns) == 1
    assert warns[0].status == Status.WARN
    assert "broken" in warns[0].check.id


def test_build_bad_manifest_emits_warn(tmp_path):
    _write_plugin(tmp_path / ".invigil" / "plugins", "badm.py", BAD_MANIFEST_PLUGIN)
    registry, warns = build_registry(tmp_path, builtins=[])
    assert any(w.status == Status.WARN for w in warns)


def test_build_raising_call_emits_warn(tmp_path):
    _write_plugin(tmp_path / ".invigil" / "plugins", "raise.py", RAISING_CALL_PLUGIN)
    registry, warns = build_registry(tmp_path, builtins=[])
    assert any(w.status == Status.WARN for w in warns)


# ---------------------------------------------------------------------------
# Integration — full pipeline: plugin appears in run_all()
# ---------------------------------------------------------------------------


def test_project_plugin_appears_in_run_all(tmp_path):
    """A valid project plugin check runs via run_all() and appears in results."""
    _write_plugin(tmp_path / ".invigil" / "plugins", "hello.py", MINIMAL_PLUGIN)
    ctx = Context(repo=tmp_path, config=InvigilConfig())
    results = run_all(ctx, offline=True)
    hello_results = [r for r in results if r.check.id == "hello-world"]
    assert len(hello_results) == 1
    assert hello_results[0].status == Status.PASS


def test_broken_plugin_emits_warn_not_crash(tmp_path):
    """A plugin that fails to import emits a WARN in run_all(), never crashes."""
    _write_plugin(tmp_path / ".invigil" / "plugins", "broken.py", BAD_IMPORT_PLUGIN)
    ctx = Context(repo=tmp_path, config=InvigilConfig())
    results = run_all(ctx, offline=True)
    warn_results = [r for r in results if r.status == Status.WARN]
    assert len(warn_results) >= 1
    assert any("broken" in r.check.id for r in warn_results)
