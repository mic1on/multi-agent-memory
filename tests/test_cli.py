import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]


def run_cli(vault: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["AGENT_MEMORY_VAULT"] = str(vault)
    env["AGENT_MEMORY_STATE_DIR"] = str(vault.parent / "state")
    return subprocess.run([sys.executable, "-m", "multi_agent_memory.cli", *args], cwd=cwd or ROOT, env=env, text=True, capture_output=True, check=True)


def test_cli_lifecycle_and_compatibility_alias(tmp_path):
    vault = tmp_path / "vault"
    run_cli(vault, "init")
    result = run_cli(vault, "propose", "--type", "preferences", "--text", "Use concise answers.", "--source_session", "test")
    identifier = result.stdout.split("	", 1)[0]
    assert identifier in run_cli(vault, "search", "concise", "--include-candidates").stdout
    run_cli(vault, "confirm", identifier)
    assert "active" in run_cli(vault, "search", "concise").stdout


def test_cli_version_commands_match():
    short = subprocess.run([sys.executable, "-m", "multi_agent_memory.cli", "-v"], capture_output=True, text=True, check=True)
    command = subprocess.run([sys.executable, "-m", "multi_agent_memory.cli", "version"], capture_output=True, text=True, check=True)

    assert short.stdout == command.stdout
    assert short.stdout.strip() == "0.2.0"


def test_recover_auto_syncs_managed_adapter_without_extra_stdout(tmp_path):
    home = tmp_path / "home"
    vault = tmp_path / "vault"
    state = tmp_path / "state"
    run_cli(vault, "install", "--agent", "pi", "--home", str(home))
    target = home / ".pi/agent/extensions/agent-memory.js"
    target.write_text("// multi-agent-memory-managed\n// stale adapter\n", encoding="utf-8")

    environment = os.environ.copy()
    environment["AGENT_MEMORY_VAULT"] = str(vault)
    environment["AGENT_MEMORY_STATE_DIR"] = str(state)
    environment["HOME"] = str(home)
    result = subprocess.run([sys.executable, "-m", "multi_agent_memory.cli", "recover"], cwd=ROOT, env=environment, text=True, capture_output=True, check=True)

    assert result.stdout == "recovered 0 pending summaries\n"
    assert 'const CLI = "mam"' in target.read_text(encoding="utf-8")
    status = subprocess.run([sys.executable, "-m", "multi_agent_memory.cli", "status"], cwd=ROOT, env=environment, text=True, capture_output=True, check=True)
    assert json.loads(status.stdout)["adapters"]["pi"]["status"] == "current"


def test_recover_respects_disabled_auto_sync(tmp_path):
    home = tmp_path / "home"
    vault = tmp_path / "vault"
    state = tmp_path / "state"
    config = tmp_path / "settings.yaml"
    run_cli(vault, "install", "--agent", "pi", "--home", str(home))
    target = home / ".pi/agent/extensions/agent-memory.js"
    stale = "// multi-agent-memory-managed\n// stale adapter\n"
    target.write_text(stale, encoding="utf-8")
    config.write_text("auto_sync_adapters: false\n", encoding="utf-8")

    environment = os.environ.copy()
    environment["AGENT_MEMORY_VAULT"] = str(vault)
    environment["AGENT_MEMORY_STATE_DIR"] = str(state)
    environment["HOME"] = str(home)
    subprocess.run([sys.executable, "-m", "multi_agent_memory.cli", "--config", str(config), "recover"], cwd=ROOT, env=environment, text=True, capture_output=True, check=True)

    assert target.read_text(encoding="utf-8") == stale


def test_cli_project_detection_and_summary(tmp_path):
    project = tmp_path / "example-project"
    (project / ".git").mkdir(parents=True)
    result = run_cli(tmp_path / "vault", "propose", "--type", "project", "--text", "Use project rules.", cwd=project)
    identifier = result.stdout.split("	", 1)[0]
    assert identifier.startswith("project-")
    summary = run_cli(tmp_path / "vault", "session-summary", "--text", "A short summary.")
    assert "session-" in summary.stdout


def test_cli_empty_pending_does_not_create_receipt(tmp_path):
    result = run_cli(tmp_path / "vault", "pending", "--session-id", "empty")
    assert "nothing saved" in result.stdout
    assert json.loads(run_cli(tmp_path / "vault", "status").stdout)["pending"] == 0


def test_cli_empty_summary_file_is_a_noop(tmp_path):
    result = run_cli(tmp_path / "vault", "pending", "--session-id", "empty", "--summary-file", "")
    assert "nothing saved" in result.stdout
