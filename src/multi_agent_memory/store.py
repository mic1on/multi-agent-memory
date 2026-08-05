"""Markdown-authoritative Vault and rebuildable SQLite search index."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sqlite3
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .config import Settings

LAYERS = {
    "preferences": "00-profile",
    "project": "10-projects",
    "decision": "20-decisions",
    "learning": "30-learnings",
    "session": "90-sessions",
    "candidate": "inbox",
}
MEMORY_TYPES = set(LAYERS) - {"candidate"}
FRONT_MATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", re.S)


def timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def today() -> str:
    return dt.date.today().isoformat()


def slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", value.lower()).strip("-")[:64] or "memory"


def parse_markdown(text: str) -> tuple[dict[str, str], str]:
    match = FRONT_MATTER.match(text)
    if not match:
        return {}, text
    metadata: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if line.strip() and not line.lstrip().startswith("#") and ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata, match.group(2).lstrip("\n")


def _scalar(value: Any) -> str:
    value = str(value).replace("\n", " ").strip()
    if not value or re.search(r"[:#{}\[\],&*!|>'\"%@]", value):
        return json.dumps(value, ensure_ascii=False)
    return value


def render_markdown(metadata: dict[str, Any], body: str) -> str:
    fields = "\n".join(f"{key}: {_scalar(value)}" for key, value in metadata.items())
    return f"---\n{fields}\n---\n\n{body.rstrip()}\n"


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Vault:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.root = settings.vault
        self.lock_path = settings.state_dir / ".memory.lock.sqlite3"

    def layout(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.settings.state_dir.mkdir(parents=True, exist_ok=True)
        for folder in set(LAYERS.values()) | {".memory/pending"}:
            (self.root / folder).mkdir(parents=True, exist_ok=True)

    @contextmanager
    def locked(self) -> Iterator[None]:
        self.settings.state_dir.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.lock_path)
        try:
            connection.execute("CREATE TABLE IF NOT EXISTS lock (id INTEGER PRIMARY KEY)")
            connection.execute("BEGIN IMMEDIATE")
            yield
        finally:
            connection.close()

    def documents(self) -> Iterator[Path]:
        for folder in LAYERS.values():
            base = self.root / folder
            if base.exists():
                yield from sorted(base.rglob("*.md"))

    def _connection(self) -> sqlite3.Connection:
        self.settings.index_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.settings.index_path)
        existing = [row[0] for row in connection.execute("SELECT name FROM pragma_table_info('documents')").fetchall()]
        expected = ["id", "path", "title", "body", "type", "scope", "project", "status", "updated"]
        if existing and existing != expected:
            connection.execute("DROP TABLE documents")
        connection.execute("CREATE VIRTUAL TABLE IF NOT EXISTS documents USING fts5(id UNINDEXED, path UNINDEXED, title, body, type UNINDEXED, scope UNINDEXED, project UNINDEXED, status UNINDEXED, updated UNINDEXED)")
        return connection

    def _rebuild_unlocked(self) -> int:
        self.layout()
        connection = self._connection()
        connection.execute("DELETE FROM documents")
        count = 0
        for path in self.documents():
            metadata, body = parse_markdown(path.read_text(encoding="utf-8"))
            if not metadata.get("id"):
                continue
            connection.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?)", (metadata["id"], str(path.relative_to(self.root)), metadata.get("title", path.stem), body, metadata.get("type", "learning"), metadata.get("scope", "global"), metadata.get("project", ""), metadata.get("status", "active"), metadata.get("updated", "")))
            count += 1
        connection.commit()
        connection.close()
        return count

    def rebuild(self) -> int:
        with self.locked():
            return self._rebuild_unlocked()

    def search(self, query: str = "", limit: int | None = None, include_candidates: bool = False) -> list[dict[str, str]]:
        self.layout()
        self.rebuild()
        connection = self._connection()
        statuses = "'active','confirmed'" + (",'candidate'" if include_candidates else "")
        limit = limit or self.settings.recall_limit
        keys = ("id", "path", "title", "body", "type", "scope", "project", "status", "updated")
        try:
            if query.strip():
                rows = connection.execute(f"SELECT id,path,title,body,type,scope,project,status,updated FROM documents WHERE documents MATCH ? AND status IN ({statuses}) ORDER BY bm25(documents), updated DESC LIMIT ?", (query, limit)).fetchall()
            else:
                rows = connection.execute(f"SELECT id,path,title,body,type,scope,project,status,updated FROM documents WHERE status IN ({statuses}) ORDER BY updated DESC LIMIT ?", (limit,)).fetchall()
        except sqlite3.Error:
            rows = connection.execute(f"SELECT id,path,title,body,type,scope,project,status,updated FROM documents WHERE status IN ({statuses}) ORDER BY updated DESC").fetchall()
            needle = query.casefold().strip()
            rows = [row for row in rows if not needle or needle in (row[2] + "\n" + row[3]).casefold()][:limit]
        connection.close()
        return [dict(zip(keys, row)) for row in rows]

    def create(self, data: dict[str, Any], *, candidate: bool = True) -> tuple[str, Path]:
        body = str(data.get("body") or data.get("content") or "").strip()
        if not body:
            raise ValueError("memory body is empty")
        kind = str(data.get("type", "learning"))
        if kind not in MEMORY_TYPES:
            raise ValueError(f"invalid memory type: {kind}")
        title = str(data.get("title") or body.splitlines()[0][:80])
        identifier = str(data.get("id") or f"{kind}-{today()}-{uuid.uuid4().hex[:8]}")
        metadata: dict[str, Any] = {"id": identifier, "title": title, "type": kind, "scope": str(data.get("scope", "global")), "status": "candidate" if candidate else str(data.get("status", "active")), "confidence": str(data.get("confidence", "inferred" if candidate else "confirmed")), "source": str(data.get("source", "agent")), "updated": timestamp()}
        for key in ("project", "source_session", "review_after"):
            if data.get(key):
                metadata[key] = str(data[key])
        folder = LAYERS["candidate" if candidate else kind]
        path = self.root / folder / f"{today()}-{slug(title)}-{identifier[-8:]}.md"
        with self.locked():
            atomic_write(path, render_markdown(metadata, body))
            self._rebuild_unlocked()
        return identifier, path

    def locate(self, identifier: str) -> tuple[Path, dict[str, str], str]:
        for path in self.documents():
            metadata, body = parse_markdown(path.read_text(encoding="utf-8"))
            if metadata.get("id") == identifier:
                return path, metadata, body
        raise ValueError(f"memory not found: {identifier}")

    def confirm(self, identifier: str) -> Path:
        path, metadata, body = self.locate(identifier)
        kind = metadata.get("type", "learning")
        if kind not in MEMORY_TYPES - {"session"}:
            raise ValueError("only candidates for reusable memories can be confirmed")
        metadata.update(status="active", confidence="confirmed", source="captain-confirmed", updated=timestamp())
        target = self.root / LAYERS[kind] / path.name
        with self.locked():
            atomic_write(target, render_markdown(metadata, body))
            if target != path:
                path.unlink()
            self._rebuild_unlocked()
        return target

    def forget(self, identifier: str) -> Path:
        path, metadata, body = self.locate(identifier)
        metadata.update(status="deprecated", updated=timestamp())
        with self.locked():
            atomic_write(path, render_markdown(metadata, body))
            self._rebuild_unlocked()
        return path

    def pending(self, data: dict[str, Any]) -> Path | None:
        if not data.get("summary"):
            return None
        self.layout()
        identifier = str(data.get("session_id") or f"pending-{today()}-{uuid.uuid4().hex[:8]}")
        path = self.root / ".memory/pending" / f"{slug(identifier)}.json"
        with self.locked():
            atomic_write(path, json.dumps({"schema": 1, "created": timestamp(), **data, "status": "summary_pending"}, ensure_ascii=False, indent=2) + "\n")
        return path

    def recover(self) -> int:
        self.layout()
        recovered = 0
        for path in sorted((self.root / ".memory/pending").glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            summary = str(data.get("summary") or "").strip()
            if not summary:
                continue
            self.create({"type": "session", "title": data.get("title", "Recovered session summary"), "body": summary, "source_session": data.get("session_id", "unknown"), "source": "recovered"}, candidate=False)
            with self.locked():
                path.unlink(missing_ok=True)
            recovered += 1
        return recovered

    def status(self) -> dict[str, Any]:
        self.layout()
        counts: dict[str, int] = {}
        for path in self.documents():
            metadata, _ = parse_markdown(path.read_text(encoding="utf-8"))
            status = metadata.get("status", "untyped")
            counts[status] = counts.get(status, 0) + 1
        pending = len(list((self.root / ".memory/pending").glob("*.json")))
        return {"vault": str(self.root), "index": str(self.settings.index_path), "documents": sum(counts.values()), "by_status": counts, "pending": pending}
