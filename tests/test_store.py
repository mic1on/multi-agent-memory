import json
import multiprocessing as mp
from pathlib import Path

from multi_agent_memory.config import Settings
from multi_agent_memory.store import Vault


def make_vault(tmp_path: Path) -> Vault:
    return Vault(Settings(vault=tmp_path / "vault", state_dir=tmp_path / "state", index_path=tmp_path / "state" / "memory.sqlite3"))


def _child_create(payload: tuple[str, str, str, str]) -> None:
    vault_path, state_path, index_path, body = payload
    vault = Vault(Settings(vault=Path(vault_path), state_dir=Path(state_path), index_path=Path(index_path)))
    vault.create({"type": "learning", "body": body}, candidate=False)


def test_candidate_confirmation_search_and_forget(tmp_path):
    vault = make_vault(tmp_path)
    identifier, candidate = vault.create({"type": "preferences", "title": "Writing", "body": "Answer in Chinese and lead with the conclusion."})
    assert candidate.parent.name == "inbox"
    assert vault.search("Chinese") == []
    assert vault.search("Chinese", include_candidates=True)[0]["id"] == identifier
    confirmed = vault.confirm(identifier)
    assert confirmed.parent.name == "00-profile"
    assert vault.search("Chinese")[0]["status"] == "active"
    vault.forget(identifier)
    assert vault.search("Chinese") == []


def test_project_metadata_is_indexed_and_filterable(tmp_path):
    vault = make_vault(tmp_path)
    identifier, _ = vault.create({"type": "project", "scope": "project", "project": "alpha", "body": "Use bounded workers."}, candidate=False)
    result = vault.search("bounded")[0]
    assert result["id"] == identifier
    assert result["project"] == "alpha"


def test_pending_without_summary_is_noop_and_recovery_promotes_summary(tmp_path):
    vault = make_vault(tmp_path)
    assert vault.pending({"session_id": "empty"}) is None
    assert vault.pending({"session_id": "crashed", "summary": "Recovered summary"}) is not None
    assert vault.recover() == 1
    assert vault.status()["pending"] == 0
    assert vault.search("Recovered")[0]["type"] == "session"


def test_markdown_is_authoritative_after_rebuild(tmp_path):
    vault = make_vault(tmp_path)
    identifier, path = vault.create({"type": "learning", "title": "Manual edit", "body": "Original"}, candidate=False)
    text = path.read_text(encoding="utf-8").replace("Original", "Edited in Obsidian")
    path.write_text(text, encoding="utf-8")
    vault.rebuild()
    assert vault.search("Edited")[0]["id"] == identifier


def test_concurrent_writers_from_separate_processes_serialize(tmp_path):
    vault = make_vault(tmp_path)
    context = mp.get_context("spawn")
    payloads = [
        (str(tmp_path / "vault"), str(tmp_path / "state"), str(tmp_path / "state" / "memory.sqlite3"), f"concurrent writer {i}")
        for i in range(4)
    ]
    workers = [context.Process(target=_child_create, args=(payload,)) for payload in payloads]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    assert all(worker.exitcode == 0 for worker in workers)
    assert (tmp_path / "state" / ".memory.lock.sqlite3").exists()
    assert vault.status()["by_status"]["active"] == 4
