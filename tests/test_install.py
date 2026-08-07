import json

from multi_agent_memory.install import install_agent
from multi_agent_memory.resources import read_text


def test_install_all_adapters_into_an_isolated_home(tmp_path):
    results = install_agent("all", home=tmp_path)
    assert len(results) == 5
    assert (tmp_path / ".pi/agent/extensions/agent-memory.js").is_file()
    assert (tmp_path / ".config/opencode/plugins/agent-memory.js").is_file()
    hooks = json.loads((tmp_path / ".codex/hooks.json").read_text(encoding="utf-8"))
    commands = [hook["command"] for block in hooks["hooks"]["SessionStart"] for hook in block["hooks"]]
    assert "mam context" in commands
    assert "mam recover" in commands
    assert "mam protocol" in commands


def test_install_is_idempotent_and_refuses_unmanaged_files(tmp_path):
    install_agent("pi", home=tmp_path)
    assert "already installed" in install_agent("pi", home=tmp_path)[0]
    target = tmp_path / ".config/opencode/plugins/agent-memory.js"
    target.parent.mkdir(parents=True)
    target.write_text("// user plugin", encoding="utf-8")
    try:
        install_agent("opencode", home=tmp_path)
    except FileExistsError as error:
        assert "refusing to overwrite" in str(error)
    else:
        raise AssertionError("unmanaged adapter was overwritten")


def test_codex_install_migrates_legacy_stop_command(tmp_path):
    hooks_path = tmp_path / ".codex/hooks.json"
    hooks_path.parent.mkdir(parents=True)
    hooks_path.write_text(
        '{"hooks": {"Stop": [{"matcher": "", "hooks": [{"type": "command", '
        '"command": "mam pending --session-id codex --summary-file \\\"$AGENT_MEMORY_SUMMARY_FILE\\\"", '
        '"timeout": 5}]}]}}\n',
        encoding="utf-8",
    )

    result = install_agent("codex", home=tmp_path)

    assert "updated" in result[0]
    commands = [
        hook["command"]
        for block in json.loads(hooks_path.read_text(encoding="utf-8"))["hooks"]["Stop"]
        for hook in block["hooks"]
    ]
    assert commands == [
        'mam pending --session-id codex --summary-file "$AGENT_MEMORY_SUMMARY_FILE" >/dev/null'
    ]


def test_claude_install_migrates_legacy_stop_command(tmp_path):
    settings_path = tmp_path / ".claude/settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        '{"hooks": {"Stop": [{"matcher": "", "hooks": [{"type": "command", '
        '"command": "mam pending --session-id claude-code --summary-file \\\"$AGENT_MEMORY_SUMMARY_FILE\\\"", '
        '"timeout": 5}]}]}}\n',
        encoding="utf-8",
    )

    result = install_agent("claude", home=tmp_path)

    assert "updated" in result[0]
    commands = [
        hook["command"]
        for block in json.loads(settings_path.read_text(encoding="utf-8"))["hooks"]["Stop"]
        for hook in block["hooks"]
    ]
    assert commands == [
        'mam pending --session-id claude-code --summary-file "$AGENT_MEMORY_SUMMARY_FILE" >/dev/null'
    ]


def test_protocol_is_shipped_as_a_package_resource():
    protocol = read_text("protocol.md")
    assert "记住" in protocol
    assert "写入偏好记忆" in protocol
    assert "Other memory tools may coexist" in protocol


def test_claude_code_install_merges_settings_and_preserves_claude_md(tmp_path):
    settings = tmp_path / ".claude/settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text('{"env": {"KEEP_ME": "yes"}, "hooks": {"UserHook": []}}\n', encoding="utf-8")
    instructions = tmp_path / ".claude/CLAUDE.md"
    instructions.write_text("# My instructions\n\nKeep this text.\n", encoding="utf-8")

    results = install_agent("claude", home=tmp_path)

    data = json.loads(settings.read_text(encoding="utf-8"))
    commands = [hook["command"] for block in data["hooks"]["SessionStart"] for hook in block["hooks"]]
    assert data["env"]["KEEP_ME"] == "yes"
    assert data["hooks"]["UserHook"] == []
    assert "mam context" in commands
    assert "mam protocol" in commands
    stop_commands = [hook["command"] for block in data["hooks"]["Stop"] for hook in block["hooks"]]
    assert stop_commands == [
        'mam pending --session-id claude-code --summary-file "$AGENT_MEMORY_SUMMARY_FILE" >/dev/null'
    ]
    assert any("CLAUDE.md" in result for result in results)
    text = instructions.read_text(encoding="utf-8")
    assert "Keep this text." in text
    assert "multi-agent-memory-managed:start" in text
    assert "写入偏好记忆" in text


def test_claude_code_install_updates_only_managed_instruction_block(tmp_path):
    install_agent("claude", home=tmp_path)
    instructions = tmp_path / ".claude/CLAUDE.md"
    instructions.write_text(instructions.read_text(encoding="utf-8") + "\nUser addition.\n", encoding="utf-8")
    results = install_agent("claude", home=tmp_path)
    assert any("already installed" in result for result in results)
    text = instructions.read_text(encoding="utf-8")
    assert "User addition." in text
    assert text.count("multi-agent-memory-managed:start") == 1


def test_claude_code_refuses_incomplete_instruction_markers(tmp_path):
    instructions = tmp_path / ".claude/CLAUDE.md"
    instructions.parent.mkdir(parents=True)
    instructions.write_text("<!-- multi-agent-memory-managed:start -->\n", encoding="utf-8")
    try:
        install_agent("claude", home=tmp_path)
    except ValueError as error:
        assert "incomplete management block" in str(error)
    else:
        raise AssertionError("incomplete Claude Code block was modified")


def test_install_command_supports_all_and_repeated_agents(tmp_path):
    import os
    import subprocess
    import sys

    env = os.environ.copy()
    env["AGENT_MEMORY_VAULT"] = str(tmp_path / "vault")
    env["AGENT_MEMORY_STATE_DIR"] = str(tmp_path / "state")
    result = subprocess.run([sys.executable, "-m", "multi_agent_memory.cli", "install", "--agent", "pi", "--agent", "claude", "--home", str(tmp_path)], env=env, text=True, capture_output=True, check=True)
    assert "agent-memory.js" in result.stdout
    assert "CLAUDE.md" in result.stdout

    all_result = subprocess.run([sys.executable, "-m", "multi_agent_memory.cli", "install-agent", "--agent", "all", "--home", str(tmp_path)], env=env, text=True, capture_output=True, check=True)
    assert "already installed" in all_result.stdout


def test_install_without_arguments_is_safe_in_noninteractive_mode(tmp_path):
    import os
    import subprocess
    import sys

    env = os.environ.copy()
    env["AGENT_MEMORY_VAULT"] = str(tmp_path / "vault")
    env["AGENT_MEMORY_STATE_DIR"] = str(tmp_path / "state")
    result = subprocess.run([sys.executable, "-m", "multi_agent_memory.cli", "install", "--home", str(tmp_path)], env=env, text=True, capture_output=True)
    assert result.returncode == 2
    assert "--agent NAME or --all" in result.stderr
