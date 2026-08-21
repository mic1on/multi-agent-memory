import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_javascript_adapters_parse():
    for path in (
        ROOT / "adapters/pi/agent-memory.js",
        ROOT / "src/multi_agent_memory/assets/pi-agent-memory.js",
        ROOT / "adapters/opencode/agent-memory.js",
    ):
        subprocess.run(["node", "--check", str(path)], check=True, capture_output=True, text=True)


def test_pi_adapters_use_supported_process_execution_and_register_lifecycle_handlers():
    for path in (ROOT / "adapters/pi/agent-memory.js", ROOT / "src/multi_agent_memory/assets/pi-agent-memory.js"):
        source = path.read_text(encoding="utf-8")
        assert "ctx.exec" not in source
        assert 'from "node:child_process"' in source
        assert 'spawn(CLI' in source

        script = f"""
const module = await import({path.as_uri()!r});
const events = new Map();
module.default({{ on(name, handler) {{ events.set(name, handler); }} }});
for (const name of ["session_start", "before_agent_start", "session_shutdown"]) {{
  if (typeof events.get(name) !== "function") throw new Error("missing " + name + " handler");
}}
"""
        subprocess.run(["node", "--input-type=module", "-e", script], check=True, capture_output=True, text=True)


def test_pi_adapters_inject_protocol_and_context(tmp_path):
    mam = tmp_path / "mam"
    mam.write_text(
        "#!/bin/sh\n"
        "case \"$1\" in\n"
        "  protocol) printf 'PROTOCOL: use mam for memory operations' ;;\n"
        "  context) printf 'CONTEXT: confirmed preferences' ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    mam.chmod(0o755)
    environment = os.environ.copy()
    environment["PATH"] = str(tmp_path) + os.pathsep + environment.get("PATH", "")

    for path in (ROOT / "adapters/pi/agent-memory.js", ROOT / "src/multi_agent_memory/assets/pi-agent-memory.js"):
        script = f"""
const module = await import({path.as_uri()!r});
const events = new Map();
module.default({{ on(name, handler) {{ events.set(name, handler); }} }});
const result = await events.get("before_agent_start")(
  {{ systemPrompt: "BASE" }},
  {{ cwd: {str(tmp_path)!r} }},
);
if (!result.systemPrompt.includes("PROTOCOL: use mam for memory operations")) throw new Error("protocol was not injected");
if (!result.systemPrompt.includes("CONTEXT: confirmed preferences")) throw new Error("context was not injected");
"""
        subprocess.run(
            ["node", "--input-type=module", "-e", script],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )


def test_codex_example_is_valid_json():
    for path in (
        ROOT / "adapters/codex/hooks.example.json",
        ROOT / "src/multi_agent_memory/assets/codex-hooks.json",
    ):
        data = json.loads(path.read_text(encoding="utf-8"))
        session_commands = [
            hook["command"]
            for block in data["hooks"]["SessionStart"]
            for hook in block["hooks"]
        ]
        assert "mam protocol" in session_commands
        assert all("memoryctl" not in command for command in session_commands)


def test_zcode_hook_asset_is_valid_and_uses_process_protocol():
    for path in (ROOT / "src/multi_agent_memory/assets/zcode-hooks.json", ROOT / "adapters/zcode/hooks.example.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["hooks"]["enabled"] is True
        for event in ("SessionStart", "Stop"):
            hook = data["hooks"]["events"][event][0]["hooks"][0]
            assert hook["type"] == "process"
            assert hook["command"] == "mam"
            assert hook["args"] == ["zcode-hook", event]


def test_codex_stop_hook_returns_valid_json_after_discarding_human_readable_stdout(tmp_path):
    mam = tmp_path / "mam"
    mam.write_text("#!/bin/sh\nprintf 'pending receipt\n'\n", encoding="utf-8")
    mam.chmod(0o755)
    environment = os.environ.copy()
    environment["PATH"] = str(tmp_path) + os.pathsep + environment.get("PATH", "")

    for path in (
        ROOT / "adapters/codex/hooks.example.json",
        ROOT / "src/multi_agent_memory/assets/codex-hooks.json",
    ):
        data = json.loads(path.read_text(encoding="utf-8"))
        command = data["hooks"]["Stop"][0]["hooks"][0]["command"]
        result = subprocess.run(
            ["/bin/sh", "-c", command],
            capture_output=True,
            text=True,
            env=environment,
            check=True,
        )
        assert json.loads(result.stdout) == {}


def test_claude_stop_hook_discards_human_readable_stdout(tmp_path):
    mam = tmp_path / "mam"
    mam.write_text("#!/bin/sh\nprintf 'pending receipt\n'\n", encoding="utf-8")
    mam.chmod(0o755)
    environment = os.environ.copy()
    environment["PATH"] = str(tmp_path) + os.pathsep + environment.get("PATH", "")

    for path in (
        ROOT / "adapters/claude/settings.example.json",
        ROOT / "src/multi_agent_memory/assets/claude-hooks.json",
    ):
        data = json.loads(path.read_text(encoding="utf-8"))
        command = data["hooks"]["Stop"][0]["hooks"][0]["command"]
        result = subprocess.run(
            ["/bin/sh", "-c", command],
            capture_output=True,
            text=True,
            env=environment,
            check=True,
        )
        assert result.stdout == ""


def test_opencode_adapter_injects_protocol_and_context(tmp_path):
    mam = tmp_path / "mam"
    mam.write_text(
        "#!/bin/sh\n"
        "case \"$1\" in\n"
        "  protocol) printf 'PROTOCOL: use mam for memory operations' ;;\n"
        "  context) printf 'CONTEXT: confirmed preferences' ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    mam.chmod(0o755)
    environment = os.environ.copy()
    environment["PATH"] = str(tmp_path) + os.pathsep + environment.get("PATH", "")
    path = ROOT / "adapters/opencode/agent-memory.js"
    script = f"""
const module = await import({path.as_uri()!r});
const plugin = await module.AgentMemoryPlugin({{ directory: {str(tmp_path)!r} }});
const output = {{ system: [] }};
await plugin["experimental.chat.system.transform"]({{ sessionID: "test" }}, output);
const text = output.system.join("\\n");
if (!text.includes("PROTOCOL: use mam for memory operations")) throw new Error("protocol was not injected");
if (!text.includes("CONTEXT: confirmed preferences")) throw new Error("context was not injected");
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        env=environment,
    )
    assert result.returncode == 0, result.stderr


def test_opencode_adapter_flushes_pending_sessions_on_dispose(tmp_path):
    mam = tmp_path / "mam"
    log = tmp_path / "mam.log"
    mam.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' \"$*\" >> \"$MAM_LOG\"\n"
        "case \"$1\" in\n"
        "  protocol) printf 'PROTOCOL' ;;\n"
        "  context) printf 'CONTEXT' ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    mam.chmod(0o755)
    environment = os.environ.copy()
    environment.pop("AGENT_MEMORY_SUMMARY_FILE", None)
    environment["MAM_LOG"] = str(log)
    environment["PATH"] = str(tmp_path) + os.pathsep + environment.get("PATH", "")

    for path in (
        ROOT / "adapters/opencode/agent-memory.js",
        ROOT / "src/multi_agent_memory/assets/opencode-agent-memory.js",
    ):
        script = f"""
const module = await import({path.as_uri()!r});
const plugin = await module.AgentMemoryPlugin({{ directory: {str(tmp_path)!r} }});
const output = {{ system: [] }};
await plugin["experimental.chat.system.transform"]({{ sessionID: "session-123" }}, output);
if (typeof plugin.dispose !== "function") throw new Error("missing dispose handler");
await plugin.dispose();
"""
        subprocess.run(
            ["node", "--input-type=module", "-e", script],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )

    calls = log.read_text(encoding="utf-8").splitlines()
    assert calls.count("pending --session-id session-123 --summary-file ") == 2
