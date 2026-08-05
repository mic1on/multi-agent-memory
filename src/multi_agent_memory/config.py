"""Configuration loading for multi-agent-memory."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dynaconf import Dynaconf


def _platform_data_dir() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "multi-agent-memory"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "multi-agent-memory"


def _default_vault() -> Path:
    if os.environ.get("AGENT_MEMORY_VAULT"):
        return Path(os.environ["AGENT_MEMORY_VAULT"]).expanduser()
    return Path.home() / "Documents/Obsidian/AgentMemory"


def _default_config_file() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "multi-agent-memory" / "settings.yaml"


@dataclass(frozen=True)
class Settings:
    vault: Path
    state_dir: Path
    index_path: Path
    recall_limit: int = 8

    @classmethod
    def load(cls, config_file: str | Path | None = None) -> "Settings":
        filename = Path(config_file).expanduser() if config_file else _default_config_file()
        settings = Dynaconf(
            settings_files=[str(filename)] if filename.exists() else [],
            environments=False,
            load_dotenv=True,
            envvar_prefix="AGENT_MEMORY",
            merge_enabled=True,
        )
        vault = Path(settings.get("VAULT", _default_vault())).expanduser()
        state = Path(settings.get("STATE_DIR", _platform_data_dir())).expanduser()
        index = Path(settings.get("INDEX_PATH", state / "memory.sqlite3")).expanduser()
        limit = int(settings.get("RECALL_LIMIT", 8))
        if limit < 1 or limit > 100:
            raise ValueError("recall_limit must be between 1 and 100")
        return cls(vault=vault.resolve(), state_dir=state.resolve(), index_path=index.resolve(), recall_limit=limit)
