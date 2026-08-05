"""Install agent adapters without overwriting unrelated user configuration."""

from __future__ import annotations

import json
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


def _merge_codex(path: Path, *, force: bool) -> str:
    source = json.loads(read_text("codex-hooks.json"))
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


def install_agent(agent: str, *, force: bool = False, home: Path | None = None) -> list[str]:
    """Install one adapter or all adapters and return human-readable results."""

    root = (home or Path.home()).expanduser()
    targets = {
        "codex": root / ".codex" / "hooks.json",
        "pi": root / ".pi" / "agent" / "extensions" / "agent-memory.js",
        "opencode": root / ".config" / "opencode" / "plugins" / "agent-memory.js",
    }
    if agent == "all":
        agents = ("codex", "pi", "opencode")
    elif agent in targets:
        agents = (agent,)
    else:
        raise ValueError(f"unknown agent: {agent}; choose codex, pi, opencode, or all")
    results = []
    for current in agents:
        if current == "codex":
            results.append(_merge_codex(targets[current], force=force))
        elif current == "pi":
            results.append(_write_new(targets[current], "// multi-agent-memory-managed\n" + read_text("pi-agent-memory.js"), force=force))
        else:
            results.append(_write_new(targets[current], "// multi-agent-memory-managed\n" + read_text("opencode-agent-memory.js"), force=force))
    return results
