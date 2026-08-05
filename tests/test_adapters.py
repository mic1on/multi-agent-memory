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
    data = json.loads((ROOT / "adapters/codex/hooks.example.json").read_text(encoding="utf-8"))
    session_commands = [
        hook["command"]
        for block in data["hooks"]["SessionStart"]
        for hook in block["hooks"]
    ]
    assert "mam protocol" in session_commands
    assert all("memoryctl" not in command for command in session_commands)


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
