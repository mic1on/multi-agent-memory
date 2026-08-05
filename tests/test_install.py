import json

from multi_agent_memory.install import install_agent
from multi_agent_memory.resources import read_text


def test_install_all_adapters_into_an_isolated_home(tmp_path):
    results = install_agent("all", home=tmp_path)
    assert len(results) == 3
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
