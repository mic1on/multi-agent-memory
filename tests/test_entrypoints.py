import subprocess
import sys


def test_cli_module_help_is_available():
    result = subprocess.run([sys.executable, "-m", "multi_agent_memory.cli", "--help"], capture_output=True, text=True, check=True)
    assert "Shared local-first memory" in result.stdout


def test_short_entrypoint_is_available():
    result = subprocess.run(["uv", "run", "mam", "--help"], capture_output=True, text=True, check=True)
    assert "Shared local-first memory" in result.stdout
