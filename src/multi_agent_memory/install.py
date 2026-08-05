"""Install agent adapters without overwriting unrelated user configuration."""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .resources import read_text


def _backup(path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = path.with_name(f"{path.name}.multi-agent-memory-backup-{stamp}")
    shutil.copy2(path, backup)
    return backup


def _write_new(path: Path, content: str, *, force: bool) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        current = path.read_text(encoding="utf-8")
        if current == content:
            return f"already installed: {path}"
        if "multi-agent-memory-managed" not in current and not force:
            raise FileExistsError(f"refusing to overwrite existing file: {path}; inspect it or pass --force")
        backup = _backup(path)
        path.write_text(content, encoding="utf-8")
        return f"updated: {path} (backup: {backup})"
    path.write_text(content, encoding="utf-8")
    return f"installed: {path}"


def _merge_hooks(path: Path, asset: str) -> str:
    source = json.loads(read_text(asset))
    if path.exists():
        try:
            data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid Codex hooks JSON: {path}: {error}") from error
    else:
        data = {}
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError(f"Codex hooks must contain an object at hooks: {path}")
    changed = False
    for event, blocks in source["hooks"].items():
        target = hooks.setdefault(event, [])
        if not isinstance(target, list):
            raise ValueError(f"Codex hook event must be a list: hooks.{event}")
        commands = {hook.get("command") for block in target if isinstance(block, dict) for hook in block.get("hooks", []) if isinstance(hook, dict)}
        for block in blocks:
            missing = [hook for hook in block["hooks"] if hook.get("command") not in commands]
            if missing:
                target.append({"matcher": block.get("matcher", ""), "hooks": missing})
                commands.update(hook.get("command") for hook in missing)
                changed = True
    if not changed:
        return f"already installed: {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = _backup(path) if path.exists() else None
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return f"updated: {path}" + (f" (backup: {backup})" if backup else "")


def _merge_codex(path: Path, *, force: bool) -> str:
    return _merge_hooks(path, "codex-hooks.json")


def _merge_instruction_file(path: Path, asset: str) -> str:
    managed = read_text(asset).strip()
    marker_start = "<!-- multi-agent-memory-managed:start -->"
    marker_end = "<!-- multi-agent-memory-managed:end -->"
    if marker_start not in managed or marker_end not in managed:
        raise ValueError(f"instruction asset has invalid management markers: {asset}")
    path.parent.mkdir(parents=True, exist_ok=True)
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if (marker_start in current) != (marker_end in current):
        raise ValueError(f"instruction file has an incomplete management block: {path}")
    pattern = re.compile(re.escape(marker_start) + r".*?" + re.escape(marker_end), re.S)
    if pattern.search(current):
        updated = pattern.sub(managed, current).rstrip() + "\n"
    else:
        separator = "\n\n" if current.strip() else ""
        updated = current.rstrip() + separator + managed + "\n"
    if updated == current:
        return f"already installed: {path}"
    backup = _backup(path) if path.exists() else None
    path.write_text(updated, encoding="utf-8")
    return f"updated: {path}" + (f" (backup: {backup})" if backup else "")


def install_agent(agent: str, *, force: bool = False, home: Path | None = None) -> list[str]:
    """Install one adapter or all adapters and return human-readable results."""

    root = (home or Path.home()).expanduser()
    targets = {
        "codex": root / ".codex" / "hooks.json",
        "pi": root / ".pi" / "agent" / "extensions" / "agent-memory.js",
        "opencode": root / ".config" / "opencode" / "plugins" / "agent-memory.js",
        "claude": root / ".claude" / "settings.json",
    }
    if agent == "all":
        agents = ("codex", "pi", "opencode", "claude")
    elif agent in targets:
        agents = (agent,)
    else:
        raise ValueError(f"unknown agent: {agent}; choose codex, pi, opencode, claude, or all")
    results = []
    for current in agents:
        if current == "codex":
            results.append(_merge_codex(targets[current], force=force))
        elif current == "pi":
            results.append(_write_new(targets[current], "// multi-agent-memory-managed\n" + read_text("pi-agent-memory.js"), force=force))
        elif current == "opencode":
            results.append(_write_new(targets[current], "// multi-agent-memory-managed\n" + read_text("opencode-agent-memory.js"), force=force))
        else:
            results.append(_merge_hooks(targets[current], "claude-hooks.json"))
            results.append(_merge_instruction_file(root / ".claude" / "CLAUDE.md", "claude-code.md"))
    return results
