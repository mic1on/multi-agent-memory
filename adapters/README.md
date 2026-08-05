# Agent adapters

All adapters assume that the memoryctl command is installed and available on PATH.
They are intentionally thin:

- startup runs memoryctl recover;
- the agent prompt receives memoryctl context output;
- shutdown writes a pending receipt only when AGENT_MEMORY_SUMMARY_FILE
  points to an explicitly created summary file.

The adapters never read arbitrary transcript files, send data to a service, or
promote candidate memories. Copy the relevant files into the agent supported
extension or hooks directory and merge them with existing configuration.

## Codex

Review and merge codex/hooks.example.json into the Codex hooks file. Do not
replace unrelated hooks. A stop hook is inert unless
AGENT_MEMORY_SUMMARY_FILE points to a readable file.

## Pi

Copy pi/agent-memory.js to the Pi extensions directory and restart Pi. Pis
extension API supplies the current working directory to the CLI.

## OpenCode

Copy opencode/agent-memory.js to the OpenCode plugins directory and restart
OpenCode. The plugin caches context per session to avoid repeated index reads.
