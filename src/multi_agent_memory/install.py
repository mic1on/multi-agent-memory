"""Install agent adapters without overwriting unrelated user configuration."""

from __future__ import annotations

import json
import hashlib
import os
import re
import sqlite3
import shutil
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__
from .resources import read_text


MANIFEST_SCHEMA = 1
MANIFEST_NAME = "adapters.json"
SUPPORTED_AGENTS = ("codex", "pi", "opencode", "claude")
ADAPTER_ASSETS = {
    "codex": ("codex-hooks.json",),
    "pi": ("pi-agent-memory.js",),
    "opencode": ("opencode-agent-memory.js",),
    "claude": ("claude-hooks.json", "claude-code.md"),
}


def _backup(path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = path.with_name(f"{path.name}.multi-agent-memory-backup-{stamp}")
    shutil.copy2(path, backup)
    return backup


def _targets(root: Path) -> dict[str, tuple[Path, ...]]:
    return {
        "codex": (root / ".codex" / "hooks.json",),
        "pi": (root / ".pi" / "agent" / "extensions" / "agent-memory.js",),
        "opencode": (root / ".config" / "opencode" / "plugins" / "agent-memory.js",),
        "claude": (root / ".claude" / "settings.json", root / ".claude" / "CLAUDE.md"),
    }


def _manifest_path(*, home: Path | None = None, state_dir: Path | None = None) -> Path:
    if state_dir:
        return Path(state_dir).expanduser() / MANIFEST_NAME
    root = (home or Path.home()).expanduser()
    if home is None:
        if os.name == "nt":
            base = Path(os.environ.get("LOCALAPPDATA", root / "AppData/Local"))
        else:
            base = Path(os.environ.get("XDG_DATA_HOME", root / ".local/share"))
    else:
        base = root / ("AppData/Local" if os.name == "nt" else ".local/share")
    return base / "multi-agent-memory" / MANIFEST_NAME


@contextmanager
def _state_lock(state_dir: Path):
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / ".memory.lock.sqlite3"
    connection = sqlite3.connect(path, timeout=10)
    try:
        connection.execute("CREATE TABLE IF NOT EXISTS lock (id INTEGER PRIMARY KEY)")
        connection.commit()
        connection.execute("BEGIN IMMEDIATE")
        yield
    finally:
        connection.close()


def _empty_manifest() -> dict[str, Any]:
    return {"schema": MANIFEST_SCHEMA, "adapters": {}}


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return _empty_manifest()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid adapter manifest: {path}: {error}") from error
    if not isinstance(data, dict) or data.get("schema") != MANIFEST_SCHEMA or not isinstance(data.get("adapters"), dict):
        raise ValueError(f"invalid adapter manifest schema: {path}")
    return data


def _save_manifest(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _asset_hash(agent: str) -> str:
    digest = hashlib.sha256()
    for asset in ADAPTER_ASSETS[agent]:
        digest.update(asset.encode("utf-8"))
        digest.update(b"\0")
        digest.update(read_text(asset).encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _file_hash(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_record(agent: str, root: Path, *, status: str = "current", error: str | None = None) -> dict[str, Any]:
    record: dict[str, Any] = {
        "version": __version__,
        "asset_hash": _asset_hash(agent),
        "targets": [str(path) for path in _targets(root)[agent]],
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if agent in {"pi", "opencode"}:
        target_hash = _file_hash(_targets(root)[agent][0])
        if target_hash:
            record["target_hash"] = target_hash
    if error:
        record["error"] = error
    return record


def _hook_commands(path: Path) -> set[str] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    commands: set[str] = set()
    for blocks in data.get("hooks", {}).values() if isinstance(data, dict) and isinstance(data.get("hooks"), dict) else ():
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            if not isinstance(block, dict) or not isinstance(block.get("hooks"), list):
                continue
            for hook in block["hooks"]:
                if isinstance(hook, dict) and isinstance(hook.get("command"), str):
                    commands.add(hook["command"])
    return commands


def _has_hook_signature(path: Path, session_id: str) -> bool:
    commands = _hook_commands(path)
    if commands is None:
        return False
    required = {"mam recover", "mam context", "mam protocol"}
    pending = f"mam pending --session-id {session_id}"
    return required.issubset(commands) and any(command.startswith(pending) for command in commands)


def _managed_command_key(command: Any) -> str | None:
    if not isinstance(command, str):
        return None
    normalized = command.strip()
    for name in ("recover", "context", "protocol"):
        if normalized == f"mam {name}" or normalized.startswith(f"mam {name} "):
            return name
    match = re.match(r"mam pending --session-id ([^\s]+)(?:\s|$)", normalized)
    if match and match.group(1) in {"codex", "claude-code"}:
        return f"pending:{match.group(1)}"
    return None


def _legacy_agents(root: Path) -> list[str]:
    targets = _targets(root)
    discovered: list[str] = []
    for agent in ("pi", "opencode"):
        path = targets[agent][0]
        if path.is_file() and "multi-agent-memory-managed" in path.read_text(encoding="utf-8"):
            discovered.append(agent)
    if _has_hook_signature(targets["codex"][0], "codex"):
        discovered.append("codex")
    claude_instructions = targets["claude"][1]
    if _has_hook_signature(targets["claude"][0], "claude-code") and claude_instructions.is_file():
        instructions = claude_instructions.read_text(encoding="utf-8")
        if "<!-- multi-agent-memory-managed:start -->" in instructions and "<!-- multi-agent-memory-managed:end -->" in instructions:
            discovered.append("claude")
    return discovered


def _managed_target_is_intact(agent: str, root: Path, record: dict[str, Any]) -> bool:
    try:
        targets = _targets(root)[agent]
        if agent in {"pi", "opencode"}:
            target = targets[0]
            return bool(target.is_file() and "multi-agent-memory-managed" in target.read_text(encoding="utf-8") and (not record.get("target_hash") or _file_hash(target) == record["target_hash"]))
        if agent == "codex":
            return _has_hook_signature(targets[0], "codex")
        if not _has_hook_signature(targets[0], "claude-code") or not targets[1].is_file():
            return False
        instructions = targets[1].read_text(encoding="utf-8")
        return "<!-- multi-agent-memory-managed:start -->" in instructions and "<!-- multi-agent-memory-managed:end -->" in instructions
    except (OSError, UnicodeError):
        return False


def _install_one(agent: str, root: Path, *, force: bool = False) -> list[str]:
    targets = _targets(root)
    if agent == "codex":
        return [_merge_codex(targets[agent][0], force=force)]
    if agent == "pi":
        return [_write_new(targets[agent][0], "// multi-agent-memory-managed\n" + read_text("pi-agent-memory.js"), force=force)]
    if agent == "opencode":
        return [_write_new(targets[agent][0], "// multi-agent-memory-managed\n" + read_text("opencode-agent-memory.js"), force=force)]
    if agent == "claude":
        return [
            _merge_hooks(targets[agent][0], "claude-hooks.json"),
            _merge_instruction_file(root / ".claude" / "CLAUDE.md", "claude-code.md"),
        ]
    raise ValueError(f"unknown agent: {agent}; choose codex, pi, opencode, claude, or all")


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
    source_commands = {
        _managed_command_key(hook.get("command")): hook.get("command")
        for blocks in source["hooks"].values()
        for block in blocks
        for hook in block.get("hooks", [])
        if isinstance(hook, dict) and _managed_command_key(hook.get("command"))
    }
    changed = False
    for event, blocks in source["hooks"].items():
        target = hooks.setdefault(event, [])
        if not isinstance(target, list):
            raise ValueError(f"Codex hook event must be a list: hooks.{event}")
        for block in target:
            if not isinstance(block, dict):
                continue
            for hook in block.get("hooks", []):
                if not isinstance(hook, dict):
                    continue
                command = hook.get("command")
                key = _managed_command_key(command)
                if key in source_commands and command != source_commands[key]:
                    hook["command"] = source_commands[key]
                    changed = True
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


def _selected_agents(agent: str) -> tuple[str, ...]:
    if agent == "all":
        return SUPPORTED_AGENTS
    if agent in SUPPORTED_AGENTS:
        return (agent,)
    raise ValueError(f"unknown agent: {agent}; choose codex, pi, opencode, claude, or all")


def install_agent(
    agent: str,
    *,
    force: bool = False,
    home: Path | None = None,
    state_dir: Path | None = None,
) -> list[str]:
    """Install one adapter or all adapters and record managed agents."""

    root = (home or Path.home()).expanduser()
    manifest_path = _manifest_path(home=home, state_dir=state_dir)
    results: list[str] = []
    with _state_lock(manifest_path.parent):
        manifest = _load_manifest(manifest_path)
        for current in _selected_agents(agent):
            results.extend(_install_one(current, root, force=force))
            manifest["adapters"][current] = _manifest_record(current, root)
        _save_manifest(manifest_path, manifest)
    return results


def sync_adapters(*, home: Path | None = None, state_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Synchronize managed adapters and return statuses without printing output."""

    root = (home or Path.home()).expanduser()
    manifest_path = _manifest_path(home=home, state_dir=state_dir)
    statuses: dict[str, dict[str, Any]] = {}
    with _state_lock(manifest_path.parent):
        manifest = _load_manifest(manifest_path)
        adapters = manifest["adapters"]
        for agent in _legacy_agents(root):
            if agent not in adapters:
                adapters[agent] = {"version": "legacy", "asset_hash": "", "status": "legacy"}
        for agent in list(adapters):
            if agent not in SUPPORTED_AGENTS or not isinstance(adapters[agent], dict):
                continue
            record = adapters[agent]
            current_hash = _asset_hash(agent)
            if record.get("status") == "current" and record.get("asset_hash") == current_hash and _managed_target_is_intact(agent, root, record):
                statuses[agent] = record
                continue
            try:
                _install_one(agent, root)
            except (OSError, ValueError, TypeError) as error:
                failed = dict(record)
                failed.update({"status": "conflict" if isinstance(error, FileExistsError) else "error", "error": str(error), "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
                adapters[agent] = failed
                statuses[agent] = failed
                continue
            updated = _manifest_record(agent, root)
            updated["last_action"] = "updated" if record.get("asset_hash") else "adopted"
            adapters[agent] = updated
            statuses[agent] = updated
        if adapters:
            _save_manifest(manifest_path, manifest)
    return statuses


def adapter_status(*, home: Path | None = None, state_dir: Path | None = None) -> dict[str, Any]:
    """Return managed adapter state for inclusion in ``mam status``."""

    root = (home or Path.home()).expanduser()
    manifest_path = _manifest_path(home=home, state_dir=state_dir)
    try:
        manifest = _load_manifest(manifest_path)
    except ValueError as error:
        return {"manifest": "error", "error": str(error), "adapters": {}}
    adapters = {agent: dict(record) for agent, record in manifest["adapters"].items() if isinstance(record, dict)}
    if not adapters:
        adapters = {agent: {"status": "legacy"} for agent in _legacy_agents(root)}
    for agent, record in adapters.items():
        if agent not in SUPPORTED_AGENTS:
            continue
        if record.get("status") in {"conflict", "error"}:
            continue
        if not _managed_target_is_intact(agent, root, record):
            record["status"] = "conflict"
            record["error"] = "managed adapter target is missing or changed"
        elif record.get("asset_hash") and record.get("asset_hash") != _asset_hash(agent):
            record["status"] = "outdated"
    return {"manifest": str(manifest_path), "adapters": adapters}
