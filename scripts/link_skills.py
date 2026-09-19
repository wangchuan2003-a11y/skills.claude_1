#!/usr/bin/env python3
"""Preview or install registered skills without silently replacing local files."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]


def exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def plan_links(repo: Path, destination: Path, names: list[str] | None = None,
               replace: bool = False) -> list[tuple[Path, Path, str]]:
    repo = repo.resolve(strict=True)
    destination = destination.expanduser()
    if destination.is_symlink():
        raise ValueError("destination must not be a symlink")
    destination = destination.resolve()
    if destination == repo or repo in destination.parents:
        raise ValueError("destination must be outside this repository")
    if destination.exists() and not destination.is_dir():
        raise ValueError("destination must be a directory")
    registered = json.loads((repo / ".claude-plugin/plugin.json").read_text())["skills"]
    sources = {}
    for entry in registered:
        source = repo / entry
        if not source.resolve().is_relative_to(repo / "skills"):
            raise ValueError(f"registered skill escapes repository: {entry}")
        if any(part.is_symlink() for part in [source, *source.parents] if part != repo and repo in part.parents):
            raise ValueError(f"registered skill contains a symlink: {entry}")
        if not (source / "SKILL.md").is_file() or (source / "SKILL.md").is_symlink():
            raise ValueError(f"missing or symlinked SKILL.md: {entry}")
        if source.name in sources:
            raise ValueError(f"duplicate registered skill name: {source.name}")
        sources[source.name] = source.resolve()
    selected = sorted(sources) if names is None else names
    if not selected or len(selected) != len(set(selected)):
        raise ValueError("select at least one skill without duplicates")
    plan = []
    for name in selected:
        if name not in sources:
            raise ValueError(f"unknown or unregistered skill: {name}")
        source, target = sources[name], destination / name
        if target.is_symlink() and target.resolve() == source:
            action = "unchanged"
        elif exists(target):
            if not replace:
                raise ValueError(f"destination already exists; nothing changed: {target}; "
                                 "use --replace to back it up")
            action = "backup-and-link"
        else:
            action = "link"
        plan.append((source, target, action))
    return plan


def apply_links(plan: list[tuple[Path, Path, str]]) -> Path | None:
    """Back up conflicts by renaming; roll back our changes if linking fails."""
    pending = [(s, t, action) for s, t, action in plan if action != "unchanged"]
    if not pending:
        return None
    destination = pending[0][1].parent
    if destination.is_symlink() or destination.resolve() != destination:
        raise ValueError("destination changed after preview")
    # Recheck every conflict before creating anything.
    for source, target, action in pending:
        if action == "link" and exists(target):
            raise ValueError(f"destination appeared after preview: {target}")
        if action == "backup-and-link" and not exists(target):
            raise ValueError(f"destination disappeared after preview: {target}")
    destination.mkdir(parents=True, exist_ok=True)
    backup_root = None
    if any(action == "backup-and-link" for _, _, action in pending):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_root = destination.parent / f"{destination.name}-backup-{stamp}-{uuid.uuid4().hex[:8]}"
        backup_root.mkdir(exist_ok=False)
    changes = []
    try:
        for source, target, action in pending:
            backup = backup_root / target.name if action == "backup-and-link" else None
            if backup is not None:
                target.rename(backup)
            changes.append((source, target, backup))
            # Unlike ln -sfn, this fails if another file appeared at the target.
            target.symlink_to(source, target_is_directory=True)
    except OSError:
        for source, target, backup in reversed(changes):
            if target.is_symlink() and target.resolve() == source:
                target.unlink()
            if backup is not None and not exists(target):
                backup.rename(target)
        raise
    return backup_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=Path.home() / ".claude/skills")
    parser.add_argument("--skills", nargs="+", help="registered names; defaults to plugin.json")
    parser.add_argument("--apply", action="store_true", help="create links after successful preflight")
    parser.add_argument("--replace", action="store_true", help="back up conflicting targets before linking")
    args = parser.parse_args(argv)
    try:
        plan = plan_links(ROOT, args.dest, args.skills, args.replace)
        for source, target, action in plan:
            print(f"{action}: {target} -> {source}")
        if not args.apply:
            print("Preview only; nothing changed. Add --apply to install.")
            return 0
        backup = apply_links(plan)
        print("Links installed." + (f" Backups retained at: {backup}" if backup else ""))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f"Install stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
