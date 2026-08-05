import json
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


def test_codex_example_is_valid_json():
    json.loads((ROOT / "adapters/codex/hooks.example.json").read_text(encoding="utf-8"))
