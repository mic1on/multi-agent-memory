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


def test_protocol_is_shipped_as_a_package_resource():
    assert "记住" in read_text("protocol.md")


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
    assert any("CLAUDE.md" in result for result in results)
    text = instructions.read_text(encoding="utf-8")
    assert "Keep this text." in text
    assert "multi-agent-memory-managed:start" in text


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
