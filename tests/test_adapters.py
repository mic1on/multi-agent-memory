import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_javascript_adapters_parse():
    for path in (ROOT / "adapters/pi/agent-memory.js", ROOT / "adapters/opencode/agent-memory.js"):
        subprocess.run(["node", "--check", str(path)], check=True, capture_output=True, text=True)


def test_codex_example_is_valid_json():
    json.loads((ROOT / "adapters/codex/hooks.example.json").read_text(encoding="utf-8"))
