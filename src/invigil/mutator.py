"""The safe file-system mutation broker for the `invigil fix` engine.

Fixes never run arbitrary shell. A check's fix returns *structured intents*
(`Mutation`s) and this broker is the only thing that touches the filesystem — it
validates every path stays inside the repo (no `..`/absolute escape), applies the
change idempotently, and logs it. That containment is the whole safety story:
a broken or hostile fix can only ever create/append/replace/delete inside the
target repo, and every action is auditable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

ACTIONS = ("create_file", "append_file", "replace_string", "delete_file")


class MutationError(RuntimeError):
    """A mutation was malformed or tried to escape the repo."""


@dataclass
class Mutation:
    action: str
    path: str
    content: str = ""  # create_file / append_file
    find: str = ""  # replace_string
    replace: str = ""  # replace_string

    @classmethod
    def from_dict(cls, d: dict) -> Mutation:
        """Build from a polyglot plugin's JSON `mutation` object."""
        return cls(
            action=d["action"],
            path=d["path"],
            content=d.get("content", ""),
            find=d.get("find", ""),
            replace=d.get("replace", ""),
        )


@dataclass
class Mutator:
    repo: Path
    dry_run: bool = False
    changed: list[str] = field(default_factory=list)  # repo-relative paths touched
    log: list[str] = field(default_factory=list)

    def _safe(self, rel: str) -> Path:
        """Resolve `rel` inside the repo, refusing any path that escapes it."""
        root = self.repo.resolve()
        target = (root / rel).resolve()
        if target != root and root not in target.parents:
            raise MutationError(f"path escapes the repo: {rel!r}")
        return target

    def apply(self, m: Mutation) -> bool:
        """Apply one mutation. Returns True if it changed anything (idempotent:
        a create/append that's already satisfied is a no-op returning False)."""
        if m.action not in ACTIONS:
            raise MutationError(f"unknown mutation action: {m.action!r}")
        target = self._safe(m.path)

        if m.action == "create_file":
            if target.exists():
                self.log.append(f"skip create_file (exists): {m.path}")
                return False
            if not self.dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(m.content)
            return self._record("create_file", m.path)

        if m.action == "append_file":
            existing = target.read_text(errors="replace") if target.exists() else ""
            if m.content and m.content in existing:  # already appended
                return False
            if not self.dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("a", encoding="utf-8") as f:
                    f.write(m.content)
            return self._record("append_file", m.path)

        if m.action == "replace_string":
            if not target.exists():
                raise MutationError(f"replace_string on a missing file: {m.path}")
            text = target.read_text(errors="replace")
            if m.find not in text:  # nothing to swap
                return False
            if not self.dry_run:
                target.write_text(text.replace(m.find, m.replace))
            return self._record("replace_string", m.path)

        # delete_file
        if not target.exists():
            return False
        if not self.dry_run:
            target.unlink()
        return self._record("delete_file", m.path)

    def _record(self, action: str, path: str) -> bool:
        self.changed.append(path)
        self.log.append(f"{action}: {path}")
        return True
