"""Resources shipped inside the multi-agent-memory distribution."""

from __future__ import annotations

from importlib.resources import files


def read_text(name: str) -> str:
    return files("multi_agent_memory.assets").joinpath(name).read_text(encoding="utf-8")
